"""基本面：月營收（含年增/月增）、PER/PBR、EPS、現金股利。"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.services import data_source


def _month_revenue(stock_id: str) -> dict:
    # 抓約 14 個月，才能算最新月的年增（需去年同月）
    start = (date.today() - timedelta(days=430)).isoformat()
    df = data_source.fetch("TaiwanStockMonthRevenue", data_id=stock_id, start_date=start)
    if df.empty:
        return {"available": False}

    df = df.sort_values(["revenue_year", "revenue_month"]).reset_index(drop=True)
    latest = df.iloc[-1]
    rev = float(latest["revenue"])
    year, month = int(latest["revenue_year"]), int(latest["revenue_month"])

    yoy = mom = None
    last_year = df[(df["revenue_year"] == year - 1) & (df["revenue_month"] == month)]
    if not last_year.empty and float(last_year.iloc[0]["revenue"]):
        yoy = round((rev / float(last_year.iloc[0]["revenue"]) - 1) * 100, 2)
    if len(df) >= 2 and float(df.iloc[-2]["revenue"]):
        mom = round((rev / float(df.iloc[-2]["revenue"]) - 1) * 100, 2)

    return {
        "available": True,
        "year": year,
        "month": month,
        "revenue": rev,
        "yoy_pct": yoy,
        "mom_pct": mom,
    }


def _per_pbr(stock_id: str) -> dict:
    start = (date.today() - timedelta(days=14)).isoformat()
    df = data_source.fetch("TaiwanStockPER", data_id=stock_id, start_date=start)
    if df.empty:
        return {"available": False}
    latest = df.sort_values("date").iloc[-1]
    return {
        "available": True,
        "date": str(latest["date"]),
        "per": float(latest["PER"]) if pd.notna(latest.get("PER")) else None,
        "pbr": float(latest["PBR"]) if pd.notna(latest.get("PBR")) else None,
        "dividend_yield": (
            float(latest["dividend_yield"]) if pd.notna(latest.get("dividend_yield")) else None
        ),
    }


def _latest_eps(stock_id: str) -> dict:
    start = (date.today() - timedelta(days=400)).isoformat()
    df = data_source.fetch("TaiwanStockFinancialStatements", data_id=stock_id, start_date=start)
    if df.empty or "type" not in df.columns:
        return {"available": False}
    eps = df[df["type"] == "EPS"].sort_values("date")
    if eps.empty:
        return {"available": False}
    latest = eps.iloc[-1]
    return {"available": True, "date": str(latest["date"]), "eps": float(latest["value"])}


def get_fundamental_summary(stock_id: str) -> dict:
    return {
        "month_revenue": _month_revenue(stock_id),
        "valuation": _per_pbr(stock_id),
        "eps": _latest_eps(stock_id),
    }
