"""管理端點：手動觸發每日更新、查詢更新狀態。"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.db import duckdb_conn
from app.jobs import daily_update

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/refresh")
def trigger_refresh(background_tasks: BackgroundTasks):
    """手動觸發一次每日更新（背景執行，立即回應）。"""
    background_tasks.add_task(daily_update.run_daily_update)
    return {"status": "started", "message": "更新已於背景啟動，可稍後用 /api/admin/status 查詢"}


@router.get("/status")
def update_status():
    """查詢最近一次更新的日期與摘要。"""
    return {
        "last_update_date": duckdb_conn.get_meta(daily_update.META_LAST_UPDATE_DATE),
        "already_updated_today": daily_update.already_updated_today(),
        "last_summary": duckdb_conn.get_meta(daily_update.META_LAST_UPDATE_SUMMARY),
    }
