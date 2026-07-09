# 後端：FastAPI + uv
FROM python:3.12-slim

# 從官方 uv 映像複製 uv 二進位（推薦做法，免自行安裝）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# 先裝依賴，利用 layer cache（程式碼變動時不用重裝）
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 再複製應用程式碼
COPY app ./app

# DuckDB 資料目錄（compose 會掛 volume 到這）
RUN mkdir -p data

EXPOSE 8000

# 0.0.0.0 讓容器外可連
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
