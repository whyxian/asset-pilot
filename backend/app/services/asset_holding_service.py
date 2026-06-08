"""持仓业务逻辑"""

from app.core.exceptions import BusinessError
from app.models.asset_holding import AssetHolding, AssetHoldingCreate, AssetHoldingUpdate
from app.repositories.asset_holding_repository import AssetHoldingRepository
from app.repositories.asset_variety_repository import AssetVarietyRepository


class AssetHoldingService:
    """持仓业务逻辑"""

    def __init__(self):
        self._repo = AssetHoldingRepository()

    async def list_holdings(self) -> list[AssetHolding]:
        """获取全部持仓"""
        return await self._repo.list_holdings()

    async def get_holding(self, ticker: str) -> AssetHolding | None:
        """按代码获取持仓"""
        return await self._repo.get_holding(ticker)

    async def create_holding(self, data: AssetHoldingCreate) -> AssetHolding:
        """新增持仓（先校验品种是否存在）"""
        variety = await AssetVarietyRepository().get_variety(data.ticker)
        if not variety:
            raise BusinessError(40001, f"未识别的品种代码 '{data.ticker}'，请先通过 /api/v1/varieties 添加该品种")
        return await self._repo.create_holding(data)

    async def update_holding(self, ticker: str, data: AssetHoldingUpdate) -> AssetHolding | None:
        """更新持仓"""
        return await self._repo.update_holding(ticker, data)

    async def delete_holding(self, ticker: str) -> bool:
        """删除持仓"""
        return await self._repo.delete_holding(ticker)
