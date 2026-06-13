"""从雪球抓取美股品种公司概况，并入库到 asset_varieties。

仅处理美股（NASDAQ / NYSE），写入 market=US, asset_class=STOCK, currency=USD。

用法：
    .venv/bin/python backend/script/seed_us_variety.py SPCX
    .venv/bin/python backend/script/seed_us_variety.py SPCX CRCL    # 一次多个

抓取流程：
1. 调用 test_xueqiu.fetch_company_info(ticker) 获取雪球公司概况表
2. 取 "英文名称" 作为 name（项目美股目录统一用英文名）
3. INSERT 或 UPDATE asset_varieties；is_active=True

依赖：必须先 playwright install chromium
"""

import asyncio
import sys
from pathlib import Path

# 把项目根加到 sys.path 让 backend.test.test_xueqiu 可被 import
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.orm.asset_variety_orm import AssetVarietyRecord  # noqa: E402
from backend.test.test_xueqiu import fetch_company_info  # noqa: E402


def _row_value(rows: list[dict], key: str) -> str:
    """从 [{item, value}] 列表里取指定字段"""
    for r in rows:
        if r["item"] == key:
            return r["value"].strip()
    return ""


async def seed_one(ticker: str) -> None:
    """抓取并入库单个 ticker（仅美股）"""
    print(f"\n📡 抓取 {ticker} ...")
    rows = await fetch_company_info(ticker)
    if not rows:
        print(f"  ❌ 雪球未返回数据，跳过")
        return

    en_name = _row_value(rows, "英文名称")
    if not en_name:
        print(f"  ❌ 英文名称为空，跳过")
        return

    print(f"  英文名: {en_name}")

    # 入库（market=US, asset_class=STOCK, currency=USD）
    async with async_session() as session:
        existing = (await session.execute(
            select(AssetVarietyRecord).where(
                AssetVarietyRecord.ticker == ticker,
                AssetVarietyRecord.asset_class == "STOCK",
                AssetVarietyRecord.market == "US",
            )
        )).scalar_one_or_none()

        if existing:
            existing.name = en_name
            existing.is_active = True
            await session.commit()
            print(f"  ✅ 已更新（id={existing.id}）")
        else:
            record = AssetVarietyRecord(
                ticker=ticker,
                name=en_name,
                market="US",
                asset_class="STOCK",
                sub_category=None,
                currency="USD",
                is_active=True,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            print(f"  ✅ 已新增（id={record.id}）")


async def main(tickers: list[str]) -> None:
    if not tickers:
        print("用法: .venv/bin/python backend/script/seed_us_variety.py TICKER [TICKER...]")
        sys.exit(1)
    for ticker in tickers:
        try:
            await seed_one(ticker.strip().upper())
        except Exception as e:
            print(f"  ❌ {ticker} 处理失败: {type(e).__name__}: {e}")
    print("\n✅ 全部处理完毕")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
