import overviewData from '@/data/overview.json'
import type { Overview } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react'

const data: Overview = overviewData as Overview

export function OverviewPage() {
  const { overview, net_worth_history, asset_allocation } = data
  const isPositive = overview.total_pnl >= 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">概览</h1>

      {/* 统计卡 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总市值</CardTitle>
            <Wallet className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">¥{overview.total_value.toLocaleString()}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总成本</CardTitle>
            <DollarSign className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">¥{overview.total_cost.toLocaleString()}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总盈亏</CardTitle>
            {isPositive
              ? <TrendingUp className="w-4 h-4 text-green-500" />
              : <TrendingDown className="w-4 h-4 text-red-500" />
            }
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? '+' : ''}{overview.total_pnl_pct.toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground">
              ¥{isPositive ? '+' : ''}{overview.total_pnl.toLocaleString()}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">年化回报率</CardTitle>
            <TrendingUp className="w-4 h-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              +{overview.annualized_return.toFixed(2)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 净值走势（简化为表格展示） */}
      <Card>
        <CardHeader>
          <CardTitle>净值走势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="text-left py-2">日期</th>
                  <th className="text-right py-2">市值</th>
                  <th className="text-right py-2">成本</th>
                </tr>
              </thead>
              <tbody>
                {net_worth_history.map((item) => (
                  <tr key={item.date} className="border-b last:border-0">
                    <td className="py-2">{item.date}</td>
                    <td className="text-right py-2">¥{item.value.toLocaleString()}</td>
                    <td className="text-right py-2">¥{item.cost.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* 资产配比 */}
      <Card>
        <CardHeader>
          <CardTitle>资产配比</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {asset_allocation.map((item) => (
              <div key={item.market} className="flex items-center gap-4">
                <span className="w-20 text-sm">{item.label}</span>
                <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${item.pct}%` }}
                  />
                </div>
                <span className="w-20 text-right text-sm text-muted-foreground">
                  {item.pct.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
