"""行情数据源层 — 纯获取逻辑，不涉及 DB 操作"""

import abc
import asyncio
import json
import re
import traceback
from datetime import datetime
from decimal import Decimal

import httpx
from playwright.async_api import async_playwright

from app.core.logger import logger
from app.models.asset_quote import AssetQuote

# ═══════════════════════════════════════════
# 数据源层（纯获取逻辑，不涉及 DB 操作）
# ═══════════════════════════════════════════


class QuoteDataSource(abc.ABC):
    """行情数据源基类"""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """数据源唯一标识"""
        ...

    @abc.abstractmethod
    async def fetch(self, codes: list[str], market: str) -> list[AssetQuote]:
        """批量获取行情"""
        ...

    def supports(self, asset_class: str, market: str) -> bool:
        """判断是否支持指定资产类别和市场"""
        return False

    async def close(self):
        """释放资源（按需重写）"""
        pass


class TencentDataSource(QuoteDataSource):
    """腾讯财经 — 支持 A 股 + 美股"""

    @property
    def name(self) -> str:
        return "tencent"

    def supports(self, asset_class: str, market: str) -> bool:
        return (asset_class == "STOCK" and market in ("CN", "US")) or \
               (asset_class == "FUND" and market == "US")

    async def fetch(self, codes: list[str], market: str) -> list[AssetQuote]:
        if market == "CN":
            return await self._fetch_a_shares(codes)
        return await self._fetch_us_stocks(codes)

    async def _fetch_a_shares(self, codes: list[str]) -> list[AssetQuote]:
        """A 股行情

        交易所前缀规则：
          sh（沪市）: 6xxxxx / 9xxxxx（股票）  51xxx / 58xxx（ETF）  501xx / 502xx（LOF）
          sz（深市）: 0xxxxx / 3xxxxx（股票）  159xxx / 158xxx（ETF）  16xxxx / 15xxxx（LOF）
          bj（北交所）: 8xxxxx
        """
        prefixed = []
        for c in codes:
            if c.startswith(("5", "6", "9")):
                prefixed.append(f"sh{c}")
            elif c.startswith("8"):
                prefixed.append(f"bj{c}")
            else:
                prefixed.append(f"sz{c}")

        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.text

        now = datetime.now()
        results = []
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 53:
                continue
            code = key[2:]
            results.append(AssetQuote(
                ticker=code, market="CN", name=vals[1],
                price=Decimal(str(vals[3])) if vals[3] else Decimal("0"),
                currency="CNY",
                change_price=Decimal(str(vals[31])) if vals[31] else None,
                change_ratio=float(vals[32]) if vals[32] else None,
                updated_at=now, source="TENCENT",
            ))
        return results

    async def _fetch_us_stocks(self, codes: list[str]) -> list[AssetQuote]:
        """美股行情"""
        prefixed = ",".join(f"us{c}" for c in codes)
        url = f"https://qt.gtimg.cn/q={prefixed}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.text

        now = datetime.now()
        results = []
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line:
                continue
            vals = line.split('"')[1].split("~")
            if len(vals) < 47 or vals[0] != "200":
                continue
            ticker = vals[2].split(".")[0]
            results.append(AssetQuote(
                ticker=ticker, market="US",
                name=vals[46] or vals[1],
                price=Decimal(str(vals[3])) if vals[3] else Decimal("0"),
                currency=vals[35] if vals[35] else "USD",
                change_price=Decimal(str(vals[31])) if vals[31] else None,
                change_ratio=float(vals[32]) if vals[32] else None,
                volume=int(vals[6]) if vals[6] else None,
                updated_at=now, source="TENCENT",
            ))
        return results


class SinaDataSource(QuoteDataSource):
    """新浪财经 Playwright — 仅支持美股"""

    def __init__(self):
        self._playwright = None
        self._browser = None

    @property
    def name(self) -> str:
        return "sina"

    def supports(self, asset_class: str, market: str) -> bool:
        return asset_class == "STOCK" and market == "US"

    async def _get_browser(self):
        if self._browser is None:
            p = await async_playwright().start()
            self._playwright = p
            self._browser = await p.chromium.launch(headless=True)
        return self._browser

    async def close(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def fetch(self, codes: list[str], market: str) -> list[AssetQuote]:
        try:
            browser = await self._get_browser()
        except Exception as e:
            logger.error(f"[SinaDataSource] 浏览器启动失败: {e}")
            traceback.print_exc()
            return []

        async def fetch_one(symbol: str) -> AssetQuote | None:
            url = f"https://stock.finance.sina.com.cn/usstock/quotes/{symbol}.html"
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=20000)
                await page.wait_for_selector("#hqPrice", timeout=10000, state="attached")
                price_el = await page.query_selector("#hqPrice")
                price_text = (await price_el.inner_text()).strip() if price_el else ""
                name_el = await page.query_selector(".s_name")
                name_text = (await name_el.get_attribute("title")) if name_el else ""
                if not name_text:
                    name_text = (await name_el.inner_text()).strip() if name_el else ""
                change_el = await page.query_selector(".hq_change")
                change_text = (await change_el.inner_text()).strip() if change_el else ""
                change_price, change_ratio = None, None
                if "(" in change_text and ")" in change_text and "--" not in change_text:
                    price_part = change_text.split("(")[0].replace(",", "")
                    ratio_part = change_text.split("(")[1].rstrip(")")
                    change_price = Decimal(price_part) if price_part else None
                    change_ratio = float(ratio_part.replace("%", "")) if ratio_part else None
                return AssetQuote(
                    ticker=symbol, market="US", name=name_text,
                    price=Decimal(price_text) if price_text else Decimal("0"),
                    currency="USD", change_price=change_price, change_ratio=change_ratio,
                    updated_at=datetime.now(), source="SINA",
                )
            except Exception as e:
                logger.error(f"[SinaDataSource] 获取 {symbol} 失败: {e}")
                return None
            finally:
                await page.close()

        t0 = datetime.now()
        results = await asyncio.gather(*[fetch_one(s) for s in codes])
        results = [r for r in results if r is not None]
        logger.info(f"  [耗时] Sina {len(codes)} 只: {(datetime.now() - t0).total_seconds():.1f}s")
        return results


