"""用合并后的 ETF 数据替换 DB 中的重复记录"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import delete, select, func

from app.core.database import async_session
from app.models.asset_variety import AssetVarietyCreate
from app.models.orm.asset_variety_orm import AssetVarietyRecord
from app.repositories.asset_variety_repository import AssetVarietyRepository

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MERGED_FILE = DATA_DIR / "merged_etf_fund.json"

repo = AssetVarietyRepository()


async def main():
    with open(MERGED_FILE, "r") as f:
        records = json.load(f)

    tickers = [r["ticker"] for r in records]
    print(f"待处理 {len(records)} 条（涉及 {len(set(tickers))} 个 ticker）")

    # 1. 删除这些 ticker 的所有旧记录
    async with async_session() as session:
        result = await session.execute(
            delete(AssetVarietyRecord).where(AssetVarietyRecord.ticker.in_(tickers))
        )
        await session.commit()
        deleted = result.rowcount
        print(f"已删除 {deleted} 条旧记录")

    # 2. 插入合并后的新记录
    added = 0
    for r in records:
        data = AssetVarietyCreate(
            ticker=r["ticker"],
            name=r["name"],
            market=r["market"],
            asset_class=r["asset_class"],
            sub_category=r.get("sub_category"),
            currency="CNY",
        )
        await repo.create_variety(data)
        added += 1

    print(f"已插入 {added} 条合并记录")

    # 3. 验证
    async with async_session() as session:
        remaining = (await session.execute(
            select(func.count()).select_from(AssetVarietyRecord).where(
                AssetVarietyRecord.ticker.in_(tickers)
            )
        )).scalar()
        print(f"验证：处理后这些 ticker 共 {remaining} 条（应为 {added}）")


if __name__ == "__main__":
    asyncio.run(main())
