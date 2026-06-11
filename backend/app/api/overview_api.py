"""概览接口"""

from fastapi import APIRouter

from app.core.response import success
from app.services.overview_service import OverviewService

router = APIRouter(prefix="/api/v1", tags=["overview"])
service = OverviewService()


@router.get("/overview")
async def get_overview():
    """获取概览统计（总市值/成本/盈亏/年化/配比，统一为 CNY）"""
    data = await service.get_overview()
    return success(data)
