"""API 路由层集成测试（代表性端点）— 统一返回格式 / 错误码 / 路由可达性

用 httpx ASGITransport 直连 FastAPI app（不触发 lifespan，不启动调度器）。
2026-08-04 盘点后补：覆盖 8 个路由中不触网的代表性端点 + 全局异常处理格式。
"""

import httpx
import pytest
from httpx import ASGITransport

from app.core.error_codes import CODE_VALIDATION
from app.main import app
from test.conftest import approx


@pytest.fixture
async def client(Session):
    """依赖 Session 触发 conftest 的 async_session patch（否则 API 会连真实数据库）"""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ════════════════════════════════════════════════════
# 统一返回格式
# ════════════════════════════════════════════════════

async def test_success_response_format(client):
    """GET /holdings：code=0 + data 列表"""
    r = await client.get("/api/v1/holdings")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert body["data"] == []


async def test_business_error_format(client):
    """未建仓录交易 → code=40001 + message（HTTP 200，业务码在 body）"""
    r = await client.post("/api/v1/transactions", json={
        "ticker": "TEST", "asset_class": "STOCK", "market": "CN",
        "transaction_date": "2026-08-01", "type": "buy",
        "quantity": "10", "unit_price": "10",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == CODE_VALIDATION
    assert "请先在持仓页新增" in body["message"]
    assert body["data"] is None


async def test_not_found_error_format(client):
    """不存在路由 → HTTPException 转统一格式（code=404）"""
    r = await client.get("/api/v1/not-exist")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 404
    assert body["data"] is None


async def test_validation_error_format(client):
    """非法参数（缺必填 query）→ FastAPI 422（RequestValidationError 走 FastAPI 内置格式）"""
    r = await client.get("/api/v1/varieties/search")
    assert r.status_code == 422
    assert "detail" in r.json()


# ════════════════════════════════════════════════════
# 代表性业务端点
# ════════════════════════════════════════════════════

async def test_variety_create_and_search(client):
    """品种：POST 创建 → GET 搜索命中"""
    r = await client.post("/api/v1/varieties", json={
        "ticker": "TEST", "name": "测试品种", "market": "CN", "asset_class": "STOCK",
    })
    assert r.status_code == 201
    assert r.json()["code"] == 0

    r = await client.get("/api/v1/varieties/search", params={"q": "TEST"})
    assert r.json()["code"] == 0
    tickers = [v["ticker"] for v in r.json()["data"]]
    assert "TEST" in tickers


async def test_cash_balances_with_mocked_rates(client, monkeypatch):
    """现金余额：mock 汇率 → 空账户 total=0 + 汇率日期透传"""
    from app.utils.exchange_rate import RatesSnapshot

    async def fake_fetch_rates():
        return RatesSnapshot(rates={"USD": 1.0, "CNY": 7.2}, source_date="2026-08-04", is_stale=False)
    monkeypatch.setattr("app.services.cash_flow_service.fetch_rates", fake_fetch_rates)

    r = await client.get("/api/v1/cash/balances", params={"currency": "CNY"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["total"] == "0"
    assert body["data"]["display_currency"] == "CNY"
    assert body["data"]["rate_stale"] is False


async def test_cash_deposit_and_balances(client, monkeypatch):
    """现金：入金 → 余额反映"""
    from app.utils.exchange_rate import RatesSnapshot

    async def fake_fetch_rates():
        return RatesSnapshot(rates={"USD": 1.0, "CNY": 7.2}, source_date="2026-08-04", is_stale=False)
    monkeypatch.setattr("app.services.cash_flow_service.fetch_rates", fake_fetch_rates)

    r = await client.post("/api/v1/cash/deposit", json={"amount": "1000", "currency": "CNY"})
    assert r.status_code == 200
    assert r.json()["code"] == 0

    r = await client.get("/api/v1/cash/balances")
    body = r.json()
    assert approx(body["data"]["total"], "1000")


async def test_transaction_list_paginated(client):
    """交易列表：统一分页结构"""
    r = await client.get("/api/v1/transactions", params={"page": 1, "page_size": 20})
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["data"] == []
    assert body["data"]["total"] == 0
    assert body["data"]["page"] == 1
