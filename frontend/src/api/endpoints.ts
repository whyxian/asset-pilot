import apiClient from './client'
import type { AssetQuote, AssetSnapshot, AssetVariety, CashBalancesResponse, CashFlow, ClosedHolding, ClosedHoldingDetail, ClosedTransaction, HoldingCreate, HoldingsWithQuotesResponse, HoldingUpdate, HoldingWithQuote, NetWorthSnapshot, OverviewStats, PaginatedResponse, Transaction, TransactionCreate, TransactionUpdate, WatchlistCreate, WatchlistItem, WatchlistWithQuote } from '@/types'

// ═══════════════════════════════════════════
// 持仓
// ═══════════════════════════════════════════

/** 获取持仓 + 实时行情 + 市值/盈亏/年化
 *  forceRefresh=true 时绕过基金 15 分钟缓存，强制拉取最新行情
 */
export const fetchHoldingsWithQuotes = (forceRefresh: boolean = false) =>
  apiClient.get('/api/v1/holdings/with-quotes', { params: { force_refresh: forceRefresh } }) as Promise<HoldingsWithQuotesResponse>

/** 新增持仓 */
export const createHolding = (data: HoldingCreate) =>
  apiClient.post('/api/v1/holdings', data) as Promise<HoldingWithQuote>

/** 更新持仓（按三元组定位） */
export const updateHolding = (ticker: string, asset_class: string, market: string, data: HoldingUpdate) =>
  apiClient.put(`/api/v1/holdings/${ticker}`, data, { params: { asset_class, market } }) as Promise<HoldingWithQuote>

/** 删除持仓（按三元组定位，级联删交易） */
export const deleteHolding = (ticker: string, asset_class: string, market: string) =>
  apiClient.delete(`/api/v1/holdings/${ticker}`, { params: { asset_class, market } }) as Promise<void>

// ═══════════════════════════════════════════
// 概览
// ═══════════════════════════════════════════

/** 获取概览统计
 *  forceRefresh=true 时绕过基金 15 分钟缓存，强制拉取最新行情
 */
export const fetchOverview = (currency: string = 'CNY', forceRefresh: boolean = false) =>
  apiClient.get('/api/v1/overview', { params: { currency, force_refresh: forceRefresh } }) as Promise<OverviewStats>

// ═══════════════════════════════════════════
// 品种目录
// ═══════════════════════════════════════════

/** 搜索品种（按 ticker 或名称模糊匹配） */
export const searchVarieties = (q: string, limit = 10) =>
  apiClient.get('/api/v1/varieties/search', {
    params: { q, limit },
  }) as Promise<AssetVariety[]>

/** 新增品种（添加到品种库） */
export const createVariety = (data: { ticker: string; name: string; market: string; asset_class: string }) =>
  apiClient.post('/api/v1/varieties', data) as Promise<AssetVariety>

// ═══════════════════════════════════════════
// 股票行情
// ═══════════════════════════════════════════

/** 获取 A 股 / 美股实时行情 */
export const fetchStockQuotes = (market: 'CN' | 'US', codes: string[]) =>
  apiClient.get(`/api/v1/stock/quotes/${market}`, {
    params: { codes: codes.join(',') },
  }) as Promise<AssetQuote[]>

// ═══════════════════════════════════════════
// 加密货币行情
// ═══════════════════════════════════════════

/** 获取加密货币实时行情 */
export const fetchCryptoQuotes = (coins: string[]) =>
  apiClient.get('/api/v1/crypto/quotes', {
    params: { coins: coins.join(',') },
  }) as Promise<AssetQuote[]>

// ═══════════════════════════════════════════
// 基金行情
// ═══════════════════════════════════════════

/** 获取基金净值（CN 市场走天天基金，US 市场走腾讯） */
export const fetchFundQuotes = (market: 'CN' | 'US', codes: string[]) =>
  apiClient.get(`/api/v1/fund/quotes/${market}`, {
    params: { codes: codes.join(',') },
  }) as Promise<AssetQuote[]>

// ═══════════════════════════════════════════
// 交易记录
// ═══════════════════════════════════════════

/** 获取交易记录列表（三元组都可选筛选，分页） */
export const fetchTransactions = (
  page: number = 1,
  pageSize: number = 20,
  ticker?: string,
  asset_class?: string,
  market?: string,
) =>
  apiClient.get('/api/v1/transactions', {
    params: { page, page_size: pageSize, ticker, asset_class, market },
  }) as Promise<PaginatedResponse<Transaction>>

