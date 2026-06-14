import apiClient from './client'
import type { AssetQuote, AssetVariety, ClosedHolding, ClosedHoldingDetail, ClosedTransaction, HoldingCreate, HoldingUpdate, HoldingWithQuote, OverviewStats, Transaction, TransactionCreate, TransactionUpdate } from '@/types'

// ═══════════════════════════════════════════
// 持仓
// ═══════════════════════════════════════════

/** 获取持仓 + 实时行情 + 市值/盈亏/年化 */
export const fetchHoldingsWithQuotes = () =>
  apiClient.get('/api/v1/holdings/with-quotes') as Promise<HoldingWithQuote[]>

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

/** 获取概览统计（CNY 统一换算） */
export const fetchOverview = () =>
  apiClient.get('/api/v1/overview') as Promise<OverviewStats>

// ═══════════════════════════════════════════
// 品种目录
// ═══════════════════════════════════════════

/** 搜索品种（按 ticker 或名称模糊匹配） */
export const searchVarieties = (q: string, limit = 10) =>
  apiClient.get('/api/v1/varieties/search', {
    params: { q, limit },
  }) as Promise<AssetVariety[]>

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

/** 获取交易记录列表（三元组都可选筛选） */
export const fetchTransactions = (
  ticker?: string,
  asset_class?: string,
  market?: string,
  limit = 100,
) =>
  apiClient.get('/api/v1/transactions', {
    params: { ticker, asset_class, market, limit },
  }) as Promise<Transaction[]>

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

/** 获取全部归档持仓（按清仓日倒序） */
export const fetchClosedHoldings = () =>
  apiClient.get('/api/v1/closed-holdings') as Promise<ClosedHolding[]>

/** 获取单条归档持仓详情（含全部关联交易） */
export const fetchClosedHolding = (id: number) =>
  apiClient.get(`/api/v1/closed-holdings/${id}`) as Promise<ClosedHoldingDetail>

/** 获取全部归档交易（按交易日倒序，统一历史交易查询） */
export const fetchClosedTransactions = (limit = 500) =>
  apiClient.get('/api/v1/closed-transactions', { params: { limit } }) as Promise<ClosedTransaction[]>
