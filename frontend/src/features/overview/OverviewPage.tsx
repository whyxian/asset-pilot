import { useOverview } from '@/hooks/useOverview'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react'
import { formatPrice, formatPct } from '@/lib/utils'
import type { OverviewStats } from '@/types'

export function OverviewPage() {
  const { data: stats, isLoading, isError, error, refetch } = useOverview()

  // ---- 加载态 ----
  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">概览</h1>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-20" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardHeader><Skeleton className="h-5 w-24" /></CardHeader>
          <CardContent><Skeleton className="h-32 w-full" /></CardContent>
        </Card>
      </div>
    )
  }

  // ---- 错误态 ----
  if (isError) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">概览</h1>
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <p className="text-destructive font-medium">加载失败</p>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : '未知错误'}
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            重试
          </Button>
        </div>
      </div>
    )
  }

  // ---- 空持仓 ----
  if (!stats || stats.total_value_cny === 0 && stats.allocation.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">概览</h1>
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-muted/20 gap-4">
          <Wallet className="w-12 h-12 text-muted-foreground" />
          <p className="text-muted-foreground text-lg">暂无持仓数据</p>
          <p className="text-sm text-muted-foreground">添加持仓后将在此显示概览统计</p>
        </div>
      </div>
    )
  }

  const isPositive = stats.total_pnl_cny >= 0

  // ---- 正常渲染 ----
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
            <div className="text-2xl font-bold">
              {formatPrice(stats.total_value_cny, 'CNY')}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总成本</CardTitle>
            <DollarSign className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPrice(stats.total_cost_cny, 'CNY')}
            </div>
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
              {formatPct(stats.total_pnl_pct)}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatPrice(stats.total_pnl_cny, 'CNY')}
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
              {formatPct(stats.annualized_return)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 净值走势 — Phase 6 快照功能完成后启用 */}
      <Card>
        <CardHeader>
          <CardTitle>净值走势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
            净值历史将在后续版本中提供
          </div>
        </CardContent>
      </Card>

      {/* 资产配比 */}
      {stats.allocation.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>资产配比</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.allocation.map((item) => (
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
      )}

      <p className="text-sm text-muted-foreground">
        汇率数据由 exchangerates 提供 · 每小时更新
      </p>
    </div>
  )
}
