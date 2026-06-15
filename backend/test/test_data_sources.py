"""数据源解析单元测试 — mock httpx 验证解析/边界/错误处理

执行：
    .venv/bin/pytest test/test_data_sources.py -v
"""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.data_sources import (
    AkshareFundDataSource,
    CoinGlassDataSource,
    EastMoneyFundDataSource,
    TencentDataSource,
)


# ════════════════════════════════════════════════════
# 工具：构造 mock httpx 响应的 async context manager
# ════════════════════════════════════════════════════

def _mock_httpx_client(get_return):
    """构造一个 mock httpx.AsyncClient，get() 返回 get_return"""
    mock_resp = MagicMock()
    if isinstance(get_return, str):
        mock_resp.text = get_return
        mock_resp.json.return_value = json.loads(get_return) if get_return.startswith("{") else {}
    elif isinstance(get_return, dict):
        mock_resp.json.return_value = get_return
        mock_resp.text = json.dumps(get_return)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _make_tencent_a_share_line(code: str, name: str, price: str,
                                change_price: str = "", change_ratio: str = "",
                                field_count: int = 53) -> str:
    """构造腾讯 A 股响应行（~分隔），填充至 field_count 个字段"""
    vals = [""] * field_count
    vals[1] = name
    vals[3] = price
    vals[31] = change_price
    vals[32] = change_ratio
    # key 格式：v_sh600519 等
    prefix = "sh" if code.startswith(("5", "6", "9")) else ("bj" if code.startswith("8") else "sz")
    return f'v_{prefix}{code}="{"~".join(vals)}";'


def _make_tencent_us_stock_line(ticker: str, name: str = "", us_name: str = "",
                                 price: str = "170", currency: str = "USD",
                                 status: str = "200", field_count: int = 47) -> str:
    """构造腾讯美股响应行"""
    vals = [""] * field_count
    vals[0] = status
    vals[1] = name
    vals[2] = f"{ticker}.US"
    vals[3] = price
    vals[6] = "1000000"
    vals[31] = "2.5"
    vals[32] = "1.5"
    vals[35] = currency
    vals[46] = us_name or name
    return f'v_us{ticker}="{"~".join(vals)}";'


# ════════════════════════════════════════════════════
# TencentDataSource — A 股
# ════════════════════════════════════════════════════

async def test_tencent_a_shares_prefix():
    """前缀逻辑：6→sh, 0→sz, 8→bj"""
    ds = TencentDataSource()
    # 构造三条 A 股数据
    body = (
        _make_tencent_a_share_line("600519", "贵州茅台", "1800.00", "20.00", "1.12")
        + _make_tencent_a_share_line("000001", "平安银行", "12.50", "0.30", "2.46")
        + _make_tencent_a_share_line("830799", "艾融软件", "25.00")
    )

    mp = pytest.MonkeyPatch()
    mp.setattr("httpx.AsyncClient", lambda **kw: _mock_httpx_client(body))
    try:
        result = await ds.fetch(["600519", "000001", "830799"], market="CN")
    finally:
        mp.undo()

    assert len(result) == 3
    tickers = {q.ticker for q in result}
    assert tickers == {"600519", "000001", "830799"}
    # 验证解析值
    moutai = next(q for q in result if q.ticker == "600519")
    assert moutai.name == "贵州茅台"
    assert moutai.price == Decimal("1800.00")
    assert moutai.change_price == Decimal("20.00")
    assert moutai.change_ratio == 1.12


async def test_tencent_a_shares_short_line():
    """字段数 <53 的行被跳过"""
    ds = TencentDataSource()
    # 只给 10 个字段，远不够 53
    bad_line = 'v_sh600519="a~b~c~d~e~f~g~h~i~j";'
    # 再加一条正常的
    good_line = _make_tencent_a_share_line("000001", "平安银行", "12.50")

    mp = pytest.MonkeyPatch()
    mp.setattr("httpx.AsyncClient", lambda **kw: _mock_httpx_client(bad_line + good_line))
    try:
        result = await ds.fetch(["600519", "000001"], market="CN")
    finally:
        mp.undo()

    # 只解析出 1 条正常的
    assert len(result) == 1
    assert result[0].ticker == "000001"


# ════════════════════════════════════════════════════
# TencentDataSource — 美股
# ════════════════════════════════════════════════════

async def test_tencent_us_stocks_parse():
    """美股正常解析 + 非 200 状态行被跳过"""
    ds = TencentDataSource()
    ok_line = _make_tencent_us_stock_line("AAPL", name="AAPL", us_name="Apple Inc", price="170.50")
    # 状态码不是 200 的行
    fail_line = _make_tencent_us_stock_line("FAIL", status="404", price="0")

    mp = pytest.MonkeyPatch()
    mp.setattr("httpx.AsyncClient", lambda **kw: _mock_httpx_client(ok_line + fail_line))
    try:
        result = await ds.fetch(["AAPL", "FAIL"], market="US")
    finally:
        mp.undo()

    assert len(result) == 1
    assert result[0].ticker == "AAPL"
    assert result[0].price == Decimal("170.50")
    assert result[0].currency == "USD"


