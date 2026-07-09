"""消息面：個股相關新聞。"""
from __future__ import annotations

import json
from datetime import date, timedelta

from app.services import data_source


def get_news(stock_id: str, limit: int = 5) -> list[dict]:
    start = (date.today() - timedelta(days=14)).isoformat()
    df = data_source.fetch("TaiwanStockNews", data_id=stock_id, start_date=start)
    if df.empty:
        return []
    df = df.sort_values("date", ascending=False).head(limit)
    cols = [c for c in ("date", "title", "source", "link", "description") if c in df.columns]
    # to_json 把缺漏欄位的 NaN 轉成 null，避免 JSON 序列化失敗
    return json.loads(df[cols].to_json(orient="records"))
