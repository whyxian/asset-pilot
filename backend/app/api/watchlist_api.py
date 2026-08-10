"""自选股接口 — 收藏 / 取消 / 列表 / 带行情"""

from fastapi import APIRouter

from app.core.error_codes import CODE_NOT_FOUND
from app.core.exceptions import BusinessError
from app.core.response import success
from app.models.asset_watchlist import WatchlistCreate
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])
service = WatchlistService()


@router.get("")
async def list_watchlist():
    """自选列表（收藏时间倒序）"""
    data = await service.list_watchlist()
    return success(data)


@router.get("/with-quotes")
async def list_watchlist_with_quotes():
    """自选 + 实时行情（QuoteStatus 三态）"""
    data = await service.list_with_quotes()
    return success(data)


@router.post("", status_code=201)
async def create_watchlist(data: WatchlistCreate):
    """收藏（品种不存在时自动注册）"""
    item = await service.create_watchlist(data)
    return success(item)


@router.delete("/{watchlist_id}", status_code=200)
async def delete_watchlist(watchlist_id: int):
    """取消收藏（不影响品种库）"""
    ok = await service.delete_watchlist(watchlist_id)
    if not ok:
        raise BusinessError(CODE_NOT_FOUND, "自选记录不存在")
    return success(message="已取消收藏")
