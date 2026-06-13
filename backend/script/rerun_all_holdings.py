"""一次性脚本：对全部持仓调用 recompute_holding 重新计算派生字段。

用途：
- 在改了 recompute_holding 算法（如卖出 cost_price 计算规则）之后，
  数据库里现有 holdings 的派生字段（quantity / cost_price / total_invested /
  liquidated_at / first_buy_date）仍是旧算法的结果，需要重算才能反映新算法。
- recompute_holding 是幂等的，重复跑无副作用。

执行方式：
    .venv/bin/python backend/script/rerun_all_holdings.py

事务边界：每个 ticker 独立事务，单个失败不影响其它。
"""

import asyncio

from sqlalchemy import select

from app.core.database import async_session
from app.core.exceptions import BusinessError
from app.models.orm.asset_holding_orm import AssetHoldingRecord
from app.services.asset_holding_service import recompute_holding


async def main():
    async with async_session() as session:
        tickers = (await session.execute(
            select(AssetHoldingRecord.ticker).order_by(AssetHoldingRecord.ticker)
        )).scalars().all()

    if not tickers:
        print("📭 持仓表为空，无需回算")
        return

    print(f"🔄 准备回算 {len(tickers)} 个持仓品种")
    success, failed = 0, 0
    for ticker in tickers:
        try:
            async with async_session() as session:
                await recompute_holding(session, ticker)
                await session.commit()
            success += 1
            print(f"  ✅ {ticker}")
        except BusinessError as e:
            failed += 1
            print(f"  ❌ {ticker}: {e.message}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {ticker}: {type(e).__name__}: {e}")

    print(f"\n📊 回算完成：成功 {success}，失败 {failed}")


if __name__ == "__main__":
    asyncio.run(main())
