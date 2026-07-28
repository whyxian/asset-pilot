"""资金流水业务逻辑"""

from decimal import Decimal

from app.models.cash_flow import (
    CashBalance, CashBalancesResponse, CashFlow, CashDepositCreate, CashWithdrawCreate,
)
from app.models.common import PaginatedResponse
from app.repositories.cash_flow_repository import CashFlowRepository
from app.utils.exchange_rate import convert_with_rates, fetch_rates


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

    async def list_flows(self, page: int = 1, page_size: int = 20) -> PaginatedResponse[CashFlow]:
        """流水列表（分页）"""
        return await self._repo.list_flows(page=page, page_size=page_size)

    async def get_balances(self, display_currency: str = "CNY") -> CashBalancesResponse:
        """余额：各币种原始余额 + 换算到 display_currency 的总额"""
        balances = await self._repo.get_balances()
        rate_snapshot = await fetch_rates()
        total = Decimal("0")
        for b in balances:
            total += convert_with_rates(b.balance, b.currency, display_currency, rate_snapshot.rates)
        return CashBalancesResponse(
            display_currency=display_currency,
            total=total,
            balances=balances,
            rate_source_date=rate_snapshot.source_date,
            rate_stale=rate_snapshot.is_stale,
        )

    async def delete_flow(self, flow_id: int) -> bool:
        """删除流水"""
        return await self._repo.delete_flow(flow_id)
