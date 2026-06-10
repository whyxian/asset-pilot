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
  // 以下为实时计算字段
  current_price: number
  market_value: number
  pnl: number
  pnl_pct: number | null // total_invested=0 时为 null
  annualized_return: number | null // 无法计算时为 null
}

// ═══════════════════════════════════════════
// 概览（前端派生，非后端直接返回）
// ═══════════════════════════════════════════

export interface OverviewStats {
  total_value: number
  total_cost: number
  total_pnl: number
  total_pnl_pct: number | null
  annualized_return: number | null // 市值加权平均
}

export interface AssetAllocation {
  market: string
  label: string
  value: number // 市值
  pct: number // 占比%
}

/** 新增持仓请求体 */
export interface HoldingCreate {
  ticker: string
  name: string
  market: string
  asset_class: string
  currency: string
  quantity: number
  cost_price: number
  total_invested: number
  first_buy_date: string
}

/** 更新持仓请求体（所有字段可选） */
export interface HoldingUpdate {
  name?: string
  quantity?: number
  cost_price?: number
  total_invested?: number
  first_buy_date?: string
}

// ═══════════════════════════════════════════
// 交易
// ═══════════════════════════════════════════

/** 对接后端 Transaction 模型 */
export interface Transaction {
  id: number
  ticker: string
  transaction_date: string // "YYYY-MM-DD"
  type: 'buy' | 'sell'
  quantity: number | null
  unit_price: number | null
  amount: number | null
  notes: string | null
}

/** 新增交易记录请求体 */
export interface TransactionCreate {
  ticker: string
  transaction_date: string
  type: 'buy' | 'sell'
  quantity?: number | null
  unit_price?: number | null
  amount?: number | null
  notes?: string | null
}
