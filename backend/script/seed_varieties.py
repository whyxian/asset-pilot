"""将 JSON 品种数据导入数据库"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import async_session
from app.models.orm.asset_variety_orm import AssetVarietyRecord

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "source"


async def import_json(file_name: str, label: str):
    """从 JSON 文件导入品种到 asset_varieties 表"""
    path = DATA_DIR / file_name
    if not path.exists():
        print(f"文件不存在: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)

    added = 0
    skipped = 0
    total = len(records)

    async with async_session() as session:
        for idx, r in enumerate(records, 1):
            result = await session.execute(
                select(AssetVarietyRecord).where(
                    AssetVarietyRecord.asset_class == r.get("asset_class", "STOCK"),
                    AssetVarietyRecord.market == r["market"],
                    AssetVarietyRecord.ticker == r["ticker"],
                )
            )
            if result.scalar_one_or_none():
                skipped += 1
            else:
                record = AssetVarietyRecord(
                    ticker=r["ticker"],
                    name=r["name"],
                    market=r["market"],
                    asset_class=r.get("asset_class", "STOCK"),
                    currency=r.get("currency", "USD"),
                )
                session.add(record)
                added += 1

            if idx % 1000 == 0 or idx == total:
                print(f"  [{label}] {idx}/{total} → 新增 {added}, 跳过 {skipped}")

        await session.commit()

    print(f"[{label}] 完成: 总 {total} → 新增 {added}, 跳过 {skipped}")


async def main():
    await import_json("varieties_funds_akshare.json", "A股")


if __name__ == "__main__":
    asyncio.run(main())