class CoinGlassDataSource(QuoteDataSource):
    """CoinGlass API — 支持加密货币"""

    BASE_URL = "https://fapi.coinglass.com/api/coin/v2/info"

    @property
    def name(self) -> str:
        return "coinglass"

    def supports(self, asset_class: str, market: str) -> bool:
        return asset_class == "CRYPTO" and market == "CRYPTO"

    async def fetch(self, codes: list[str], market: str) -> list[AssetQuote]:
        HEADERS = {"User-Agent": "Mozilla/5.0"}

        async def fetch_one(symbol: str) -> AssetQuote | None:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{self.BASE_URL}?symbol={symbol}", headers=HEADERS, timeout=10,
                    )
                    data = resp.json()
                if data.get("code") != "0":
                    return None
                d = data["data"]
                price = Decimal(str(d["price"])) if d.get("price") else Decimal("0")
                change_pct = d.get("priceChangePercent24h")
                change_price = (price * Decimal(str(change_pct)) / 100).quantize(Decimal("0.01")) if change_pct and price else None
                return AssetQuote(
                    ticker=symbol, market="CRYPTO", name=d.get("name", symbol),
                    price=price, currency="USD", change_price=change_price,
                    change_ratio=change_pct,
                    volume=int(d.get("volUsd", 0)) if d.get("volUsd") else None,
                    updated_at=datetime.now(), source="COINGLASS",
                )
            except Exception as e:
                logger.error(f"[CoinGlassDataSource] 获取 {symbol} 失败: {e}")
                return None

        results = await asyncio.gather(*[fetch_one(s) for s in codes])
        return [r for r in results if r is not None]


class EastMoneyFundDataSource(QuoteDataSource):
    """天天基金 pingzhongdata — 支持基金"""

    BASE_URL = "https://fund.eastmoney.com/pingzhongdata/{code}.js"

    @property
    def name(self) -> str:
        return "pingzhong"

    def supports(self, asset_class: str, market: str) -> bool:
        return asset_class == "FUND" and market == "CN"

    async def fetch(self, codes: list[str], market: str) -> list[AssetQuote]:
        async def fetch_one(code: str) -> AssetQuote | None:
            try:
                url = self.BASE_URL.format(code=code)
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                    text = resp.text
                name = ""
                m = re.search(r'var fS_name\s*=\s*["\']([^"\']+)["\']', text)
                if m:
                    name = m.group(1)
                m = re.search(r'var Data_netWorthTrend\s*=\s*(\[[\s\S]*?\]);', text)
                if not m:
                    return None
                nav_data = json.loads(m.group(1))
                if not nav_data:
                    return None
                latest = nav_data[-1]
                nav = Decimal(str(latest.get("y", 0)))
                nav_date = datetime.fromtimestamp(latest["x"] / 1000) if latest.get("x") else datetime.now()
                change_ratio, change_price = None, None
                if len(nav_data) >= 2:
                    prev_nav = Decimal(str(nav_data[-2].get("y", 0)))
                    if prev_nav != 0:
                        change_price = nav - prev_nav
                        change_ratio = float((change_price / prev_nav) * 100)
                return AssetQuote(
                    ticker=code, market="CN", name=name, price=nav, currency="CNY",
                    change_price=change_price, change_ratio=change_ratio,
                    updated_at=nav_date, source="EASTMONEY_FUND",
                )
            except Exception as e:
                logger.error(f"[EastMoneyFundDataSource] 获取基金 {code} 失败: {e}")
                return None

        results = await asyncio.gather(*[fetch_one(c) for c in codes])
        return [r for r in results if r is not None]


class AkshareFundDataSource(QuoteDataSource):
    """akshare — 支持基金（备选）"""

    @property
    def name(self) -> str:
        return "akshare"

    def supports(self, asset_class: str, market: str) -> bool:
        return asset_class == "FUND" and market == "CN"

    async def fetch(self, codes: list[str], market: str) -> list[AssetQuote]:
        import akshare as ak

        async def fetch_one(code: str) -> AssetQuote | None:
            try:
                df = await asyncio.to_thread(ak.fund_open_fund_info_em, symbol=code)
                if df.empty:
                    return None
                latest = df.iloc[-1]
                nav = Decimal(str(latest["单位净值"]))
                nav_date = datetime.strptime(str(latest["净值日期"]), "%Y-%m-%d")
                change_ratio, change_price = None, None
                if len(df) >= 2:
                    prev_nav = Decimal(str(df.iloc[-2]["单位净值"]))
                    if prev_nav != 0:
                        change_price = nav - prev_nav
                        change_ratio = float((change_price / prev_nav) * 100)
                return AssetQuote(
                    ticker=code, market="CN", name="", price=nav, currency="CNY",
                    change_price=change_price, change_ratio=change_ratio,
                    updated_at=nav_date, source="AKSHARE",
                )
            except Exception as e:
                logger.error(f"[AkshareFundDataSource] 获取基金 {code} 失败: {e}")
                return None

        results = await asyncio.gather(*[fetch_one(c) for c in codes])
        return [r for r in results if r is not None]
