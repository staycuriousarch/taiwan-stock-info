"""EL 的本機／GitHub Actions 入口：抓七個來源、寫進 RAW 層。

    uv run python -m runners.run_local --date 2026-09-14
    uv run python -m runners.run_local                          # 預設抓今天
    uv run python -m runners.run_local --target snowflake       # 落地到 Snowflake

用 --runner 覆寫預設值 'local'；GitHub Actions 的 workflow 呼叫時應傳
--runner github_actions，讓 RAW 表的 _runner 欄位能分辨資料是哪條路徑
寫入的（之後接 Snowpark 展示路線時，兩邊各自只清理自己的資料，互不
干擾——見架構文件「雙軌 EL」）。
"""
from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

from core import contracts, sources

logger = logging.getLogger(__name__)

# 用檔案自身位置算路徑，不依賴呼叫時的工作目錄——不管是從 el/ 底下
# 還是從 repo 根目錄執行 `uv run python -m runners.run_local`，都落在
# 同一個 el/data/el.duckdb，不會因為 cwd 不同而疊出兩份資料庫。
_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "el.duckdb")

# 除權息(TPEX)、上市基本資料兩個來源沒有日期參數，永遠只能拿到「查詢當下」
# 的快照——所以無論 --date 傳什麼，這兩個來源都標記為「今天」，不能誤植成
# 使用者要求的 trade_date，否則 RAW 表的 _trade_date 會說謊。
_DATED_SOURCES = [
    (contracts.RAW_TABLE_QUOTE_TWSE, lambda d: sources.fetch_twse_quote(d)),
    (contracts.RAW_TABLE_QUOTE_TPEX, lambda d: sources.fetch_tpex_quote(d)),
    (contracts.RAW_TABLE_INST_TWSE, lambda d: sources.fetch_twse_inst(d)),
    (contracts.RAW_TABLE_INST_TPEX, lambda d: sources.fetch_tpex_inst(d)),
    (contracts.RAW_TABLE_EXRIGHT_TWSE, lambda d: sources.fetch_twse_exright(d, d)),
]
_SNAPSHOT_SOURCES = [
    (contracts.RAW_TABLE_EXRIGHT_TPEX, lambda: sources.fetch_tpex_exright()),
    (contracts.RAW_TABLE_PROFILE_TWSE, lambda: sources.fetch_twse_profile()),
]


def run(
    trade_date: date, *, runner: str, target: str, db_path: str
) -> dict[str, int | str]:
    # 兩個 loader 的介面一致，差別只在落地目標與連線方式。Snowflake 版的
    # 依賴是選用套件（uv sync --extra snowflake），只在真的要用時才 import，
    # 沒裝也不影響本機 DuckDB 模式。
    if target == "snowflake":
        from core import loader_snowflake as loader

        conn = loader.get_connection()
    else:
        from core import loader

        conn = loader.get_connection(db_path)
    load_rows = loader.load_rows

    load_id = str(uuid.uuid4())
    today = datetime.now().date()
    results: dict[str, int | str] = {}

    for table, fetch in _DATED_SOURCES:
        try:
            rows = fetch(trade_date)
            results[table] = load_rows(
                conn, table, rows,
                trade_date=trade_date, runner=runner,
                source_url=f"<{table}>", load_id=load_id,
            )
        except Exception as exc:  # noqa: BLE001 — 個別來源失敗不該擋住其他來源
            logger.warning("%s 失敗：%s", table, exc)
            results[table] = f"FAILED: {exc}"

    for table, fetch in _SNAPSHOT_SOURCES:
        try:
            rows = fetch()
            results[table] = load_rows(
                conn, table, rows,
                trade_date=today, runner=runner,
                source_url=f"<{table}>", load_id=load_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s 失敗：%s", table, exc)
            results[table] = f"FAILED: {exc}"

    conn.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now().date())
    parser.add_argument("--runner", default="local")
    parser.add_argument("--target", choices=("duckdb", "snowflake"), default="duckdb")
    parser.add_argument("--db-path", default=_DEFAULT_DB_PATH)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    print(f"=== EL 執行：trade_date={args.date} runner={args.runner} target={args.target} ===")
    results = run(args.date, runner=args.runner, target=args.target, db_path=args.db_path)

    print("\n來源                      結果")
    print("-" * 40)
    failed = False
    for table, result in results.items():
        print(f"{table:<26}{result}")
        if isinstance(result, str):
            failed = True

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
