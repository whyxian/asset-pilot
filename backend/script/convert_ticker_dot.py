"""读取东方财富美股数据，将 ticker 中的 _ 替换为 .，保存到新文件"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "source"

INPUT = DATA_DIR / "varieties_us_stocks_east.json"
OUTPUT = DATA_DIR / "varieties_us_stocks_east_dot.json"

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

changed = 0
for item in data:
    old = item["ticker"]
    new = old.replace("_", ".")
    if old != new:
        item["ticker"] = new
        changed += 1

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"总条数: {len(data)}")
print(f"修改了 {changed} 个 ticker")
print(f"已保存到 {OUTPUT.name}")
