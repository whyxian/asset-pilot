export interface Overview {
  overview: {
    total_value: number
    total_cost: number
    total_pnl: number
    total_pnl_pct: number
    annualized_return: number
  }
  net_worth_history: { date: string; value: number; cost: number }[]
  asset_allocation: { market: string; label: string; value: number; pct: number }[]
}

export interface Holding {
  ticker: string
  name: string
  market: string
  asset_class: string
  quantity: number
  cost_price: number
  current_price: number
  total_invested: number
  market_value: number
  pnl: number
  pnl_pct: number
  first_buy_date: string
}

export interface Transaction {
  id: number
  ticker: string
  name: string
  date: string
  type: 'buy' | 'sell'
  quantity: number
  unit_price: number
  amount: number
  notes: string
}
