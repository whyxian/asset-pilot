"""雪球个股公司概况抓取"""

import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright


async def fetch_company_info(ticker: str) -> list[dict]:
    """从雪球抓取个股公司概况

    Args:
        ticker: 美股代码, 如 "VLRS"

    Returns:
        [{item, value}, ...]
    """
    url = f"https://xueqiu.com/snowman/S/{ticker}/detail#/GSJJ"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000, wait_until="networkidle")
        try:
            await page.wait_for_selector("table.table-bordered.table-hover.gsjj", timeout=15000)
        except Exception:
            print(f"[xueqiu] {ticker}: 未找到公司概况表格")
            await browser.close()
            return []

        rows = await page.query_selector_all("table.table-bordered.table-hover.gsjj tr")
        result = []
        for row in rows:
            tds = await row.query_selector_all("td")
            if len(tds) >= 2:
                item = (await tds[0].inner_text()).strip()
                value = (await tds[1].inner_text()).strip()
                result.append({"item": item, "value": value})

        await browser.close()
        return result


async def fetch_english_name(ticker: str) -> str | None:
    """从雪球获取个股英文名称

    Args:
        ticker: 美股代码

    Returns:
        英文名称, 获取失败返回 None
    """
    info = await fetch_company_info(ticker)
    for row in info:
        if row["item"] == "英文名称":
            return row["value"]
    return None


async def batch_fetch_names(
    input_path: str | Path,
    en_output: str | Path | None = None,
    cn_output: str | Path | None = None,
    max_count: int = 0,
    concurrency: int = 3,
) -> list:
    """从 JSON 读取 ticker，并发查雪球英文名

    Args:
        input_path: 输入 JSON，需含 ticker + name 字段
        en_output: 完成后的英文名输出路径（可选）
        cn_output: 完成后剩余中文名输出路径（可选）
        max_count: 最大处理条数，0 表示全部
        concurrency: 并发数（同时开几个浏览器页面）
    """
    input_path = Path(input_path)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    todo = [item for item in data if re.search(r"[一-鿿]", item["name"])]
    if max_count:
        todo = todo[:max_count]

    total = len(todo)
    print(f"总 {len(data)} 条, 待处理 {total} 条, 并发 {concurrency}")

    sem = asyncio.Semaphore(concurrency)
    processed = 0

    async def fetch_one(item: dict) -> dict:
        nonlocal processed
        ticker = item["ticker"]
        async with sem:
            try:
                en = await fetch_english_name(ticker)
                if en:
                    item["name"] = en
                    print(f"  [{processed}/{total}] {ticker} → {en}")
                else:
                    print(f"  [{processed}/{total}] {ticker} → 无数据")
            except Exception as e:
                print(f"  [{processed}/{total}] {ticker} → 失败: {e}")
            processed += 1

            if processed % 10 == 0 or processed == total:
                with open(input_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            await asyncio.sleep(1)

    await asyncio.gather(*[fetch_one(item) for item in todo])

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 拆分成英文/中文两个文件
    en_list = [item for item in data if not re.search(r"[一-鿿]", item["name"])]
    cn_list = [item for item in data if re.search(r"[一-鿿]", item["name"])]
    if en_output:
        with open(en_output, "w", encoding="utf-8") as f:
            json.dump(en_list, f, ensure_ascii=False, indent=2)
    if cn_output:
        with open(cn_output, "w", encoding="utf-8") as f:
            json.dump(cn_list, f, ensure_ascii=False, indent=2)

    print(f"\n完成！英文 {len(en_list)} 条, 剩余中文 {len(cn_list)} 条")
    return data


if __name__ == "__main__":
    DATA = Path("/home/xian/workspace/01-ai/03-asset-pilot/data")
    asyncio.run(batch_fetch_names(
        DATA / "varieties_us_stocks_cn_fixed.json",
        en_output=DATA / "varieties_us_stocks_en.json",
        cn_output=DATA / "varieties_us_stocks_cn_left.json",
        max_count=0,
        concurrency=3,
    ))
