"""交易记录业务逻辑"""

from app.core.exceptions import BusinessError
from app.models.transaction import Transaction, TransactionCreate, TransactionUpdate
from app.repositories.asset_variety_repository import AssetVarietyRepository
from app.repositories.transaction_repository import TransactionRepository


class TransactionService:
    """交易记录业务逻辑"""

    def __init__(self):
        self._repo = TransactionRepository()
        self._variety_repo = AssetVarietyRepository()

    async def list_transactions(
        self, ticker: str | None = None, limit: int = 100
    ) -> list[Transaction]:
        """获取交易记录列表"""
        return await self._repo.list_transactions(ticker=ticker, limit=limit)

    async def get_transaction(self, transaction_id: int) -> Transaction | None:
        """获取单条交易记录"""
        return await self._repo.get_transaction(transaction_id)

    async def create_transaction(self, data: TransactionCreate) -> Transaction:
        """新增交易记录（带基本校验）"""
        # 校验品种是否存在
        variety = await self._variety_repo.get_variety(data.ticker)
        if not variety:
            raise BusinessError(40001, f"未识别的品种代码 '{data.ticker}'，请先通过 /api/v1/varieties 添加该品种")

        # 至少填 quantity+unit_price 或 amount 之一
        has_qty_price = data.quantity is not None and data.unit_price is not None
        has_amount = data.amount is not None
        if not has_qty_price and not has_amount:
            raise BusinessError(
                40001,
                "请填写 (数量 + 成交价) 或 (交易金额)，至少填一组",
            )

        return await self._repo.create_transaction(data)

    async def update_transaction(
        self, transaction_id: int, data: TransactionUpdate
    ) -> Transaction | None:
        """更新交易记录"""
        return await self._repo.update_transaction(transaction_id, data)

    async def delete_transaction(self, transaction_id: int) -> bool:
        """删除交易记录"""
        return await self._repo.delete_transaction(transaction_id)
