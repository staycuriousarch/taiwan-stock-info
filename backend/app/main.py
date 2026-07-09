"""FastAPI 進入點。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.clients.finmind import FinMindError, RateLimitError, finmind_client
from app.core.config import settings
from app.db import duckdb_conn
from app.jobs import scheduler
from app.routers import admin, stocks
from app.services import search

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動：建立 DB、預熱股票代碼索引
    duckdb_conn.get_connection()
    try:
        search.get_index()
    except FinMindError as exc:
        logger.warning("啟動預熱股票索引失敗（稍後首次查詢會重試）：%s", exc)
    scheduler.start_scheduler()  # 每日 09:00 排程 + 開機補跑
    yield
    scheduler.shutdown_scheduler()
    finmind_client.close()


app = FastAPI(title="Financial Info API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitError)
async def _rate_limit_handler(request: Request, exc: RateLimitError):
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.exception_handler(FinMindError)
async def _finmind_error_handler(request: Request, exc: FinMindError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(stocks.router)
app.include_router(admin.router)
