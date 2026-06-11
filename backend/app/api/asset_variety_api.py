"""品种目录接口 — CRUD"""

from fastapi import APIRouter, Query

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


@router.get("/varieties/search")
async def search_varieties(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回条数上限"),
):
    """搜索品种（按 ticker 或名称模糊匹配）"""
    data = await service.search_varieties(q, limit)
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
