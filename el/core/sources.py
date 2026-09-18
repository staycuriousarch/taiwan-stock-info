"""八個資料來源的抓取函式：純函式，只負責打 API、回傳 list[dict]。

刻意的邊界（架構決策，見 資料源評估文件 附錄）：
    - 只用 requests（Snowpark Anaconda channel 保證有；httpx 不保證），
      這樣同一份程式碼未來才能原封不動搬進 Snowpark stored procedure。
    - 不做型別轉換、不做業務邏輯——只有 _trade_date 的解析例外
      （冪等刪除要用它），其餘全部留給 dbt staging。
    - 不吞例外。requests 逾時、HTTP 非 200、JSON 解析失敗全部往上拋，
      讓呼叫端（runners/run_local.py）決定要不要跳過這個來源繼續跑。

兩種回應形狀：
    - openapi.twse.com.tw / openapi.tpex.org.tw
      → 直接是 list[dict]，欄位名就是 dict key。
    - www.twse.com.tw/rwd/... / www.tpex.org.tw/www/.../response=json
      → {"fields": [...], "data": [[...], ...]}（欄位名和值分開兩個陣列），
        或欄位名/值陣列包在 "tables": [{...}, ...] 裡面。
        用 _rows_from_fields_data() 統一還原成 list[dict]。

尚未實作：ic.tpex.org.tw 產業鏈成分股（HTML 爬蟲，非 JSON API，且需處理
不完整憑證鏈與 Cloudflare 挑戰）。技術性質與其餘 7 個來源不同、且是季
更新非日更新，留待下一輪獨立實作。
"""
from __future__ import annotations

from datetime import date

import requests

from core.normalize import to_slash_date, to_western_compact

_TIMEOUT = 30
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _get_json(url: str, params: dict | None = None) -> dict | list:
    resp = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _rows_from_fields_data(payload: dict) -> list[dict]:
    """{"fields": [...], "data": [[...], ...]} -> list[dict]。

    欄位名去除首尾空白後當 dict key（原始欄位常帶多餘空白，例如
    TPEX 的 '成交股數  '），但不改動值本身。
    """
    fields = [str(f).strip() for f in payload.get("fields") or []]
    rows = payload.get("data") or []
    return [dict(zip(fields, row)) for row in rows]


def _table_by_title(payload: dict, title_contains: str) -> dict:
    """從 RWD 回應的 tables[] 裡找出標題含指定關鍵字的那張表。"""
    for table in payload.get("tables") or []:
        if title_contains in str(table.get("title", "")):
            return table
    raise ValueError(f"回應中找不到標題含「{title_contains}」的表格")


# ---------------------------------------------------------------- 行情 ----

def fetch_twse_quote(trade_date: date) -> list[dict]:
    """上市個股當日收盤行情（含成交金額、漲跌）。

    用 MI_INDEX 而非 STOCK_DAY_ALL，因為後者不支援指定日期查詢
    （只回傳最近一個交易日）。type 務必用 ALLBUT0999，用 ALL 會把
    所有指數表也一起抓下來，回應從 250KB 暴增到 4.8MB。
    """
    url = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
    payload = _get_json(
        url, {"date": to_western_compact(trade_date), "type": "ALLBUT0999", "response": "json"}
    )
    table = _table_by_title(payload, "每日收盤行情")
    return _rows_from_fields_data(table)


def fetch_tpex_quote(trade_date: date) -> list[dict]:
    """上櫃個股當日收盤行情（自帶發行股數，上市那邊沒有）。"""
    url = "https://www.tpex.org.tw/www/zh-tw/afterTrading/otc"
    payload = _get_json(
        url, {"date": to_slash_date(trade_date), "type": "EW", "response": "json"}
    )
    tables = payload.get("tables") or []
    if not tables:
        return []
    return _rows_from_fields_data(tables[0])


# ------------------------------------------------------------ 三大法人 ----

def fetch_twse_inst(trade_date: date) -> list[dict]:
    """上市個股三大法人買賣超（股數，非金額——換算金額留給 dbt）。"""
    url = "https://www.twse.com.tw/rwd/zh/fund/T86"
    payload = _get_json(
        url, {"date": to_western_compact(trade_date), "selectType": "ALL", "response": "json"}
    )
    return _rows_from_fields_data(payload)


def fetch_tpex_inst(trade_date: date) -> list[dict]:
    """上櫃個股三大法人買賣超。"""
    url = "https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"
    payload = _get_json(
        url,
        {"type": "Daily", "sect": "EW", "date": to_slash_date(trade_date), "response": "json"},
    )
    tables = payload.get("tables") or []
    if not tables:
        return []
    return _rows_from_fields_data(tables[0])


# -------------------------------------------------------------- 除權息 ----

def fetch_twse_exright(start_date: date, end_date: date) -> list[dict]:
    """上市除權息計算結果表。支援區間查詢（回補歷史用），
    每列自帶中文格式日期（'115年07月01日'），日常單日跑時 start=end 即可。
    """
    url = "https://www.twse.com.tw/rwd/zh/exRight/TWT49U"
    payload = _get_json(
        url,
        {
            "startDate": to_western_compact(start_date),
            "endDate": to_western_compact(end_date),
            "response": "json",
        },
    )
    return _rows_from_fields_data(payload)


def fetch_tpex_exright() -> list[dict]:
    """上櫃除權息計算結果表。

    已知限制：這個 openapi 端點不支援日期參數，只能拿到「今天」的資料，
    上櫃除權息的歷史無法用這支回補（見架構文件「未決與限制」）。
    """
    url = "https://www.tpex.org.tw/openapi/v1/tpex_exright_daily"
    payload = _get_json(url)
    return list(payload) if isinstance(payload, list) else []


# -------------------------------------------------------------- 基本面 ----

def fetch_twse_profile() -> list[dict]:
    """上市公司基本資料（含已發行普通股數，算市值用）。每月更新即可，
    無日期參數，回傳的是「查詢當下」最新一期。
    """
    url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
    payload = _get_json(url)
    return list(payload) if isinstance(payload, list) else []
