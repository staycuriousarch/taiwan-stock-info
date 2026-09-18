"""日期格式轉換：查詢參數用西元、回應內容解析用民國年，兩個方向不要搞混。

依架構決策，EL 只做 E 和 L，不做 T（型別轉換、業務邏輯全部留給 dbt
staging）。這裡的函式分兩類：

    to_western_compact() / to_slash_date()
        組「請求參數」用。TWSE／TPEX 的查詢參數一律吃**西元**日期
        （YYYYMMDD 或 YYYY/MM/DD），跟回應內容裡顯示的民國年格式無關。

        踩過的雷：MI_INDEX 傳民國年格式的 date 參數（例如 "1150914"）
        不會報錯，而是**默默回傳「今天」的資料**——這種沉默錯誤比報錯
        更危險，因此這裡刻意不提供「西元轉民國年」的請求參數建構函式，
        避免重蹈覆轍。

    roc_compact_to_iso() / roc_chinese_to_iso()
        解析「回應內容」用。TWT49U 這類區間查詢的回應，每一列自帶
        各自的民國年日期（列與列可能不同一天），需要個別解析才能標
        出每列真正對應的交易日——目前 sources.fetch_twse_exright()
        僅支援 start=end 的單日呼叫，尚未使用到這兩個函式；之後要做
        「一次回補一段區間」時才需要逐列呼叫解析，取代目前「整批貼
        同一個 trade_date」的簡化做法。
"""
from __future__ import annotations

import re
from datetime import date

_CHINESE_DATE_RE = re.compile(r"(\d{2,3})年(\d{1,2})月(\d{1,2})日")


def roc_compact_to_iso(value: str) -> str:
    """'1150914' -> '2026-09-14'。民國年 + 月日共 7 碼（無分隔符）。"""
    s = value.strip()
    if len(s) != 7:
        raise ValueError(f"預期 7 碼民國年日期，收到：{value!r}")
    year = int(s[:3]) + 1911
    month, day = s[3:5], s[5:7]
    return f"{year:04d}-{month}-{day}"


def roc_chinese_to_iso(value: str) -> str:
    """'115年07月01日' -> '2026-07-01'。"""
    m = _CHINESE_DATE_RE.search(value.strip())
    if not m:
        raise ValueError(f"無法解析民國年日期：{value!r}")
    roc_year, month, day = (int(g) for g in m.groups())
    return f"{roc_year + 1911:04d}-{month:02d}-{day:02d}"


def to_western_compact(d: date) -> str:
    """date(2026, 9, 14) -> '20260914'。MI_INDEX／T86／TWT49U 請求參數格式。"""
    return d.strftime("%Y%m%d")


def to_slash_date(d: date) -> str:
    """date(2026, 9, 14) -> '2026/09/14'。TPEX 端點請求參數格式。"""
    return d.strftime("%Y/%m/%d")
