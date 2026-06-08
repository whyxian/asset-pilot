"""品种目录业务逻辑"""

from app.models.asset_variety import AssetVariety, AssetVarietyCreate
from app.repositories.asset_variety_repository import AssetVarietyRepository


class AssetVarietyService:
    """品种目录业务逻辑"""

    def __init__(self):
        self._repo = AssetVarietyRepository()

    async def list_varieties(self) -> list[AssetVariety]:
        return await self._repo.list_varieties()

    async def create_variety(self, data: AssetVarietyCreate) -> AssetVariety:
        return await self._repo.create_variety(data)

    async def delete_variety(self, ticker: str) -> bool:
        return await self._repo.soft_delete_variety(ticker)
