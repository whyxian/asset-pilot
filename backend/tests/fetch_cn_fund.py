"""获取基金全量列表，保存到 JSON"""

import json
from pathlib import Path

import akshare as ak


def fetch_cn_funds(output_path: str | Path | None = None) -> list[dict]:
    """从 akshare 获取基金全量列表

    Args:
        output_path: 可选的输出文件路径，不为 None 则保存到文件

    Returns:
        基金品种列表 [{ticker, name, market, asset_class, currency}]
    """
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

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"已保存 {len(records)} 条到 {output_path}")

    return records


if __name__ == "__main__":
    default_output = Path(__file__).resolve().parents[2] / "data" / "varieties_funds_akshare.json"
    fetch_cn_funds(default_output)
