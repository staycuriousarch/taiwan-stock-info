"""資料存取整合層：先查 DuckDB 快取，未命中才打 FinMind 並回寫快取。

所有面向的 service 都透過這裡取資料，統一享有快取與節流保護。
"""
from __future__ import annotations

import pandas as pd

from app.clients.finmind import finmind_client
from app.db import duckdb_conn


def fetch(
    dataset: str,
    *,
    data_id: str = "",
    start_date: str = "",
    end_date: str = "",
    ttl_hours: float | None = None,
) -> pd.DataFrame:
    """cache-aside 取資料。回傳 DataFrame（可能為空）。"""
    cached = duckdb_conn.cache_get(
        dataset, data_id, start_date, end_date, ttl_hours=ttl_hours
    )
    if cached is not None:
        return cached

    df = finmind_client.get_dataset(
        dataset,
        data_id=data_id or None,
        start_date=start_date or None,
        end_date=end_date or None,
    )
    duckdb_conn.cache_put(df, dataset, data_id, start_date, end_date)
    return df
