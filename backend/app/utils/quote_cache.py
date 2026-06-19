"""行情内存缓存 — 按 (market, ticker) 单条缓存，带 TTL，支持部分命中

设计要点：
- 单 ticker 粒度：同一 (market, ticker) 跨用户、跨页面共享缓存。
  A 用户和 B 用户都查 600519 共享；概览页和持仓页 codes 不同也能复用命中的 ticker。
- 部分命中：codes 里命中若干只、缺若干只时，只拉缺失的（与原基金 DB 缓存 missing 逻辑一致）。
- TTL 按市场交易时段定（交易 30s / 非交易 30min / 基金 15min），见 trading_hours.quote_cache_ttl。
- 进程内内存缓存，重启失效（短 TTL 下合理）。
"""

import time

from app.utils.trading_hours import quote_cache_ttl


class QuoteCache:
    """行情内存缓存 — 单 ticker + 部分命中"""

    def __init__(self):
        # {(market, ticker): (quote, expire_at)}
        self._store: dict[tuple[str, str], tuple[object, float]] = {}

    def get(self, market: str, codes: list[str]) -> tuple[dict, list[str]]:
        """查询缓存，返回 (命中 {ticker: quote}, 缺失 [ticker])

        命中的 ticker 直接从缓存取；缺失/过期的 ticker 进 missing 列表，
        调用方只拉 missing。过期项顺便清除。

        Args:
            market: "CN" / "US" / "CRYPTO" / "FUND"
            codes: 待查询的 ticker 列表

        Returns:
            (hit, missing)：hit 为 {ticker: AssetQuote}，missing 为未命中的 ticker 列表
        """
        now = time.time()
        hit: dict[str, object] = {}
        missing: list[str] = []
        for code in codes:
            key = (market, code)
            entry = self._store.get(key)
            if entry is None or now > entry[1]:
                if entry is not None:
                    self._store.pop(key, None)  # 顺手清过期
                missing.append(code)
            else:
                hit[code] = entry[0]
        return hit, missing

    def set(self, market: str, quotes: list) -> None:
        """批量写入缓存，TTL 按 market 交易时段定

        Args:
            market: "CN" / "US" / "CRYPTO" / "FUND"
            quotes: AssetQuote 列表（取 q.ticker 作 key）
        """
        expire_at = time.time() + quote_cache_ttl(market)
        for q in quotes:
            self._store[(market, q.ticker)] = (q, expire_at)

    def clear(self) -> None:
        """清空全部缓存"""
        self._store.clear()
