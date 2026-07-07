import { useEffect, useState } from 'react'
import { useOverview } from '@/hooks/useOverview'
import { useCreateSnapshot, useSnapshots } from '@/hooks/useSnapshots'
import { fetchOverview } from '@/api/endpoints'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { CountUp } from '@/components/ui/countup'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Camera, RefreshCw, TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react'
import { formatPrice, formatPct, toNum } from '@/lib/utils'
import { useColors } from '@/lib/settings'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts'

const CURRENCY = 'CNY'

export function OverviewPage() {
  const { data: stats, isLoading, isError, error, refetch } = useOverview(CURRENCY)
  const { data: snapshots } = useSnapshots(CURRENCY)
  const createSnapshotMut = useCreateSnapshot()
  const queryClient = useQueryClient()
  const { upColor, downColor } = useColors()

  // 入场动画：卡片 + 配比进度条统一在 mount 后展开
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])

  // 手动刷新：force_refresh=true 绕过基金 15 分钟缓存，强制拉最新行情后写回缓存
  const refreshMut = useMutation({
    mutationFn: () => fetchOverview(CURRENCY, true),
    onSuccess: (data) => {
      queryClient.setQueryData(['overview', CURRENCY], data)
      queryClient.invalidateQueries({ queryKey: ['holdings'] })
      toast.success('行情已刷新')
    },
    onError: (e: unknown) => toast.error('刷新失败', {
      description: e instanceof Error ? e.message : '未知错误',
    }),
  })

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
  if (!stats || (stats.total_value === 0 && stats.allocation.length === 0)) {
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
    <div className="space-y-6 tabular-nums">
      {/* 标题 + 操作按钮 */}
      <div className={`transition-all duration-500 ease-out ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">概览</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => refreshMut.mutate()}
            disabled={refreshMut.isPending}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshMut.isPending ? 'animate-spin' : ''}`} />
            {refreshMut.isPending ? '刷新中...' : '刷新'}
          </Button>
          <Button
            variant="outline"
            onClick={() => createSnapshotMut.mutate()}
            disabled={createSnapshotMut.isPending}
          >
            <Camera className="w-4 h-4 mr-2" />
            {createSnapshotMut.isPending ? '记录中...' : '记录快照'}
          </Button>
        </div>
      </div>
      </div>

      {/* 统计卡 */}
      <div className={`grid grid-cols-2 lg:grid-cols-4 gap-4 transition-all duration-500 ease-out ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总市值</CardTitle>
            <Wallet className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <CountUp end={toNum(stats.total_value)} duration={0.8} decimals={2} formattingFn={(v: number) => formatPrice(v, stats.currency, 2)} />
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
              <CountUp end={toNum(stats.total_cost)} duration={0.8} decimals={2} formattingFn={(v: number) => formatPrice(v, stats.currency, 2)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总盈亏</CardTitle>
            {isPositive
              ? <TrendingUp className={`w-4 h-4 ${upColor}`} />
              : <TrendingDown className={`w-4 h-4 ${downColor}`} />
            }
          </CardHeader>
          <CardContent>
            <div className={`${isPositive ? upColor : downColor} inline-flex items-baseline gap-2`}>
              <span className="text-2xl font-bold">{isPositive ? '+' : ''}<CountUp end={toNum(stats.total_pnl)} duration={0.8} decimals={2} formattingFn={(v: number) => formatPrice(v, stats.currency, 2)} /></span>
              <span className="text-sm text-muted-foreground">
                {formatPct(stats.total_pnl_pct)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">历史累计总收益</CardTitle>
            {stats.cumulative_return_pct != null ? (
              stats.cumulative_return >= 0
                ? <TrendingUp className={`w-4 h-4 ${upColor}`} />
                : <TrendingDown className={`w-4 h-4 ${downColor}`} />
            ) : null}
          </CardHeader>
          <CardContent>
            {stats.cumulative_return_pct != null ? (
              <div className={`inline-flex items-baseline gap-2 ${stats.cumulative_return >= 0 ? upColor : downColor}`}>
                <span className="text-2xl font-bold">
                  {stats.cumulative_return >= 0 ? '+' : ''}<CountUp end={toNum(stats.cumulative_return)} duration={0.8} decimals={2} formattingFn={(v: number) => formatPrice(v, stats.currency, 2)} />
                </span>
                <span className="text-sm text-muted-foreground">
                  {formatPct(stats.cumulative_return_pct)}
                </span>
              </div>
            ) : (
              <div className="text-2xl font-bold text-muted-foreground">—</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 净值走势 */}
      <div className={`transition-all duration-500 ease-out delay-100 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <Card>
        <CardHeader>
          <CardTitle>净值走势</CardTitle>
        </CardHeader>
        <CardContent>
          {!snapshots || snapshots.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 gap-2 text-sm text-muted-foreground">
              <p>暂无快照数据</p>
              <p className="text-xs">点击右上角「记录快照」开始追踪净值走势</p>
            </div>
          ) : snapshots.length === 1 ? (
            <div className="flex flex-col items-center justify-center h-32 gap-2 text-sm text-muted-foreground">
              <p>已有 1 条快照（{snapshots[0].snapshot_date}）</p>
              <p className="text-xs">至少需要 2 条快照才能绘制走势图</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={snapshots} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="snapshot_date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => v.slice(5)}  // MM-DD
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  domain={['auto', 'auto']}
                />
                <RechartsTooltip
                  formatter={(value: number) => formatPrice(value, CURRENCY, 2)}
                  labelFormatter={(label) => `日期：${label}`}
                />
                <Line
                  type="linear"
                  dataKey="total_value"
                  name="总市值"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ r: 2, strokeWidth: 1 }}
                  activeDot={{ r: 5 }}
                  isAnimationActive={true}
                  animationDuration={600}
                  animationEasing="ease-out"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
      </div>

      {/* 资产配比 */}
      {stats.allocation.length > 0 && (
        <div className={`transition-all duration-500 ease-out delay-200 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <Card>
          <CardHeader>
            <CardTitle>资产配比</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.allocation.map((item, i) => (
                <div key={item.market} className="flex items-center gap-4">
                  <span className="w-20 text-sm">{item.label}</span>
                  <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500 ease-out bg-primary"
                      style={{
                        width: mounted ? `${item.pct}%` : '0%',
                        transitionDelay: `${i * 80}ms`,
                      }}
                    />
                  </div>
                  <span className="w-20 text-right text-sm text-muted-foreground">
                    {item.pct.toFixed(1)}%
                  </span>
                  <span className="w-28 text-right text-xs text-muted-foreground">
                    {formatPrice(item.value, stats.currency, 2)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        </div>
      )}

      <p className={`text-sm text-center transition-all duration-500 ease-out delay-[250ms] ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'} ${stats.rate_stale ? 'text-amber-600' : 'text-muted-foreground'}`}>
        {stats.rate_stale
          ? `⚠ 汇率非最新（来自 ${stats.rate_source_date ?? '未知日期'}），网络异常时使用历史汇率兜底 · 历史快照按当时汇率换算`
          : `汇率数据由 exchangerates 提供 · 更新于 ${stats.rate_source_date ?? '未知'} · 历史快照按当时汇率换算`}
      </p>
    </div>
  )
}
