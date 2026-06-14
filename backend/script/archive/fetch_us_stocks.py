"""从东方财富 API 获取美股全量列表，保存到 JSON"""

import json
import time
from pathlib import Path

import httpx


def fetch_us_stocks_east(output_path: str | Path | None = None) -> list[dict]:
    """从东方财富 API 获取美股全量列表

    Args:
        output_path: 可选的输出文件路径，不为 None 则保存到文件

    Returns:
        美股品种列表 [{ticker, name, market, asset_class, currency}]
    """
    url = "https://push2.eastmoney.com/weblogin/api/qt/clist/get"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }
    params = {
        "np": 1, "fltt": 1, "invt": 2,
        "fs": "m:105,m:106,m:107",
        "fields": "f12,f13,f14",
        "fid": "f20", "pn": 1, "pz": 100, "po": 1,
        "dect": 1, "ut": "fa5fd1943c7b386f172d689d3bfba10b",
    }

    all_items = []
    page = 1
    total = None

    while True:
        params["pn"] = page
        resp = httpx.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()

        if total is None:
            total = data["data"]["total"]
            print(f"API 总数: {total}")

        if "diff" not in data["data"]:
            break

        items = data["data"]["diff"]
        all_items.extend(items)
        print(f"  第 {page} 页 → {len(items)} 条（累计 {len(all_items)}）")

        if len(all_items) >= total:
            break
        page += 1
        time.sleep(2)

    records = [
        {"ticker": item["f12"], "name": item["f14"], "market": "US", "asset_class": "STOCK", "currency": "USD"}
        for item in all_items
    ]

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"\n已保存 {len(records)} 条到 {output_path}")

    return records


if __name__ == "__main__":
    default_output = Path(__file__).resolve().parents[2] / "data" / "source" / "varieties_us_stocks_east.json"
    fetch_us_stocks_east(default_output)
