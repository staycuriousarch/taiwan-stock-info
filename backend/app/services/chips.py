"""籌碼面：三大法人近期買賣超、融資融券餘額。"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.services import data_source


def _institutional(stock_id: str, days: int = 20) -> dict:
    start = (date.today() - timedelta(days=days)).isoformat()
    df = data_source.fetch(
        "TaiwanStockInstitutionalInvestorsBuySell", data_id=stock_id, start_date=start
    )
    if df.empty:
        return {"available": False}

    df["net"] = df["buy"].astype(float) - df["sell"].astype(float)
    latest_date = df["date"].max()
    # 依法人別彙總「最近一個交易日」買賣超（單位：股）
    latest = df[df["date"] == latest_date]
    by_investor = (
        latest.groupby("name")["net"].sum().round(0).astype("int64").to_dict()
    )
    total_net = int(latest["net"].sum())

    return {
        "available": True,
        "date": str(latest_date),
        "total_net_shares": total_net,
        "by_investor": by_investor,  # 如 {"Foreign_Investor": ..., "Investment_Trust": ...}
    }


def _margin(stock_id: str, days: int = 10) -> dict:
    start = (date.today() - timedelta(days=days)).isoformat()
    df = data_source.fetch(
        "TaiwanStockMarginPurchaseShortSale", data_id=stock_id, start_date=start
    )
    if df.empty:
        return {"available": False}
    latest = df.sort_values("date").iloc[-1]
    return {
        "available": True,
        "date": str(latest["date"]),
        "margin_balance": (
            int(latest["MarginPurchaseTodayBalance"])
            if pd.notna(latest.get("MarginPurchaseTodayBalance"))
            else None
        ),
        "short_balance": (
            int(latest["ShortSaleTodayBalance"])
            if pd.notna(latest.get("ShortSaleTodayBalance"))
            else None
        ),
    }


def get_chips_summary(stock_id: str) -> dict:
    return {
        "institutional": _institutional(stock_id),
        "margin": _margin(stock_id),
    }
