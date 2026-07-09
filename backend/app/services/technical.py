"""技術面：股價、均線（MA5/20/60）、成交量、漲跌幅。均線在後端以 pandas 計算。"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

from app.services import data_source

# 抓約 4 個月日線，足以算出 MA60（60 個交易日）
_LOOKBACK_DAYS = 130


def _price_history(stock_id: str) -> pd.DataFrame:
    start = (date.today() - timedelta(days=_LOOKBACK_DAYS)).isoformat()
    df = data_source.fetch("TaiwanStockPrice", data_id=stock_id, start_date=start)
    if df.empty:
        return df
    df = df.sort_values("date").reset_index(drop=True)
    for w in (5, 20, 60):
        df[f"ma{w}"] = df["close"].rolling(window=w).mean().round(2)
    return df


def get_technical_summary(stock_id: str) -> dict:
    df = _price_history(stock_id)
    if df.empty:
        return {"available": False}

    latest = df.iloc[-1]
    prev_close = df.iloc[-2]["close"] if len(df) >= 2 else None
    change = round(float(latest["close"]) - float(prev_close), 2) if prev_close else None
    change_pct = (
        round(change / float(prev_close) * 100, 2) if prev_close else None
    )

    def _ma(col: str):
        val = latest.get(col)
        return None if pd.isna(val) else float(val)

    return {
        "available": True,
        "date": str(latest["date"]),
        "close": float(latest["close"]),
        "open": float(latest["open"]),
        "high": float(latest["max"]),
        "low": float(latest["min"]),
        "change": change,
        "change_pct": change_pct,
        "volume": int(latest["Trading_Volume"]),
        "ma5": _ma("ma5"),
        "ma20": _ma("ma20"),
        "ma60": _ma("ma60"),
    }


def get_price_series(stock_id: str) -> list[dict]:
    """給前端 K 線圖用的完整序列（含均線）。"""
    df = _price_history(stock_id)
    if df.empty:
        return []
    cols = ["date", "open", "max", "min", "close", "Trading_Volume", "ma5", "ma20", "ma60"]
    out = df[[c for c in cols if c in df.columns]].rename(
        columns={"max": "high", "min": "low", "Trading_Volume": "volume"}
    )
    # 用 to_json 把 NaN（均線前幾筆）正確轉成 null，避免 JSON 序列化失敗
    return json.loads(out.to_json(orient="records"))
