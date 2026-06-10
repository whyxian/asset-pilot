import { useMemo } from 'react'
import { useHoldings } from '@/hooks/useHoldings'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react'
import type { OverviewStats, AssetAllocation } from '@/types'

const marketLabel: Record<string, string> = {
  CN: 'A 股/基金',
  US: '美股',
  CRYPTO: '加密货币',
}

export function OverviewPage() {
  const { data: holdings, isLoading, isError, error, refetch } = useHoldings()

  // 从持仓数据计算概览统计
  const stats = useMemo<OverviewStats | null>(() => {
    if (!holdings || holdings.length === 0) return null
    // toNum 处理后端 Decimal 序列化为字符串的情况
    const toNum = (v: number | string): number => typeof v === 'string' ? parseFloat(v) : v
    const totalValue = holdings.reduce((s, h) => s + toNum(h.market_value), 0)
    const totalCost = holdings.reduce((s, h) => s + toNum(h.total_invested), 0)
    const totalPnl = totalValue - totalCost
    const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : null
    // 市值加权年化回报率
    let weightedReturn = 0
    let totalWeight = 0
    for (const h of holdings) {
      const mv = toNum(h.market_value)
      if (h.annualized_return != null && mv > 0) {
        weightedReturn += h.annualized_return * mv
        totalWeight += mv
      }
    }
    const avgAnnualized = totalWeight > 0 ? weightedReturn / totalWeight : null
    return {
      total_value: totalValue,
      total_cost: totalCost,
      total_pnl: totalPnl,
      total_pnl_pct: totalPnlPct,
      annualized_return: avgAnnualized,
    }
  }, [holdings])

  // 从持仓数据计算资产配比（按 market 分组）
  const allocation = useMemo<AssetAllocation[]>(() => {
    if (!holdings || holdings.length === 0) return []
    const toNum = (v: number | string): number => typeof v === 'string' ? parseFloat(v) : v
    const groups = new Map<string, { market: string; value: number }>()
    const total = holdings.reduce((s, h) => s + toNum(h.market_value), 0)
    for (const h of holdings) {
      const mv = toNum(h.market_value)
      const existing = groups.get(h.market)
      if (existing) {
        existing.value += mv
      } else {
        groups.set(h.market, { market: h.market, value: mv })
      }
    }
    return Array.from(groups.values()).map((g) => ({
      market: g.market,
      label: marketLabel[g.market] || g.market,
      value: g.value,
      pct: total > 0 ? (g.value / total) * 100 : 0,
    }))
  }, [holdings])

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
  if (!stats) {
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

  const isPositive = stats.total_pnl >= 0

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
              ¥{stats.total_value.toLocaleString()}
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
              ¥{stats.total_cost.toLocaleString()}
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
              {stats.total_pnl_pct != null
                ? `${isPositive ? '+' : ''}${stats.total_pnl_pct.toFixed(2)}%`
                : 'N/A'}
            </div>
            <p className="text-xs text-muted-foreground">
              ¥{isPositive ? '+' : ''}{stats.total_pnl.toLocaleString()}
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
              {stats.annualized_return != null
                ? `${stats.annualized_return >= 0 ? '+' : ''}${stats.annualized_return.toFixed(2)}%`
                : 'N/A'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 净值走势 — Phase 5 快照功能完成后启用 */}
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
      {allocation.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>资产配比</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {allocation.map((item) => (
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
        共 {holdings!.length} 个品种
      </p>
    </div>
  )
}
