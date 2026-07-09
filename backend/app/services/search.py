"""搜尋：股票代碼 / 公司名稱 → 個股。

啟動或首次查詢時抓 TaiwanStockInfo（台股總覽）建立記憶體索引，
之後模糊搜尋都在記憶體完成，不重打 FinMind。
"""
from __future__ import annotations

import logging
import threading

import pandas as pd

from app.services import data_source

logger = logging.getLogger(__name__)

_INFO_TTL_HOURS = 24.0
_index_lock = threading.Lock()
_index: pd.DataFrame | None = None


def _build_index() -> pd.DataFrame:
    df = data_source.fetch("TaiwanStockInfo", ttl_hours=_INFO_TTL_HOURS)
    if df.empty:
        return df
    # 同一 stock_id 可能有多個 industry_category，去重保留第一筆
    cols = [c for c in ("stock_id", "stock_name", "industry_category", "type") if c in df.columns]
    df = df[cols].drop_duplicates(subset=["stock_id"]).reset_index(drop=True)
    logger.info("股票索引建立完成，共 %d 檔", len(df))
    return df


def get_index(force_refresh: bool = False) -> pd.DataFrame:
    global _index
    with _index_lock:
        if _index is None or force_refresh:
            _index = _build_index()
        return _index


def search(query: str, limit: int = 20) -> list[dict]:
    """依代碼或名稱模糊搜尋，回傳個股清單。"""
    q = query.strip()
    if not q:
        return []

    idx = get_index()
    if idx.empty:
        return []

    if q.isdigit():
        # 純數字：代碼前綴優先，完全相符排最前
        mask = idx["stock_id"].str.startswith(q)
        hits = idx[mask].copy()
        hits["_rank"] = (hits["stock_id"] != q).astype(int)  # 完全相符 rank=0
        hits = hits.sort_values(["_rank", "stock_id"]).drop(columns="_rank")
    else:
        # 文字：名稱包含關鍵字（也順帶比對代碼）
        name_mask = idx["stock_name"].str.contains(q, case=False, na=False, regex=False)
        id_mask = idx["stock_id"].str.contains(q, case=False, na=False, regex=False)
        hits = idx[name_mask | id_mask]

    return hits.head(limit).to_dict(orient="records")


def resolve(query: str) -> dict | None:
    """把使用者輸入解析成單一個股（取搜尋第一名），找不到回 None。"""
    results = search(query, limit=1)
    return results[0] if results else None