/** 新增交易记录 */
export const createTransaction = (data: TransactionCreate) =>
  apiClient.post('/api/v1/transactions', data) as Promise<Transaction>

/** 更新交易记录 */
export const updateTransaction = (id: number, data: TransactionUpdate) =>
  apiClient.put(`/api/v1/transactions/${id}`, data) as Promise<Transaction>

/** 删除交易记录 */
export const deleteTransaction = (id: number) =>
  apiClient.delete(`/api/v1/transactions/${id}`) as Promise<void>

// ═══════════════════════════════════════════
// 历史持仓（已归档）
// ═══════════════════════════════════════════

/** 获取全部归档持仓（按清仓日倒序，分页） */
export const fetchClosedHoldings = (page: number = 1, pageSize: number = 20) =>
  apiClient.get('/api/v1/closed-holdings', { params: { page, page_size: pageSize } }) as Promise<PaginatedResponse<ClosedHolding>>

/** 获取单条归档持仓详情（含全部关联交易） */
export const fetchClosedHolding = (id: number) =>
  apiClient.get(`/api/v1/closed-holdings/${id}`) as Promise<ClosedHoldingDetail>

/** 获取全部归档交易（按交易日倒序，分页） */
export const fetchClosedTransactions = (page: number = 1, pageSize: number = 20) =>
  apiClient.get('/api/v1/closed-transactions', { params: { page, page_size: pageSize } }) as Promise<PaginatedResponse<ClosedTransaction>>

/** 删除归档持仓及其关联交易 */
export const deleteClosedHolding = (id: number) =>
  apiClient.delete(`/api/v1/closed-holdings/${id}`) as Promise<void>

// ═══════════════════════════════════════════
// 净值快照
// ═══════════════════════════════════════════

/** 记录今日快照（手动触发） */
export const createSnapshot = () =>
  apiClient.post('/api/v1/snapshots') as Promise<NetWorthSnapshot>

/** 获取组合级快照列表（按日期升序） */
export const fetchSnapshots = (currency: string = 'CNY', limit = 365) =>
  apiClient.get('/api/v1/snapshots', { params: { currency, limit } }) as Promise<NetWorthSnapshot[]>

/** 获取品种级快照（可按三元组过滤） */
// ═══════════════════════════════════════════
// 资金流水
// ═══════════════════════════════════════════

export interface CashDepositData {
  amount: number
  currency: string
  notes?: string | null
}

export interface CashWithdrawData {
  amount: number
  currency: string
  notes?: string | null
}

/** 获取各币种现金余额 + 换算到指定币种的总额 */
export const fetchCashBalances = (currency: string = 'CNY') =>
  apiClient.get('/api/v1/cash/balances', { params: { currency } }) as Promise<CashBalancesResponse>

/** 获取资金流水列表（分页） */
export const fetchCashFlows = (page: number = 1, pageSize: number = 20) =>
  apiClient.get('/api/v1/cash/flows', { params: { page, page_size: pageSize } }) as Promise<PaginatedResponse<CashFlow>>

/** 入金 */
export const cashDeposit = (data: CashDepositData) =>
  apiClient.post('/api/v1/cash/deposit', data) as Promise<CashFlow>

/** 出金 */
export const cashWithdraw = (data: CashWithdrawData) =>
  apiClient.post('/api/v1/cash/withdraw', data) as Promise<CashFlow>

export const fetchAssetSnapshots = (
  currency: string = 'CNY',
  ticker?: string,
  asset_class?: string,
  market?: string,
  limit = 365,
) =>
  apiClient.get('/api/v1/snapshots/assets', {
    params: { currency, ticker, asset_class, market, limit },
  }) as Promise<AssetSnapshot[]>

// ═══════════════════════════════════════════
// 自选股
// ═══════════════════════════════════════════

/** 自选列表（收藏时间倒序） */
export const fetchWatchlist = () =>
  apiClient.get('/api/v1/watchlist') as Promise<WatchlistItem[]>

/** 自选 + 实时行情（QuoteStatus 三态，前端 30s 轮询此端点） */
export const fetchWatchlistWithQuotes = () =>
  apiClient.get('/api/v1/watchlist/with-quotes') as Promise<WatchlistWithQuote[]>

/** 收藏（品种不存在时后端自动注册） */
export const createWatchlist = (data: WatchlistCreate) =>
  apiClient.post('/api/v1/watchlist', data) as Promise<WatchlistItem>

/** 取消收藏 */
export const deleteWatchlist = (watchlistId: number) =>
  apiClient.delete(`/api/v1/watchlist/${watchlistId}`) as Promise<void>
