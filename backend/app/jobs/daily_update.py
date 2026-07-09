"""每日更新作業：刷新股票代碼表與各股四面向快取。

策略：目標股票 = 快取中出現過的（有人查過）∪ 種子清單。
對每檔股票先 cache_invalidate 再 get_overview 強制重抓，重用既有面向邏輯。

可由三處觸發：
  1. APScheduler 每日 09:00（見 scheduler.py）
  2. server 啟動時的補跑（今天尚未更新過才跑）
  3. 手動：`python -m app.jobs.daily_update` 或 POST /api/admin/refresh
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from app.clients.finmind import FinMindError, RateLimitError
from app.db import duckdb_conn
from app.services import data_source, overview, search

logger = logging.getLogger(__name__)

# 熱門種子清單：即使沒人查過也每日保鮮
SEED_STOCK_IDS = [
    "2330",  # 台積電
    "2317",  # 鴻海
    "2454",  # 聯發科
    "2308",  # 台達電
    "2382",  # 廣達
    "2412",  # 中華電
    "2891",  # 中信金
    "2881",  # 富邦金
    "0050",  # 元大台灣50
    "2603",  # 長榮
]

META_LAST_UPDATE_DATE = "last_update_date"
META_LAST_UPDATE_SUMMARY = "last_update_summary"


def _refresh_stock_info() -> None:
    """強制重抓台股總覽並重建搜尋索引（ttl=0 繞過快取）。"""
    data_source.fetch("TaiwanStockInfo", ttl_hours=0)
    search.get_index(force_refresh=True)
    logger.info("已刷新 TaiwanStockInfo 與搜尋索引")


def target_stock_ids(extra_ids: list[str] | None = None) -> list[str]:
    ids = set(duckdb_conn.list_cached_stock_ids())
    ids.update(SEED_STOCK_IDS)
    if extra_ids:
        ids.update(extra_ids)
    return sorted(ids)


def run_daily_update(extra_ids: list[str] | None = None) -> dict:
    """執行一次完整更新，回傳統計摘要。"""
    started = datetime.now(timezone.utc)
    logger.info("=== 每日更新開始 ===")

    try:
        _refresh_stock_info()
    except FinMindError as exc:
        logger.warning("刷新股票總覽失敗：%s", exc)

    ids = target_stock_ids(extra_ids)
    logger.info("目標股票 %d 檔", len(ids))

    ok, failed, rate_limited = 0, [], False
    for i, sid in enumerate(ids, 1):
        try:
            duckdb_conn.cache_invalidate(sid)
            overview.get_overview(sid)  # 重抓四面向並回寫快取
            ok += 1
            logger.info("(%d/%d) %s 更新完成", i, len(ids), sid)
        except RateLimitError as exc:
            logger.warning("達 FinMind 流量上限，於第 %d 檔停止：%s", i, exc)
            rate_limited = True
            break
        except FinMindError as exc:
            logger.warning("%s 更新失敗：%s", sid, exc)
            failed.append(sid)

    finished = datetime.now(timezone.utc)
    summary = {
        "run_at": started.isoformat(),
        "duration_sec": round((finished - started).total_seconds(), 1),
        "targeted": len(ids),
        "succeeded": ok,
        "failed": failed,
        "rate_limited": rate_limited,
    }

    # 只有真的有更新到才記錄「今天已更新」，避免額度爆掉卻誤判已完成
    if ok > 0 and not rate_limited:
        duckdb_conn.set_meta(META_LAST_UPDATE_DATE, date.today().isoformat())
    duckdb_conn.set_meta(META_LAST_UPDATE_SUMMARY, str(summary))

    logger.info("=== 每日更新結束：%s ===", summary)
    return summary


def already_updated_today() -> bool:
    return duckdb_conn.get_meta(META_LAST_UPDATE_DATE) == date.today().isoformat()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    result = run_daily_update()
    print("\n更新摘要：", result)
