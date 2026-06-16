"""归档持仓接口 — 只读"""

from fastapi import APIRouter, Query

from app.core.exceptions import BusinessError
from app.core.response import success
from app.services.closed_holding_service import ClosedHoldingService

router = APIRouter(prefix="/api/v1", tags=["closed_holding"])
service = ClosedHoldingService()


@router.get("/closed-holdings")
async def list_closed_holdings():
    """获取全部归档持仓（按清仓日倒序）"""
    data = await service.list_closed_holdings()
    return success(data)


@router.get("/closed-holdings/{holding_id}")
async def get_closed_holding(holding_id: int):
    """获取单条归档持仓详情（含该周期全部交易）"""
    holding = await service.get_closed_holding(holding_id)
    if not holding:
        raise BusinessError(40401, "归档持仓不存在")
    return success(holding)


@router.delete("/closed-holdings/{holding_id}")
async def delete_closed_holding(holding_id: int):
    """删除归档持仓及其关联交易"""
    deleted = await service.delete_closed_holding(holding_id)
    if not deleted:
        raise BusinessError(40401, "归档持仓不存在")
    return success(message="已删除")


@router.get("/closed-transactions")
async def list_closed_transactions(
    limit: int = Query(500, ge=1, le=2000, description="返回条数上限"),
):
    """获取全部归档交易（按交易日倒序，统一历史交易查询）"""
    data = await service.list_closed_transactions(limit=limit)
    return success(data)
