"""快照接口"""

from fastapi import APIRouter, Query

from app.core.response import success
from app.services.snapshot_service import SnapshotService

router = APIRouter(prefix="/api/v1", tags=["snapshot"])
service = SnapshotService()


@router.post("/snapshots", status_code=201)
async def create_snapshot():
    """记录今日快照（手动触发；当日重复触发会覆盖）"""
    data = await service.take_snapshot()
    return success(data, message="快照已记录")


@router.get("/snapshots")
async def list_snapshots(
    currency: str = Query("CNY", description="显示币种，如 CNY/USD/HKD/EUR"),
    limit: int = Query(365, ge=1, le=3650, description="返回条数上限"),
):
    """获取组合级快照列表（按日期升序，便于折线图直接画）

    历史曲线用快照里冻结的汇率换算到 currency。
    """
    data = await service.list_snapshots(currency=currency, limit=limit)
    return success(data)


@router.get("/snapshots/assets")
async def list_asset_snapshots(
    currency: str = Query("CNY", description="显示币种"),
    ticker: str | None = Query(None),
    asset_class: str | None = Query(None),
    market: str | None = Query(None),
    limit: int = Query(365, ge=1, le=3650),
):
    """获取品种级快照（可按三元组过滤）"""
    data = await service.list_asset_snapshots(
        currency=currency, ticker=ticker, asset_class=asset_class,
        market=market, limit=limit,
    )
    return success(data)