# ════════════════════════════════════════════════════
# CoinGlassDataSource
# ════════════════════════════════════════════════════

async def test_coinglass_parse():
    """JSON 解析 + change_price = price * changePct / 100"""
    ds = CoinGlassDataSource()
    response_data = {
        "code": "0",
        "data": {
            "name": "Bitcoin",
            "price": 100000.50,
            "priceChangePercent24h": 2.5,
            "volUsd": 50000000000,
        },
    }

    mp = pytest.MonkeyPatch()
    mp.setattr("httpx.AsyncClient", lambda **kw: _mock_httpx_client(response_data))
    try:
        result = await ds.fetch(["BTC"], market="CRYPTO")
    finally:
        mp.undo()

    assert len(result) == 1
    q = result[0]
    assert q.ticker == "BTC"
    assert q.price == Decimal("100000.50")
    assert q.name == "Bitcoin"
    # change_price = 100000.50 * 2.5 / 100 = 2500.00125 → quantize 0.01 = 2500.01
    assert q.change_price is not None
    assert abs(q.change_price - Decimal("2500.01")) < Decimal("0.01")
    assert q.change_ratio == 2.5


async def test_coinglass_error_code():
    """code != "0" → 返回 None，最终从结果中过滤掉"""
    ds = CoinGlassDataSource()
    response_data = {"code": "1", "data": {}}

    mp = pytest.MonkeyPatch()
    mp.setattr("httpx.AsyncClient", lambda **kw: _mock_httpx_client(response_data))
    try:
        result = await ds.fetch(["UNKNOWN"], market="CRYPTO")
    finally:
        mp.undo()

    assert len(result) == 0


# ════════════════════════════════════════════════════
# EastMoneyFundDataSource
# ════════════════════════════════════════════════════

async def test_eastmoney_parse_js():
    """JS 正则解析 + NAV 涨跌计算"""
    ds = EastMoneyFundDataSource()
    import time
    ts = int(time.time() * 1000)  # 毫秒时间戳

    js_text = f'''
var fS_name = "华夏成长";
var Data_netWorthTrend = [{{"x":{ts - 86400000},"y":1.5,"equityReturn":0}},{{"x":{ts},"y":1.55,"equityReturn":0.0333}}];
'''
    mp = pytest.MonkeyPatch()
    mp.setattr("httpx.AsyncClient", lambda **kw: _mock_httpx_client(js_text))
    try:
        result = await ds.fetch(["000001"], market="CN")
    finally:
        mp.undo()

    assert len(result) == 1
    q = result[0]
    assert q.ticker == "000001"
    assert q.name == "华夏成长"
    assert q.price == Decimal("1.55")
    # change = 1.55 - 1.50 = 0.05
    assert q.change_price == Decimal("0.05")
    # change_ratio = (0.05 / 1.50) * 100 ≈ 3.333
    assert q.change_ratio is not None
    assert abs(q.change_ratio - 3.33) < 0.1


async def test_eastmoney_single_nav():
    """只有 1 条 NAV → change_price / change_ratio 为 None"""
    ds = EastMoneyFundDataSource()
    import time
    ts = int(time.time() * 1000)

    js_text = f'''
var fS_name = "单条基金";
var Data_netWorthTrend = [{{"x":{ts},"y":1.20,"equityReturn":0}}];
'''
    mp = pytest.MonkeyPatch()
    mp.setattr("httpx.AsyncClient", lambda **kw: _mock_httpx_client(js_text))
    try:
        result = await ds.fetch(["000002"], market="CN")
    finally:
        mp.undo()

    assert len(result) == 1
    assert result[0].change_price is None
    assert result[0].change_ratio is None


# ════════════════════════════════════════════════════
# AkshareFundDataSource
# ════════════════════════════════════════════════════

async def test_akshare_parse_dataframe():
    """mock ak.fund_open_fund_info_em 返回 DataFrame → 正确解析"""
    import pandas as pd

    ds = AkshareFundDataSource()

    df = pd.DataFrame({
        "净值日期": ["2026-06-13", "2026-06-14"],
        "单位净值": [1.50, 1.55],
        "累计净值": [1.50, 1.55],
    })

    mp = pytest.MonkeyPatch()
    mp.setattr("akshare.fund_open_fund_info_em", lambda symbol: df)
    try:
        result = await ds.fetch(["000001"], market="CN")
    finally:
        mp.undo()

    assert len(result) == 1
    q = result[0]
    assert q.ticker == "000001"
    assert q.price == Decimal("1.55")
    assert q.change_price == Decimal("0.05")
    assert q.change_ratio is not None
    assert abs(q.change_ratio - 3.33) < 0.1
