"""资金流水接口 — 独立于交易系统"""

from fastapi import APIRouter, Query

from app.core.exceptions import BusinessError
from app.core.response import success
from app.models.cash_flow import CashDepositCreate, CashWithdrawCreate
from app.services.cash_flow_service import CashFlowService

router = APIRouter(prefix="/api/v1/cash", tags=["cash"])
service = CashFlowService()


@router.get("/balances")
async def get_balances():
    """各币种现金余额"""
    data = await service.get_balances()
    return success(data)


@router.get("/flows")
async def list_flows(limit: int = Query(100, ge=1, le=1000)):
    """资金流水列表（按时间倒序）"""
    data = await service.list_flows(limit=limit)
    return success(data)


@router.post("/deposit")
async def deposit(data: CashDepositCreate):
    """入金"""
    flow = await service.deposit(data)
    return success(flow)


@router.post("/withdraw")
async def withdraw(data: CashWithdrawCreate):
    """出金"""
    # 检查余额是否充足
    balances = await service.get_balances()
    current = Decimal("0")
    for b in balances:
        if b.currency == data.currency:
            current = b.balance
            break
    if current < data.amount:
        raise BusinessError(40001, f"{data.currency} 现金余额不足：当前 {current}，需要 {data.amount}")
    flow = await service.withdraw(data)
    return success(flow)


@router.delete("/flows/{flow_id}")
async def delete_flow(flow_id: int):
    """删除单笔资金流水"""
    ok = await service.delete_flow(flow_id)
    if not ok:
        raise BusinessError(40401, "资金流水记录不存在")
    return success(message="已删除")
