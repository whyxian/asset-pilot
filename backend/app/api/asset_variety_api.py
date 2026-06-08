"""品种目录接口 — CRUD"""

from fastapi import APIRouter

from app.core.exceptions import BusinessError
from app.core.response import success
from app.models.asset_variety import AssetVarietyCreate
from app.services.asset_variety_service import AssetVarietyService

router = APIRouter(prefix="/api/v1", tags=["variety"])
service = AssetVarietyService()


@router.get("/varieties")
async def list_varieties():
    """获取全部品种"""
    data = await service.list_varieties()
    return success(data)


@router.post("/varieties", status_code=201)
async def create_variety(data: AssetVarietyCreate):
    """新增品种"""
    variety = await service.create_variety(data)
    return success(variety, message="品种添加成功")


@router.delete("/varieties/{ticker}", status_code=200)
async def delete_variety(ticker: str):
    """删除品种（软删除）"""
    deleted = await service.delete_variety(ticker)
    if not deleted:
        raise BusinessError(40401, "品种不存在")
    return success(message="品种删除成功")
