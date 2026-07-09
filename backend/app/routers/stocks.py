"""個股相關 API 路由。

路由以同步 def 定義，FastAPI 會自動丟進 threadpool 執行，
不阻塞事件迴圈（下游 DuckDB / pandas 皆同步）。
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import (
    chips,
    fundamental,
    news,
    overview,
    search,
    technical,
)

router = APIRouter(prefix="/api", tags=["stocks"])


@router.get("/search")
def search_stocks(q: str = Query(..., min_length=1), limit: int = 20):
    """依代碼或公司名稱模糊搜尋。"""
    return {"query": q, "results": search.search(q, limit=limit)}


@router.get("/stock/{stock_id}/overview")
def stock_overview(stock_id: str):
    return overview.get_overview(stock_id)


@router.get("/stock/{stock_id}/fundamental")
def stock_fundamental(stock_id: str):
    return fundamental.get_fundamental_summary(stock_id)


@router.get("/stock/{stock_id}/technical")
def stock_technical(stock_id: str):
    return {
        "summary": technical.get_technical_summary(stock_id),
        "series": technical.get_price_series(stock_id),
    }


@router.get("/stock/{stock_id}/chips")
def stock_chips(stock_id: str):
    return chips.get_chips_summary(stock_id)


@router.get("/stock/{stock_id}/news")
def stock_news(stock_id: str, limit: int = 5):
    return {"news": news.get_news(stock_id, limit=limit)}
