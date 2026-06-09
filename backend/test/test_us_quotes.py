"""测试美股行情接口（腾讯源 + 新浪源）"""

import asyncio
import json
import urllib.request

BASE_URL = "http://localhost:8000"

TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "QQQ", "SPY"]


def test_api():
    """测试 API 接口（默认腾讯源）"""
    url = f"{BASE_URL}/api/v1/stock/quotes/US?codes={','.join(TICKERS)}"
    print(f"请求: {url}")
    resp = urllib.request.urlopen(url, timeout=30)
    data = json.loads(resp.read().decode())["data"]
    print(f"返回 {len(data)} 条:")
    for q in data:
        print(f"  {q['ticker']}: {q['price']} ({q['name']}) source={q['source']}")


async def test_sina():
    """直接调用 SinaDataSource 测试新浪源"""
    from app.core.data_sources import SinaDataSource

    ds = SinaDataSource()
    print("\n--- 新浪源 ---")
    results = await ds.fetch(TICKERS, market="US")
    await ds.close()
    print(f"返回 {len(results)} 条:")
    for q in results:
        print(f"  {q.ticker}: {q.price} ({q.name}) source={q.source}")


async def test_tencent():
    """直接调用 TencentDataSource 测试腾讯源"""
    from app.core.data_sources import TencentDataSource

    ds = TencentDataSource()
    print("\n--- 腾讯源 ---")
    results = await ds.fetch(TICKERS, market="US")
    print(f"返回 {len(results)} 条:")
    for q in results:
        print(f"  {q.ticker}: {q.price} ({q.name}) source={q.source}")


if __name__ == "__main__":
    print(f"测试 {len(TICKERS)} 个美股\n")
    test_api()
    asyncio.run(test_tencent())
    asyncio.run(test_sina())
