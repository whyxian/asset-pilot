"""用新浪源批量获取美股英文名称"""

import asyncio
import json
import re
import time
from pathlib import Path

from app.core.data_sources import SinaDataSource


async def fetch_us_names(
    input_path: str | Path,
    output_path: str | Path,
    batch: int = 10,
    save_interval: int = 5,
) -> list:
    """用新浪源批量获取美股英文名称

    Args:
        input_path: 输入 JSON（含中文名的数据）
        output_path: 输出 JSON 路径
        batch: 每批处理的 ticker 数
        save_interval: 每多少批保存一次进度

    Returns:
        处理后的完整数据列表
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    todo = [item for item in data if re.search(r"[一-鿿]", item["name"])]
    total = len(todo)
    print(f"总 {len(data)} 条, 待处理 {total} 条")

    ds = SinaDataSource()

    for start in range(0, total, batch):
        items = todo[start:start + batch]
        tickers = [item["ticker"] for item in items]

        try:
            quotes = await ds.fetch(tickers, market="US")
            qmap = {q.ticker: q.name for q in quotes}
            for item in items:
                if item["ticker"] in qmap:
                    item["name"] = qmap[item["ticker"]]
            print(f"  [{min(start + batch, total)}/{total}] {' '.join(tickers)}")
        except Exception as e:
            print(f"  [{start + 1}/{total}] 失败: {e}")

        if (start // batch + 1) % save_interval == 0 or start + batch >= total:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        await asyncio.sleep(1)

    await ds.close()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    remaining = sum(1 for item in data if re.search(r"[一-鿿]", item["name"]))
    print(f"\n完成！剩余中文名: {remaining} 条")
    return data


if __name__ == "__main__":
    DATA = Path(__file__).resolve().parents[2] / "data"
    asyncio.run(fetch_us_names(
        DATA / "varieties_us_stocks_cn_left.json",
        DATA / "varieties_us_stocks_cn_fixed.json",
    ))
