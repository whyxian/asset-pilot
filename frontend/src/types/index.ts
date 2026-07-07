// ═══════════════════════════════════════════
// 行情
// ═══════════════════════════════════════════

/** 对接后端 AssetQuote 模型 */
export interface AssetQuote {
  ticker: string
  market: string // "CN" / "US" / "CRYPTO"
  name: string
  price: number // Decimal → number
  currency: string // "CNY" / "USD"
  change_price: number | null
  change_ratio: number | null
  updated_at: string // ISO datetime
  source: string // "TENCENT" / "SINA" / "COINGLASS" / "EASTMONEY_FUND" / "AKSHARE"
}

// ═══════════════════════════════════════════
// 持仓
// ═══════════════════════════════════════════

/** 对接后端 AssetVariety 模型 — 品种目录 */
export interface AssetVariety {
  ticker: string
  name: string
  market: string
  asset_class: string
  sub_category: string | null
  currency: string
  is_active: boolean
}

/** 对接后端 HoldingWithQuote 模型 — 持仓 + 实时行情 + 计算字段 */
export interface HoldingWithQuote {
  ticker: string
  name: string
  market: string // "CN" / "US" / "CRYPTO"
  asset_class: string // "STOCK" / "FUND" / "CRYPTO"
  currency: string
  quantity: number
  cost_price: number
  total_invested: number
  first_buy_date: string // "YYYY-MM-DD"
  first_buy_price: number      // 建仓首笔买入价（盈亏率分母）
  liquidated_at: string | null // 清仓日期，未清仓为 null
  // 以下为实时计算字段
  current_price: number
  market_value: number
  pnl: number
  pnl_pct: number | string | null // 成本>0 时=传统公式，≤0 时=剩余底仓收益率
  annualized_return: number | string | null // 历史累计总收益率（Modified Dietz）
  quote_status: 'REALTIME' | 'HISTORICAL' | 'UNAVAILABLE' // 行情状态
}

export interface MarketSummary {
  market: string            // "CN" / "US" / "CRYPTO"
  label: string             // 显示名，如 "A 股"
  count: number             // 该市场持仓品种数
  value_usd: number         // 该市场总市值（USD，跨币种聚合用）
  pct: number               // 占组合总市值百分比
}

export interface HoldingsWithQuotesResponse {
  holdings: HoldingWithQuote[]
  market_summary: MarketSummary[]
}

// ═══════════════════════════════════════════
// 概览（来自后端 API）
// ═══════════════════════════════════════════

export interface AllocationItem {
  market: string
  label: string
  value: number      // 改名 value_cny → value（数值的币种由父对象的 currency 决定）
  pct: number
}

export interface OverviewStats {
  currency: string             // 当前数据所在币种，如 "CNY" / "USD"
  total_value: number          // 改名 total_value_cny → total_value
  total_cost: number
  total_pnl: number
  total_pnl_pct: number | string | null
  cumulative_return_pct: number | string | null // 历史累计总收益率（Modified Dietz）
  cumulative_return: number                    // 历史累计收益金额
  allocation: AllocationItem[]
  rate_source_date: string | null   // 当前所用汇率的日期（YYYY-MM-DD）
  rate_stale: boolean               // 汇率是否走了兜底（旧汇率，需警告）
}

export interface NetWorthSnapshot {
  snapshot_date: string  // YYYY-MM-DD
  currency: string
  total_value: number
  total_cost: number
  total_pnl: number
  total_pnl_pct: number | string | null
  annualized_return: number | string | null
  allocation: AllocationItem[]
}

export interface AssetSnapshot {
  snapshot_date: string
  ticker: string
  asset_class: string
  market: string
  name: string
  currency: string  // 该品种原币
  quantity: number
  unit_value: number
  cost_value: number
  market_value: number
  total_invested: number
  unrealized_pnl: number
  return_pct: number | null
  display_currency: string
  market_value_in_currency: number
  total_invested_in_currency: number
}

/** 新增持仓请求体 */
export interface HoldingCreate {
  ticker: string
  name: string
  market: string
  asset_class: string
  currency: string
  quantity: string  // Decimal 字符串，避免 parseFloat 精度损失（crypto 需要 8 位小数）
  cost_price: string
  total_invested: string
  first_buy_date: string
}

/** 更新持仓请求体（所有字段可选） */
export interface HoldingUpdate {
  name?: string
  quantity?: string  // Decimal 字符串
  cost_price?: string
  total_invested?: string
  first_buy_date?: string
}

// ═══════════════════════════════════════════
// 交易
// ═══════════════════════════════════════════

/** 对接后端 Transaction 模型 */
export interface Transaction {
  id: number
  ticker: string
  asset_class: string  // STOCK / FUND / CRYPTO
  market: string       // CN / US / CRYPTO
  transaction_date: string // "YYYY-MM-DD"
  type: 'buy' | 'sell'
  quantity: number | null
  unit_price: number | null
  amount: number | null
  fee_rate: number | null  // 费率百分比（如 0.03 表示万分之三）
  notes: string | null
}

/** 新增交易记录请求体 */
export interface TransactionCreate {
  ticker: string
  asset_class: string
  market: string
  transaction_date: string
  type: 'buy' | 'sell'
  quantity?: string | null  // Decimal 字符串
  unit_price?: string | null
  amount?: string | null
  notes?: string | null
}

/** 更新交易记录请求体（所有字段可选） */
export interface TransactionUpdate {
  ticker?: string
  asset_class?: string
  market?: string
  transaction_date?: string
  type?: 'buy' | 'sell'
  quantity?: string | null  // Decimal 字符串
  unit_price?: string | null
  amount?: string | null
  notes?: string | null
}

// ═══════════════════════════════════════════
// 历史持仓（已归档的完整持仓周期）
// ═══════════════════════════════════════════

/** 对接后端 ClosedTransaction 模型 */
export interface ClosedTransaction {
  id: number
  closed_holding_id: number
  ticker: string
  asset_class: string
  market: string
  transaction_date: string
  type: 'buy' | 'sell'
  quantity: number | null
  unit_price: number | null
  amount: number | null
  fee_rate: number | null
  notes: string | null
  original_id: number | null
}

/** 对接后端 ClosedHolding 模型 */
export interface ClosedHolding {
  id: number
  ticker: string
  name: string
  market: string
  asset_class: string
  currency: string
  total_buy_amount: number  // 该周期总买入金额（sum(buy.amount)）
  first_buy_date: string
  first_buy_price: number    // 建仓首笔买入价
  closed_at: string
  holding_days: number
  realized_pnl: number
  // Modified Dietz 收益率
  pnl_pct: number | null
  is_crazy_trader: boolean
}

/** 归档持仓详情 — 含该周期全部交易 */
export interface ClosedHoldingDetail extends ClosedHolding {
  transactions: ClosedTransaction[]
}
