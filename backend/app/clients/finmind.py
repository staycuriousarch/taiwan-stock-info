"""FinMind API client：封裝呼叫、節流、錯誤處理。

採同步實作（httpx.Client），因為下游 DuckDB / pandas 都是同步；
FastAPI 會把同步路由丟進 threadpool，不會阻塞事件迴圈。
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque

import httpx
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)


class FinMindError(RuntimeError):
    """FinMind API 回傳非成功狀態時拋出。"""


class RateLimitError(FinMindError):
    """達到 FinMind 流量上限（HTTP 402 或本地節流擋下）。"""


class _SlidingWindowLimiter:
    """本地滑動視窗節流：限制每小時最多 N 次請求，避免打爆 FinMind。"""

    def __init__(self, max_per_hour: int, window_seconds: float = 3600.0) -> None:
        self._max = max_per_hour
        self._window = window_seconds
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            # 移除視窗外的紀錄
            while self._calls and now - self._calls[0] > self._window:
                self._calls.popleft()
            if len(self._calls) >= self._max:
                wait = self._window - (now - self._calls[0])
                raise RateLimitError(
                    f"本地節流：已達每小時 {self._max} 次上限，約 {wait:.0f} 秒後可再試"
                )
            self._calls.append(now)


class FinMindClient:
    def __init__(self) -> None:
        self._base_url = settings.finmind_base_url
        self._token = settings.finmind_token
        self._limiter = _SlidingWindowLimiter(settings.finmind_max_requests_per_hour)
        self._client = httpx.Client(timeout=settings.finmind_timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def get_dataset(
        self,
        dataset: str,
        *,
        data_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """呼叫 /data 端點，回傳 DataFrame（可能為空）。"""
        params: dict[str, str] = {"dataset": dataset}
        if data_id:
            params["data_id"] = data_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if self._token:
            params["token"] = self._token

        self._limiter.acquire()

        try:
            resp = self._client.get(f"{self._base_url}/data", params=params)
        except httpx.HTTPError as exc:
            raise FinMindError(f"FinMind 連線失敗：{exc}") from exc

        if resp.status_code == 402:
            raise RateLimitError("FinMind 回傳 402：已達 API 流量上限，請稍後再試或設定 token")
        if resp.status_code != 200:
            raise FinMindError(f"FinMind HTTP {resp.status_code}: {resp.text[:200]}")

        payload = resp.json()
        if payload.get("status") != 200:
            raise FinMindError(f"FinMind 回應錯誤：{payload.get('msg')}")

        data = payload.get("data", [])
        logger.info("FinMind %s data_id=%s → %d 筆", dataset, data_id, len(data))
        return pd.DataFrame(data)


# 單例：整個 app 共用一個 client（含節流狀態）
finmind_client = FinMindClient()
