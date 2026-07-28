"""交易记录接口 — CRUD"""

from fastapi import APIRouter, Query

from app.core.exceptions import BusinessError
from app.core.response import success
from app.models.transaction import TransactionCreate, TransactionUpdate
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/api/v1", tags=["transaction"])
service = TransactionService()


@router.get("/transactions")
async def list_transactions(
    ticker: str | None = Query(None, description="按品种 ticker 筛选"),
    asset_class: str | None = Query(None, description="按资产类别筛选 STOCK/FUND/CRYPTO"),
    market: str | None = Query(None, description="按市场筛选 CN/US/CRYPTO"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取交易记录列表（按日期倒序，分页）；三个筛选都可选，按品种精确筛选时三个一起传"""
    data = await service.list_transactions(
        ticker=ticker, asset_class=asset_class, market=market,
        page=page, page_size=page_size,
    )
    return success(data)


@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: int):
    """获取单条交易记录"""
    txn = await service.get_transaction(transaction_id)
    if not txn:
        raise BusinessError(40401, "交易记录不存在")
    return success(txn)


@router.post("/transactions", status_code=201)
async def create_transaction(data: TransactionCreate):
    """新增交易记录"""
    txn = await service.create_transaction(data)
    return success(txn, message="交易记录创建成功")


@router.put("/transactions/{transaction_id}")
async def update_transaction(transaction_id: int, data: TransactionUpdate):
    """更新交易记录"""
    txn = await service.update_transaction(transaction_id, data)
    if not txn:
        raise BusinessError(40401, "交易记录不存在")
    return success(txn, message="交易记录更新成功")


@router.delete("/transactions/{transaction_id}", status_code=200)
async def delete_transaction(transaction_id: int):
    """删除交易记录"""
    deleted = await service.delete_transaction(transaction_id)
    if not deleted:
        raise BusinessError(40401, "交易记录不存在")
    return success(message="交易记录删除成功")
