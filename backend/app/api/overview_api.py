"""概览接口"""

from fastapi import APIRouter, Query

from app.core.response import success
from app.services.overview_service import OverviewService

router = APIRouter(prefix="/api/v1", tags=["overview"])
service = OverviewService()


@router.get("/overview")
async def get_overview(
    currency: str = Query("CNY", description="显示币种，如 CNY/USD/HKD/EUR"),
):
    """获取概览统计（总市值/成本/盈亏/年化/配比）

    内部以 USD 聚合，按 currency 换算返回。
    """
    data = await service.get_overview(currency)
    return success(data)
