"""RAW 層的落地邏輯：一個來源一張表，一列一筆原始記錄，冪等寫入。

這支是唯一「碰資料庫」的模組。之後要把落地目標從 DuckDB 換成
Snowflake，只需要重寫這支檔案——sources.py／normalize.py／runners
完全不需要跟著改，這是刻意的介面切割（見架構文件「el/core 的介面」）。

表結構跟目標架構文件一致：
    _load_id     VARCHAR    一次執行一個 UUID
    _loaded_at   TIMESTAMP  UTC，freshness 檢查用
    _source_url  VARCHAR    出問題時能重現當初那次呼叫
    _runner      VARCHAR    'local' | 'github_actions' | 'snowpark'
    _trade_date  DATE       冪等刪除與分區用
    payload      VARCHAR    一列原始記錄的 JSON 字串（作法與現行
                             backend/app/db/duckdb_conn.py 的 cache_store
                             一致：DuckDB 沒有 VARIANT 型別，先用 JSON
                             字串存，Snowflake 版本再換成真正的 VARIANT）
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

from core.contracts import REQUIRED_FIELDS

logger = logging.getLogger(__name__)

RAW_SCHEMA = "raw"


def get_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
    return conn


def _ensure_table(conn: duckdb.DuckDBPyConnection, table: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_SCHEMA}.{table} (
            _load_id    VARCHAR,
            _loaded_at  TIMESTAMP,
            _source_url VARCHAR,
            _runner     VARCHAR,
            _trade_date DATE,
            payload     VARCHAR
        )
        """
    )


def _validate(table: str, rows: list[dict]) -> None:
    """輕量檢查：抽第一列看必要欄位在不在，抓「回應形狀整個跑掉」這種
    明顯異常（例如來源改版、回傳成錯誤頁）。不檢查每一列，也不檢查值
    是否合理——那些是 dbt 測試的工作。
    """
    required = REQUIRED_FIELDS.get(table)
    if not required or not rows:
        return
    missing = [f for f in required if f not in rows[0]]
    if missing:
        raise ValueError(
            f"{table}：回應缺少必要欄位 {missing}，來源可能已改版或回傳異常內容"
        )


def load_rows(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    rows: list[dict],
    *,
    trade_date: date,
    runner: str,
    source_url: str,
    load_id: str,
) -> int:
    """冪等寫入：同一 (table, trade_date, runner) 先刪後插，重跑不會重複。

    _runner 放進刪除條件，讓本機／GitHub Actions／Snowpark 三條路徑
    互不干擾——各自只清理自己寫過的資料。
    """
    _validate(table, rows)
    _ensure_table(conn, table)

    loaded_at = datetime.now(timezone.utc)
    records = [
        (load_id, loaded_at, source_url, runner, trade_date, json.dumps(row, ensure_ascii=False))
        for row in rows
    ]

    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            f"DELETE FROM {RAW_SCHEMA}.{table} WHERE _trade_date = ? AND _runner = ?",
            [trade_date, runner],
        )
        if records:
            conn.executemany(
                f"""
                INSERT INTO {RAW_SCHEMA}.{table}
                    (_load_id, _loaded_at, _source_url, _runner, _trade_date, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                records,
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info("%s trade_date=%s runner=%s → 寫入 %d 列", table, trade_date, runner, len(records))
    return len(records)
