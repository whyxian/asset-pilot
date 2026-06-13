"""归档持仓业务逻辑（只读，归档动作由 asset_holding_service.archive_holding 完成）"""

from app.models.closed_holding import ClosedHolding, ClosedHoldingDetail, ClosedTransaction
from app.repositories.closed_holding_repository import ClosedHoldingRepository


class ClosedHoldingService:
    """归档持仓业务逻辑"""

    def __init__(self):
        self._repo = ClosedHoldingRepository()

    async def list_closed_holdings(self) -> list[ClosedHolding]:
        """获取全部归档持仓"""
        return await self._repo.list_closed_holdings()

    async def get_closed_holding(self, holding_id: int) -> ClosedHoldingDetail | None:
        """获取单条归档持仓详情"""
        return await self._repo.get_closed_holding(holding_id)

    async def list_closed_transactions(self, limit: int = 500) -> list[ClosedTransaction]:
        """获取全部归档交易（统一历史查询）"""
        return await self._repo.list_closed_transactions(limit=limit)
