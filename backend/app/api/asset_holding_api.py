"""持仓接口 — CRUD

URL 设计：URL path 用 ticker，asset_class + market 走 query 参数（必填）。
例：GET /api/v1/holdings/000001?asset_class=FUND&market=CN
"""

from fastapi import APIRouter, Query

from app.core.exceptions import BusinessError
from app.core.error_codes import CODE_VALIDATION, CODE_NOT_FOUND
from app.core.response import success
from app.models.asset_holding import AssetHoldingCreate, AssetHoldingUpdate
from app.services.asset_holding_service import AssetHoldingService

router = APIRouter(prefix="/api/v1", tags=["holding"])
service = AssetHoldingService()


@router.get("/holdings/with-quotes")
async def list_holdings_with_quotes(
    force_refresh: bool = Query(False, description="True 时绕过基金 15 分钟缓存，强制拉取最新行情"),
):
    """获取持仓 + 实时行情 + 市值/盈亏/年化"""
    data = await service.list_holdings_with_quotes(force_refresh=force_refresh)
    return success(data)


@router.get("/holdings")
async def list_holdings():
    """获取全部持仓"""
    data = await service.list_holdings()
    return success(data)


@router.get("/holdings/{ticker}")
async def get_holding(
    ticker: str,
    asset_class: str = Query(..., description="资产类别 STOCK/FUND/CRYPTO"),
    market: str = Query(..., description="市场 CN/US/CRYPTO"),
):
    """按三元组获取持仓"""
    holding = await service.get_holding(ticker, asset_class, market)
    if not holding:
        raise BusinessError(CODE_NOT_FOUND, "持仓不存在")
    return success(holding)


@router.post("/holdings", status_code=201)
async def create_holding(data: AssetHoldingCreate):
    """新增持仓"""
    holding = await service.create_holding(data)
    return success(holding, message="持仓创建成功")


@router.put("/holdings/{ticker}")
async def update_holding(
    ticker: str,
    data: AssetHoldingUpdate,
    asset_class: str = Query(..., description="资产类别 STOCK/FUND/CRYPTO"),
    market: str = Query(..., description="市场 CN/US/CRYPTO"),
):
    """更新持仓（按三元组定位）"""
    holding = await service.update_holding(ticker, asset_class, market, data)
    if not holding:
        raise BusinessError(CODE_NOT_FOUND, "持仓不存在")
    return success(holding, message="持仓更新成功")


@router.delete("/holdings/{ticker}", status_code=200)
async def delete_holding(
    ticker: str,
    asset_class: str = Query(..., description="资产类别 STOCK/FUND/CRYPTO"),
    market: str = Query(..., description="市场 CN/US/CRYPTO"),
):
    """删除持仓 — 级联删除该品种的全部交易记录"""
    txn_count = await service.delete_holding(ticker, asset_class, market)
    if txn_count == -1:
        raise BusinessError(CODE_NOT_FOUND, "持仓不存在")
    msg = f"持仓删除成功，同时删除 {txn_count} 条关联交易记录" if txn_count > 0 else "持仓删除成功"
    return success(message=msg)
