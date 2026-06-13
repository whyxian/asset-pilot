"""持仓接口 — CRUD"""

from fastapi import APIRouter

from app.core.exceptions import BusinessError
from app.core.response import success
from app.models.asset_holding import AssetHolding, AssetHoldingCreate, AssetHoldingUpdate
from app.services.asset_holding_service import AssetHoldingService

router = APIRouter(prefix="/api/v1", tags=["holding"])
service = AssetHoldingService()


@router.get("/holdings/with-quotes")
async def list_holdings_with_quotes():
    """获取持仓 + 实时行情 + 市值/盈亏/年化"""
    data = await service.list_holdings_with_quotes()
    return success(data)


@router.get("/holdings")
async def list_holdings():
    """获取全部持仓"""
    data = await service.list_holdings()
    return success(data)


@router.get("/holdings/{ticker}")
async def get_holding(ticker: str):
    """按代码获取持仓"""
    holding = await service.get_holding(ticker)
    if not holding:
        raise BusinessError(40401, "持仓不存在")
    return success(holding)


@router.post("/holdings", status_code=201)
async def create_holding(data: AssetHoldingCreate):
    """新增持仓"""
    holding = await service.create_holding(data)
    return success(holding, message="持仓创建成功")


@router.put("/holdings/{ticker}")
async def update_holding(ticker: str, data: AssetHoldingUpdate):
    """更新持仓"""
    holding = await service.update_holding(ticker, data)
    if not holding:
        raise BusinessError(40401, "持仓不存在")
    return success(holding, message="持仓更新成功")


@router.delete("/holdings/{ticker}", status_code=200)
async def delete_holding(ticker: str):
    """删除持仓 — 级联删除该 ticker 的全部交易记录"""
    txn_count = await service.delete_holding(ticker)
    if txn_count == -1:
        raise BusinessError(40401, "持仓不存在")
    msg = f"持仓删除成功，同时删除 {txn_count} 条关联交易记录" if txn_count > 0 else "持仓删除成功"
    return success(message=msg)
