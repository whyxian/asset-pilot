"""行情内存缓存 — 按 (market, ticker) 单条缓存，带 TTL，支持部分命中

设计要点：
- 单 ticker 粒度：同一 (market, ticker) 跨用户、跨页面共享缓存。
  A 用户和 B 用户都查 600519 共享；概览页和持仓页 codes 不同也能复用命中的 ticker。
- 部分命中：codes 里命中若干只、缺若干只时，只拉缺失的（与原基金 DB 缓存 missing 逻辑一致）。
- TTL 兜底：后台定时任务负责主动刷新缓存，TTL 仅在调度器故障时兜底（5min）。
- 进程内内存缓存，重启失效。
"""

import time

from app.utils.trading_hours import quote_cache_ttl


class QuoteCache:
    """行情内存缓存 — 单 ticker + 部分命中

    进程级单例：所有 AssetQuoteService 实例共享同一个 quote_cache 实例。
    定时任务写入的缓存，用户请求立即可见。
    """

    def __init__(self):
        # {(market, ticker): (quote, expire_at)}
        self._store: dict[tuple[str, str], tuple[object, float]] = {}

    def get(self, market: str, codes: list[str]) -> tuple[dict, list[str], set[str]]:
        """查询缓存，返回 (命中 {ticker: quote}, 缺失 [ticker], 过期 {ticker})

        核心设计：用户请求永远不触网。过期数据仍返回（放进 hit），调用方标记为
        HISTORICAL 而非触发网络拉取。只有从未被缓存的 ticker 才进 missing。

        Args:
            market: "CN" / "US" / "CRYPTO" / "FUND"
            codes: 待查询的 ticker 列表

        Returns:
            (hit, missing, stale)：hit 含过期数据，missing 只有从未缓存过的 ticker，
            stale 是 hit 中已过期的 ticker 集合。
        """
        now = time.time()
        hit: dict[str, object] = {}
        missing: list[str] = []
        stale: set[str] = set()
        for code in codes:
            key = (market, code)
            entry = self._store.get(key)
            if entry is None:
                missing.append(code)
            elif now > entry[1]:
                hit[code] = entry[0]  # 过期仍返回，不丢
                stale.add(code)
            else:
                hit[code] = entry[0]
        return hit, missing, stale

    def set(self, market: str, quotes: list) -> None:
        """批量写入缓存，TTL 按 market 兜底（定时任务 30s 刷新，此 TTL 仅调度器故障时触发）

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


# 进程级单例 — 定时任务和所有请求处理共享同一缓存
quote_cache = QuoteCache()
