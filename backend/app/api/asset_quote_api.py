"""行情接口 — A股、美股、加密货币、基金"""

from fastapi import APIRouter, Query

from app.core.response import success
from app.services.asset_quote_service import AssetQuoteService

router = APIRouter(prefix="/api/v1", tags=["quote"])
service = AssetQuoteService()


@router.get("/stock/quotes/{market}")
async def get_market_quotes(market: str, codes: str = Query(..., description="逗号分隔的代码，如 600519,000001 或 AAPL,MSFT")):
    """获取 A股/美股 实时行情"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    data = await service.fetch_market_quotes(market, code_list)
    return success(data)


@router.get("/crypto/quotes")
async def get_crypto_quotes(coins: str = Query(..., description="逗号分隔的币种，如 BTC,ETH,SOL")):
    """获取加密货币现货行情"""
    coin_list = [c.strip() for c in coins.split(",") if c.strip()]
    data = await service.fetch_market_quotes("CRYPTO", coin_list)
    return success(data)


@router.get("/fund/quotes")
async def get_fund_quotes(codes: str = Query(..., description="基金代码，逗号分隔，如 166002,110011")):
    """获取基金最新单位净值"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    data = await service.fetch_market_quotes("FUND", code_list)
    return success(data)
