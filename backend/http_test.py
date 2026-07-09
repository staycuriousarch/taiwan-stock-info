"""HTTP 層測試：用 TestClient 打端點，確認路由與序列化。"""
from fastapi.testclient import TestClient

from app.main import app

with TestClient(app) as client:
    r = client.get("/health")
    print("GET /health →", r.status_code, r.json())

    r = client.get("/api/search", params={"q": "鴻海"})
    print("GET /api/search?q=鴻海 →", r.status_code, r.json()["results"][:1])

    r = client.get("/api/stock/2317/technical")
    body = r.json()
    print("GET /api/stock/2317/technical →", r.status_code,
          "| summary keys:", list(body["summary"].keys()),
          "| series 筆數:", len(body["series"]))

    r = client.get("/api/stock/2330/overview")
    print("GET /api/stock/2330/overview →", r.status_code,
          "| 面向:", list(r.json().keys()))
