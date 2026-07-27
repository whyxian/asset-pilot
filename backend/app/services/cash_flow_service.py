"""资金流水业务逻辑"""

from decimal import Decimal

from app.models.cash_flow import CashBalance, CashFlow, CashDepositCreate, CashWithdrawCreate
from app.repositories.cash_flow_repository import CashFlowRepository


class CashFlowService:
    """资金流水业务逻辑"""

    def __init__(self):
        self._repo = CashFlowRepository()

    async def deposit(self, data: CashDepositCreate) -> CashFlow:
        """入金"""
        return await self._repo.create_flow(
            type_="deposit", amount=data.amount,
            currency=data.currency, notes=data.notes,
        )

    async def withdraw(self, data: CashWithdrawCreate) -> CashFlow:
        """出金（金额存为负）"""
        return await self._repo.create_flow(
            type_="withdraw", amount=-data.amount,
            currency=data.currency, notes=data.notes,
        )

    async def list_flows(self, limit: int = 100) -> list[CashFlow]:
        """流水列表"""
        return await self._repo.list_flows(limit=limit)

    async def get_balances(self) -> list[CashBalance]:
        """余额"""
        return await self._repo.get_balances()

    async def delete_flow(self, flow_id: int) -> bool:
        """删除流水"""
        return await self._repo.delete_flow(flow_id)
