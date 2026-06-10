"""JSON 工具集合：按语言拆分 / 合并 / 批量重命名 key"""

import json
import re
from pathlib import Path


def split_by_language(
    input_path: str | Path,
    en_output: str | Path | None = None,
    cn_output: str | Path | None = None,
) -> tuple[list, list]:
    """按名称语言拆分数据

    Args:
        input_path: 输入 JSON 文件路径
        en_output: 英文名输出路径（可选）
        cn_output: 中文名输出路径（可选）

    Returns:
        (英文名列表, 中文名列表)
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    en = [item for item in data if not re.search(r"[一-鿿]", item["name"])]
    cn = [item for item in data if re.search(r"[一-鿿]", item["name"])]

    if en_output:
        with open(en_output, "w", encoding="utf-8") as f:
            json.dump(en, f, ensure_ascii=False, indent=2)
    if cn_output:
        with open(cn_output, "w", encoding="utf-8") as f:
            json.dump(cn, f, ensure_ascii=False, indent=2)

    print(f"总 {len(data)} 条 → 英文 {len(en)} 条, 中文 {len(cn)} 条")
    return en, cn


FUND_KEYWORDS = [
    # 通用基金标识词（不会出现在股票公司名中）
    "ETF", "Etf", "Fund", "Trust", "ETN",
    "Bond", "Bonds", "Yield", "Dividend", "Income",
    "Portfolio", "Strategy", "Leveraged", "Inverse",
    "Treasury", "Corporate", "Municipal", "High Yield",
    "Preferred", "Realty", "Real Estate",
    # 纯基金品牌（无同名股票公司）
    "iShares", "ProShares", "Direxion", "VanEck", "WisdomTree",
    "Global X", "First Trust", "Amplify", "Innovator",
    "Simplify", "Mirae", "ALPS", "AdvisorShares",
    "Kurv", "NEOS", "Roundhill", "GraniteShares", "YieldMax",
    "Tidal", "Rareview", "Defiance", "Merlyn.AI", "PIMCO",
]


def split_stock_vs_fund(
    input_path: str | Path,
    stock_output: str | Path | None = None,
    fund_output: str | Path | None = None,
    fund_keywords: list[str] | None = None,
    set_asset_class: bool = True,
) -> tuple[list, list]:
    """按名称关键词区分股票和基金/ETF，可选更新 asset_class

    Args:
        input_path: 输入 JSON 文件路径（所有项 asset_class 均为 "STOCK"）
        stock_output: 纯股票输出路径（默认覆盖原文件）
        fund_output: 基金/ETF 输出路径（默认覆盖原文件）
        fund_keywords: 自定义基金关键词列表，默认用 FUND_KEYWORDS
        set_asset_class: 如为 True，将基金项的 asset_class 设为 "FUND"

    Returns:
        (股票列表, 基金列表)
    """
    kw = fund_keywords or FUND_KEYWORDS

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stocks, funds = [], []
    for item in data:
        name = item.get("name", "")
        if any(k in name for k in kw):
            if set_asset_class:
                item["asset_class"] = "FUND"
            funds.append(item)
        else:
            stocks.append(item)

    if stock_output:
        with open(stock_output, "w", encoding="utf-8") as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
    if fund_output:
        with open(fund_output, "w", encoding="utf-8") as f:
            json.dump(funds, f, ensure_ascii=False, indent=2)

    print(f"完成: 总 {len(data)} 条 → 股票 {len(stocks)} 条, 基金/ETF {len(funds)} 条")
    if set_asset_class:
        print(f"  (基金项 asset_class 已设为 FUND)")
    return stocks, funds


def merge_json(
    file_a: str | Path,
    file_b: str | Path,
    output: str | Path,
) -> list:
    """合并两个 JSON 文件（直接拼接，不去重）

    Args:
        file_a: 第一个 JSON 文件
        file_b: 第二个 JSON 文件
        output: 输出路径

    Returns:
        合并后的列表
    """
    with open(file_a, "r", encoding="utf-8") as f:
        data_a = json.load(f)
    with open(file_b, "r", encoding="utf-8") as f:
        data_b = json.load(f)

    merged = data_a + data_b

    with open(output, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"A {len(data_a)} 条 + B {len(data_b)} 条 = {len(merged)} 条 → {output}")
    return merged


if __name__ == "__main__":
    DATA = Path(__file__).resolve().parents[2] / "data"

    # 用法示例：
    # merge_json("a.json", "b.json", "merged.json")
    # split_by_language("data.json", en_output="en.json", cn_output="cn.json")
