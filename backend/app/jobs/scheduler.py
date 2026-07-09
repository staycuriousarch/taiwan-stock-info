"""APScheduler 排程：每日 09:00（台北）更新，並在啟動時補跑錯過的更新。"""
from __future__ import annotations

import logging

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.daily_update import already_updated_today, run_daily_update

logger = logging.getLogger(__name__)

_TAIPEI = pytz.timezone("Asia/Taipei")
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    """啟動排程器。冪等：重複呼叫只會有一個實例。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone=_TAIPEI)
    # 每天 09:00 更新前一日資料
    sched.add_job(
        run_daily_update,
        CronTrigger(hour=9, minute=0, timezone=_TAIPEI),
        id="daily_update",
        misfire_grace_time=3600,  # 錯過 1 小時內仍補跑
        coalesce=True,
        max_instances=1,
    )
    sched.start()
    _scheduler = sched
    logger.info("排程器已啟動：每日 09:00 (Asia/Taipei) 更新")

    # 開機補跑：今天還沒更新過就背景跑一次（解決 server 非 09:00 常駐的情境）
    if not already_updated_today():
        logger.info("今天尚未更新，安排啟動補跑")
        sched.add_job(run_daily_update, id="startup_catchup", max_instances=1)
    else:
        logger.info("今天已更新過，略過啟動補跑")

    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("排程器已關閉")
