"""RAW 層落地到 Snowflake。介面與 core/loader.py（DuckDB 版）完全一致。

這是架構上刻意的切割：sources.py／normalize.py／contracts.py 三支完全
不知道資料最後落到哪裡，換落地目標只需要換這一支。run_local.py 用
--target 決定要載入哪一個 loader 模組。

與 DuckDB 版的兩個實質差異：
    1. payload 存成真正的 VARIANT（用 PARSE_JSON），不是 JSON 字串，
       dbt staging 才能直接 payload:欄位名::型別 取值。
    2. 連線參數走環境變數 + key-pair 認證，不是檔案路徑。

環境變數：
    SNOWFLAKE_ACCOUNT               必填，例如 AO92359
    SNOWFLAKE_USER                  必填，例如 SVC_EL_GITHUB
    SNOWFLAKE_PRIVATE_KEY           必填，PEM 私鑰全文
    SNOWFLAKE_PRIVATE_KEY_PASSPHRASE 選填，產金鑰時設的 passphrase
    SNOWFLAKE_ROLE                  選填，預設 EL_LOADER
    SNOWFLAKE_WAREHOUSE             選填，預設 EL_WH
    SNOWFLAKE_DATABASE              選填，預設 TW_STOCK
    SNOWFLAKE_SCHEMA                選填，預設 RAW
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timezone

import snowflake.connector
from cryptography.hazmat.primitives import serialization

from core.contracts import REQUIRED_FIELDS

logger = logging.getLogger(__name__)

# 一次 INSERT 塞幾列。Snowflake 單一語句的 bind 變數有上限，
# 500 列 × 6 個欄位 = 3000 個 bind，留足餘裕。
_CHUNK_SIZE = 500


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"缺少必要環境變數 {name}")
    return value


def _private_key_der() -> bytes:
    """把 PEM 私鑰轉成 connector 要的 DER 格式。"""
    pem = _require_env("SNOWFLAKE_PRIVATE_KEY").encode()
    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None
    key = serialization.load_pem_private_key(
        pem, password=passphrase.encode() if passphrase else None
    )
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_connection():
    """建立 Snowflake 連線。

    paramstyle 刻意指定 qmark（用 ? 佔位）而非 connector 預設的 pyformat
    （用 %s）——因為 TWSE 的欄位名稱本身就含有百分比符號（例如
    '漲跌百分比(%)'），pyformat 會把資料裡的 % 當成佔位符解析而炸掉。
    """
    conn = snowflake.connector.connect(
        account=_require_env("SNOWFLAKE_ACCOUNT"),
        user=_require_env("SNOWFLAKE_USER"),
        private_key=_private_key_der(),
        role=os.environ.get("SNOWFLAKE_ROLE", "EL_LOADER"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "EL_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "TW_STOCK"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "RAW"),
        paramstyle="qmark",
    )
    logger.info("已連線 Snowflake：account=%s user=%s",
                os.environ["SNOWFLAKE_ACCOUNT"], os.environ["SNOWFLAKE_USER"])
    return conn


def _validate(table: str, rows: list[dict]) -> None:
    """與 DuckDB 版同一套輕量檢查：抓「回應形狀整個跑掉」這種明顯異常。"""
    required = REQUIRED_FIELDS.get(table)
    if not required or not rows:
        return
    missing = [f for f in required if f not in rows[0]]
    if missing:
        raise ValueError(
            f"{table}：回應缺少必要欄位 {missing}，來源可能已改版或回傳異常內容"
        )


def load_rows(
    conn,
    table: str,
    rows: list[dict],
    *,
    trade_date: date,
    runner: str,
    source_url: str,
    load_id: str,
) -> int:
    """冪等寫入：同一 (table, trade_date, runner) 先刪後插。

    整批包在一個交易裡——中途失敗會整個回滾，不會留下刪掉舊資料
    但新資料只寫一半的狀態。
    """
    _validate(table, rows)

    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
    trade_date_str = trade_date.isoformat()
    cur = conn.cursor()

    try:
        cur.execute("BEGIN")
        cur.execute(
            f"DELETE FROM {table} WHERE _trade_date = ?::DATE AND _runner = ?",
            (trade_date_str, runner),
        )

        for start in range(0, len(rows), _CHUNK_SIZE):
            chunk = rows[start : start + _CHUNK_SIZE]
            values_clause = ", ".join(["(?, ?, ?, ?, ?, ?)"] * len(chunk))
            params: list[str] = []
            for row in chunk:
                params += [
                    load_id, loaded_at, source_url, runner, trade_date_str,
                    json.dumps(row, ensure_ascii=False),
                ]
            cur.execute(
                f"""
                INSERT INTO {table}
                    (_load_id, _loaded_at, _source_url, _runner, _trade_date, payload)
                SELECT column1::VARCHAR,
                       column2::TIMESTAMP_NTZ,
                       column3::VARCHAR,
                       column4::VARCHAR,
                       column5::DATE,
                       PARSE_JSON(column6)
                FROM VALUES {values_clause}
                """,
                params,
            )

        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise
    finally:
        cur.close()

    logger.info("%s trade_date=%s runner=%s → 寫入 %d 列", table, trade_date, runner, len(rows))
    return len(rows)
