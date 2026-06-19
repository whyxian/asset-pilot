"""AssetPilot 后端入口"""

import asyncio
import time
from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.asset_holding_api import router as asset_holding_router
from app.api.asset_quote_api import router as asset_quote_router
from app.api.asset_variety_api import router as asset_variety_router
from app.api.closed_holding_api import router as closed_holding_router
from app.api.overview_api import router as overview_router
from app.api.snapshot_api import router as snapshot_router
from app.api.transaction_api import router as transaction_router
from app.core.database import engine, init_db
from app.core.exceptions import BusinessError
from app.core.logger import logger
from app.scheduler.quote_scheduler import QuoteScheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库 + 行情定时任务，关闭时释放资源"""
    await init_db()
    scheduler = AsyncIOScheduler()
    quote_refresher = QuoteScheduler()
    scheduler.add_job(
        quote_refresher.refresh_quotes,
        trigger="interval",
        seconds=30,
        id="refresh_quotes",
        misfire_grace_time=10,
    )
    scheduler.add_job(
        quote_refresher.refresh_rates,
        trigger="interval",
        seconds=3300,  # 55min，略低于 1h 缓存 TTL，保证用户请求永远命中
        id="refresh_rates",
        misfire_grace_time=60,
    )
    # 启动时预热缓存（避免前 30s 用户请求直打网络）
    try:
        await asyncio.gather(
            quote_refresher.refresh_quotes(),
            quote_refresher.refresh_rates(),
        )
        logger.info("[lifespan] 缓存预热完成")
    except Exception as e:
        logger.warning(f"[lifespan] 缓存预热失败（不影响启动）: {e}")
    scheduler.start()
    logger.info("[lifespan] 定时任务已启动（行情30s + 汇率55min）")
    yield
    scheduler.shutdown(wait=False)
    logger.info("[lifespan] 行情定时任务已停止")
    await engine.dispose()


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
app.include_router(overview_router)
app.include_router(transaction_router)
app.include_router(closed_holding_router)
app.include_router(snapshot_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
