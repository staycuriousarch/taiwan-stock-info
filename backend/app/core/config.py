"""應用程式設定，從環境變數 / .env 讀取。"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # FinMind API
    finmind_token: str = ""  # 沒有也能用，只是額度較低（匿名）
    finmind_base_url: str = "https://api.finmindtrade.com/api/v4"

    # 節流：FinMind 免費驗證後上限 600/hr。保守設一點留餘裕。
    finmind_max_requests_per_hour: int = 550
    finmind_timeout_seconds: float = 20.0

    # DuckDB 快取
    duckdb_path: str = "data/finance.duckdb"

    # 快取新鮮度（小時）：同一資料集/股票在此時間內不重打 FinMind
    cache_ttl_hours: float = 12.0

    # CORS：前端開發伺服器來源
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
