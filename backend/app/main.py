"""AssetPilot 后端入口"""

import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.asset_holding_api import router as asset_holding_router
from app.api.asset_quote_api import router as asset_quote_router
from app.api.asset_variety_api import router as asset_variety_router
from app.core.database import init_db
from app.core.exceptions import BusinessError
from app.core.logger import logger
from app.core.response import error


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库"""
    await init_db()
    yield


app = FastAPI(title="AssetPilot", version="0.1.0", lifespan=lifespan)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 全局异常处理器 ----
@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    return JSONResponse(
        status_code=200,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=200,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


# ---- 请求日志 ----
@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    elapsed = (time.time() - t0) * 1000
    logger.info(f"[{request.method}] {request.url.path} {response.status_code} {elapsed:.0f}ms")
    return response


# ---- 注册路由 ----
app.include_router(asset_quote_router)
app.include_router(asset_holding_router)
app.include_router(asset_variety_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
