import holdingsData from '@/data/holdings.json'
import type { Holding } from '@/types'
import { Badge } from '@/components/ui/badge'

const data: Holding[] = holdingsData as Holding[]

const marketLabel: Record<string, string> = {
  A: 'A 股',
  US: '美股',
  CRYPTO: '加密货币',
}

export function HoldingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">持仓</h1>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left p-3">代码</th>
              <th className="text-left p-3">名称</th>
              <th className="text-left p-3">市场</th>
              <th className="text-right p-3">持仓量</th>
              <th className="text-right p-3">成本价</th>
              <th className="text-right p-3">现价</th>
              <th className="text-right p-3">市值</th>
              <th className="text-right p-3">盈亏</th>
            </tr>
          </thead>
          <tbody>
            {data.map((h) => {
              const isPnlPositive = h.pnl >= 0
              return (
                <tr key={h.ticker} className="border-t hover:bg-muted/30">
                  <td className="p-3 font-medium">{h.ticker}</td>
                  <td className="p-3">{h.name}</td>
                  <td className="p-3">
                    <Badge variant="outline">{marketLabel[h.market] || h.market}</Badge>
                  </td>
                  <td className="p-3 text-right">{h.quantity}</td>
                  <td className="p-3 text-right">¥{h.cost_price.toFixed(2)}</td>
                  <td className="p-3 text-right">¥{h.current_price.toFixed(2)}</td>
                  <td className="p-3 text-right">¥{h.market_value.toLocaleString()}</td>
                  <td className={`p-3 text-right font-medium ${isPnlPositive ? 'text-green-600' : 'text-red-600'}`}>
                    {isPnlPositive ? '+' : ''}{h.pnl_pct.toFixed(2)}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <p className="text-sm text-muted-foreground">
        共 {data.length} 个品种
      </p>
    </div>
  )
}
