"""接口测试 — 调用运行中的 FastAPI 服务，测试行情 + 持仓接口"""

import json
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"


def format_change(val):
    """正数前面加 +"""
    if val is None:
        return "-"
    if isinstance(val, (int, float)) and val > 0:
        return f"+{val}"
    return str(val)


def print_quote(q: dict, unit: str):
    """打印 AssetQuote 所有字段"""
    print(f"  ticker: {q['ticker']}")
    print(f"  market: {q['market']}")
    print(f"  name: {q['name']}")
    print(f"  price: {q['price']}{unit}")
    print(f"  currency: {q['currency']}")
    print(f"  change_price: {format_change(q['change_price'])}")
    print(f"  change_ratio: {format_change(q['change_ratio'])}%")
    print(f"  updated_at: {q['updated_at']}")
    print(f"  source: {q['source']}")
    print()


def fetch_json(url: str):
    """请求接口并解包统一返回格式"""
    resp = urllib.request.urlopen(url, timeout=20)
    body = json.loads(resp.read().decode())
    return body["data"]


def test_quotes():
    """测试行情接口"""
    tests = [
        ("CN", f"{BASE_URL}/api/v1/stock/quotes/CN?codes=600519,000001,688017", "元"),
        ("US", f"{BASE_URL}/api/v1/stock/quotes/US?codes=AAPL,MSFT,GOOG", "美元"),
        ("CRYPTO", f"{BASE_URL}/api/v1/crypto/quotes?coins=BTC,ETH,SOL", "美元"),
        ("FUND", f"{BASE_URL}/api/v1/fund/quotes?codes=166002,110011", "元"),
    ]

    for name, url, unit in tests:
        print(f"--- {name} ---")
        print(f"请求: {url}")
        try:
            data = fetch_json(url)
            print(f"返回 {len(data)} 条:")
            for q in data:
                print_quote(q, unit)
        except urllib.error.HTTPError as e:
            print(f"HTTP 错误: {e.code} {e.reason}")
            print(e.read().decode())
        except urllib.error.URLError as e:
            print(f"连接失败: {e.reason}")
        print()


def test_varieties():
    """测试品种接口"""
    url = f"{BASE_URL}/api/v1/varieties"
    print(f"--- 品种列表 ---")
    print(f"请求: {url}")
    try:
        data = fetch_json(url)
        print(f"返回 {len(data)} 条")
        for v in data[:10]:
            print(f"  {v['ticker']}: {v['name']} ({v['market']})")
        if len(data) > 10:
            print(f"  ... 共 {len(data)} 条")
    except Exception as e:
        print(f"失败: {e}")
    print()


if __name__ == "__main__":
    test_quotes()
    test_varieties()
