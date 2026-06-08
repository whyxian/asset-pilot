"""统一接口返回格式"""

from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一 API 响应"""
    code: int = 0
    message: str = "ok"
    data: Any = None


def success(data: Any = None, message: str = "ok") -> ApiResponse:
    """成功响应"""
    return ApiResponse(code=0, message=message, data=data)


def error(code: int, message: str) -> ApiResponse:
    """错误响应"""
    return ApiResponse(code=code, message=message, data=None)
