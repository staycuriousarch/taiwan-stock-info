"""四面向摘要聚合：首頁 /overview 一次載入。"""
from __future__ import annotations

from app.services import chips, fundamental, news, search, technical


def get_overview(stock_id: str) -> dict:
    meta = search.resolve(stock_id) or {"stock_id": stock_id}
    return {
        "stock_id": meta.get("stock_id", stock_id),
        "stock_name": meta.get("stock_name"),
        "industry_category": meta.get("industry_category"),
        "fundamental": fundamental.get_fundamental_summary(stock_id),
        "technical": technical.get_technical_summary(stock_id),
        "chips": chips.get_chips_summary(stock_id),
        "news": news.get_news(stock_id),
    }
