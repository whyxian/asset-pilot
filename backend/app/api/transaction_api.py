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
    ticker: str | None = Query(None, description="按品种筛选"),
    limit: int = Query(100, ge=1, le=500, description="返回条数上限"),
):
    """获取交易记录列表（按日期倒序）"""
    data = await service.list_transactions(ticker=ticker, limit=limit)
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
