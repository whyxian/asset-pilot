"""快照数据访问层 — networth_snapshots + asset_snapshots

INSERT OR REPLACE 策略：当日重复触发快照会覆盖旧值（同一天最后一次为准）
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.orm.asset_snapshot_orm import AssetSnapshotRecord
from app.models.orm.networth_snapshot_orm import NetWorthSnapshotRecord


class SnapshotRepository:
    """快照数据访问"""

    async def upsert_networth_snapshot(
        self, session: AsyncSession, data: dict
    ) -> NetWorthSnapshotRecord:
        """插入/覆盖组合级快照（按 snapshot_date UNIQUE）

        Args:
            session: 外部事务会话（snapshot_service 单事务统一管理）
            data: dict，对应 NetWorthSnapshotRecord 的列
        """
        stmt = sqlite_insert(NetWorthSnapshotRecord).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["snapshot_date"],
            set_={
                "total_value_usd": stmt.excluded.total_value_usd,
                "total_cost_usd": stmt.excluded.total_cost_usd,
                "total_pnl_usd": stmt.excluded.total_pnl_usd,
                "total_pnl_pct": stmt.excluded.total_pnl_pct,
                "annualized_return": stmt.excluded.annualized_return,
                "allocation": stmt.excluded.allocation,
                "fx_rates": stmt.excluded.fx_rates,
                "updated_at": stmt.excluded.created_at,
            },
        )
        await session.execute(stmt)
        # 取出刚 upsert 的行返回
        r = (await session.execute(
            select(NetWorthSnapshotRecord).where(
                NetWorthSnapshotRecord.snapshot_date == data["snapshot_date"]
            )
        )).scalar_one()
        return r

    async def upsert_asset_snapshots(
        self, session: AsyncSession, rows: list[dict]
    ):
        """批量插入/覆盖品种级快照（按四元组 UNIQUE）"""
        if not rows:
            return
        stmt = sqlite_insert(AssetSnapshotRecord).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_class", "market", "ticker", "snapshot_date"],
            set_={
                "name": stmt.excluded.name,
                "currency": stmt.excluded.currency,
                "quantity": stmt.excluded.quantity,
                "unit_value": stmt.excluded.unit_value,
                "cost_value": stmt.excluded.cost_value,
                "market_value": stmt.excluded.market_value,
                "market_value_usd": stmt.excluded.market_value_usd,
                "total_invested": stmt.excluded.total_invested,
                "total_invested_usd": stmt.excluded.total_invested_usd,
                "unrealized_pnl": stmt.excluded.unrealized_pnl,
                "return_pct": stmt.excluded.return_pct,
                "updated_at": stmt.excluded.created_at,
            },
        )
        await session.execute(stmt)

    async def list_networth_snapshots(
        self, limit: int = 365
    ) -> list[NetWorthSnapshotRecord]:
        """读组合级快照（按日期升序，便于折线图直接画）"""
        async with async_session() as session:
            records = (await session.execute(
                select(NetWorthSnapshotRecord)
                .order_by(NetWorthSnapshotRecord.snapshot_date.asc())
                .limit(limit)
            )).scalars().all()
            return list(records)

    async def list_asset_snapshots(
        self,
        ticker: str | None = None,
        asset_class: str | None = None,
        market: str | None = None,
        limit: int = 365,
    ) -> list[AssetSnapshotRecord]:
        """读品种级快照（可按三元组过滤；默认按日期升序）"""
        async with async_session() as session:
            stmt = select(AssetSnapshotRecord)
            if ticker:
                stmt = stmt.where(AssetSnapshotRecord.ticker == ticker)
            if asset_class:
                stmt = stmt.where(AssetSnapshotRecord.asset_class == asset_class)
            if market:
                stmt = stmt.where(AssetSnapshotRecord.market == market)
            stmt = stmt.order_by(AssetSnapshotRecord.snapshot_date.asc()).limit(limit)
            records = (await session.execute(stmt)).scalars().all()
            return list(records)

    async def get_networth_by_date(
        self, snapshot_date: date
    ) -> NetWorthSnapshotRecord | None:
        """按日期取单条组合快照（用于幂等判断）"""
        async with async_session() as session:
            return (await session.execute(
                select(NetWorthSnapshotRecord)
                .where(NetWorthSnapshotRecord.snapshot_date == snapshot_date)
            )).scalar_one_or_none()
