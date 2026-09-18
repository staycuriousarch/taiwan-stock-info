# 台股資訊查詢網站

輸入股票代碼或公司名稱，查詢基本面、技術面、籌碼面、新聞四面向資訊。
資料來源：[FinMind](https://finmind.github.io/)。

- 後端：FastAPI + DuckDB 快取 + APScheduler 每日更新
- 前端：React + Vite + TypeScript + lightweight-charts K 線圖

## 專案結構

| 目錄 | 內容 |
|---|---|
| `backend/` | 個股查詢 API（FastAPI + FinMind） |
| `frontend/` | 前端網站（React + Vite） |
| `el/` | **第二階段**：全市場資金流 pipeline 的 EL 層（見 [`el/README.md`](el/README.md)） |

第二階段要做個股熱力圖與產業資金流泡泡圖，需要**全市場橫切面**資料。
FinMind 免費層不支援不帶 `data_id` 的批次查詢（會回 HTTP 400），因此
改走證交所／櫃買的開放資料，並獨立成 `el/` 專案；`backend/` 的個股查詢
管線維持原樣、不受影響。

## 方式一：Docker Compose（一鍵啟動）

需先安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。
FinMind token 請放在 `backend/.env`（`FINMIND_TOKEN=...`）。

```bash
docker compose up --build
```

- 前端： http://localhost:8080
- 後端 API 文件： http://localhost:8000/docs

停止：`docker compose down`（保留快取資料）。
清掉快取資料一起刪：`docker compose down -v`。

## 方式二：原生開發（熱重載）

**後端**（需 [uv](https://docs.astral.sh/uv/)）：

```bash
cd backend
uv run uvicorn app.main:app --reload
```

**前端**（需 Node 20.19+ / 22.12+）：

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

前端開發伺服器會把 `/api` 代理到後端（見 `frontend/vite.config.ts`）。

## 每日更新快取

- 排程：每天 09:00（台北）自動更新種子清單與查詢過的股票。
- 開機補跑：server 啟動時若當天尚未更新，會自動補跑一次。
- 手動觸發：`cd backend && uv run python -m app.jobs.daily_update`
  或 `POST /api/admin/refresh`；狀態查詢 `GET /api/admin/status`。

## 主要 API

| 端點 | 說明 |
|---|---|
| `GET /api/search?q=台積電` | 代碼/名稱模糊搜尋 |
| `GET /api/stock/{id}/overview` | 四面向摘要 |
| `GET /api/stock/{id}/technical` | 股價序列 + 均線（K 線圖用） |
| `GET /api/stock/{id}/fundamental` `.../chips` `.../news` | 各面向明細 |
| `POST /api/admin/refresh` · `GET /api/admin/status` | 手動更新 / 狀態 |
