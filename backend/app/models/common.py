"""通用 Pydantic 模型 - 跨模块共享"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应 - 所有列表接口统一返回结构

    Args:
        data: 当前页数据列表
        total: 总记录数（用于前端算总页数）
        page: 当前页码（从 1 开始）
        page_size: 每页条数
    """
    data: list[T]
    total: int
    page: int
    page_size: int
