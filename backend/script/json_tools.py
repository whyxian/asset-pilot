"""按名称中是否含中文拆分 / 合并 JSON 数据"""

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
    # split_by_language(
    #     DATA / "varieties_us_stocks_cn_fixed.json",
    #     en_output=DATA / "varieties_us_stocks_cn_fixed_111.json",
    #     cn_output=DATA / "varieties_us_stocks_cn_fixed_222.json",
    # )
    merge_json(
        DATA / "",
        DATA / "",
        DATA / ""
    )
