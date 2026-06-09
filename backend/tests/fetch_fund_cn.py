"""获取基金全量列表，保存到 JSON"""

import json
from pathlib import Path

import akshare as ak

OUTPUT = Path(__file__).resolve().parents[2] / "data" / "varieties_funds_akshare.json"

df = ak.fund_name_em()
print(f"总行数: {len(df)}")

records = []
for _, row in df.iterrows():
    records.append({
        "ticker": str(row["基金代码"]).strip().zfill(6),
        "name": str(row["基金简称"]).strip(),
        "market": "CN",
        "asset_class": "FUND",
        "currency": "CNY",
    })

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"已保存 {len(records)} 条到 {OUTPUT.name}")
