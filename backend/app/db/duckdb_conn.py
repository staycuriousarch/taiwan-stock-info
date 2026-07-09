"""DuckDB 連線與快取層。

快取策略（骨架階段）：cache-aside + 新鮮度檢查。
以 (dataset, data_id, start_date, end_date) 為鍵，把 FinMind 回傳的
DataFrame 序列化成 JSON 存進 cache_store，並記錄 fetched_at。
命中且未過期 → 直接回傳，不打 FinMind。

DuckDB 單連線非執行緒安全，故所有存取以 lock 序列化（本專案規模足夠）。
"""
from __future__ import annotations

import io
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_conn: duckdb.DuckDBPyConnection | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_connection() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        db_path = Path(settings.duckdb_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _conn = duckdb.connect(str(db_path))
        _init_schema(_conn)
        logger.info("DuckDB 已連線：%s", db_path)
    return _conn


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache_store (
            dataset    VARCHAR NOT NULL,
            data_id    VARCHAR NOT NULL DEFAULT '',
            start_date VARCHAR NOT NULL DEFAULT '',
            end_date   VARCHAR NOT NULL DEFAULT '',
            fetched_at TIMESTAMPTZ NOT NULL,
            payload    VARCHAR NOT NULL,
            PRIMARY KEY (dataset, data_id, start_date, end_date)
        )
        """
    )
    # 作業狀態表：記錄每日更新的最後成功日期、統計等
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_meta (
            key   VARCHAR PRIMARY KEY,
            value VARCHAR
        )
        """
    )


def get_meta(key: str) -> str | None:
    conn = get_connection()
    with _lock:
        row = conn.execute("SELECT value FROM job_meta WHERE key = ?", [key]).fetchone()
    return row[0] if row else None


def set_meta(key: str, value: str) -> None:
    conn = get_connection()
    with _lock:
        conn.execute(
            "INSERT OR REPLACE INTO job_meta (key, value) VALUES (?, ?)", [key, value]
        )


def cache_invalidate(data_id: str) -> int:
    """刪除某股票的所有快取列（用於每日更新強制重抓）。回傳刪除筆數。"""
    conn = get_connection()
    with _lock:
        before = conn.execute(
            "SELECT count(*) FROM cache_store WHERE data_id = ?", [data_id]
        ).fetchone()[0]
        conn.execute("DELETE FROM cache_store WHERE data_id = ?", [data_id])
    return before


def list_cached_stock_ids() -> list[str]:
    """列出快取中出現過的股票代碼（代表有人查過），排除空值。"""
    conn = get_connection()
    with _lock:
        rows = conn.execute(
            "SELECT DISTINCT data_id FROM cache_store WHERE data_id <> ''"
        ).fetchall()
    return [r[0] for r in rows]


def cache_get(
    dataset: str,
    data_id: str = "",
    start_date: str = "",
    end_date: str = "",
    *,
    ttl_hours: float | None = None,
) -> pd.DataFrame | None:
    """命中且未過期回傳 DataFrame，否則回傳 None。"""
    ttl = settings.cache_ttl_hours if ttl_hours is None else ttl_hours
    conn = get_connection()
    with _lock:
        row = conn.execute(
            """
            SELECT fetched_at, payload FROM cache_store
            WHERE dataset = ? AND data_id = ? AND start_date = ? AND end_date = ?
            """,
            [dataset, data_id, start_date, end_date],
        ).fetchone()

    if row is None:
        return None

    fetched_at, payload = row
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    if _now() - fetched_at > timedelta(hours=ttl):
        logger.info("快取過期 %s data_id=%s", dataset, data_id)
        return None

    logger.info("快取命中 %s data_id=%s", dataset, data_id)
    return pd.read_json(io.StringIO(payload), orient="records", dtype=False)


def cache_put(
    df: pd.DataFrame,
    dataset: str,
    data_id: str = "",
    start_date: str = "",
    end_date: str = "",
) -> None:
    conn = get_connection()
    payload = df.to_json(orient="records", force_ascii=False)
    with _lock:
        conn.execute(
            """
            INSERT OR REPLACE INTO cache_store
                (dataset, data_id, start_date, end_date, fetched_at, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [dataset, data_id, start_date, end_date, _now(), payload],
        )
