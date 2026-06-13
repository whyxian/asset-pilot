import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClosedHoldings } from '@/hooks/useClosedHoldings'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ClosedHoldingDetailDialog } from './ClosedHoldingDetailDialog'
import { Eye, ArrowLeft } from 'lucide-react'
import { Tooltip } from '@/components/ui/tooltip'
import { formatPrice, formatPct } from '@/lib/utils'
import type { ClosedHolding } from '@/types'

const marketLabel: Record<string, string> = {
  CN: 'A 股',
  US: '美股',
  CRYPTO: '加密货币',
}

function toNum(v: number | string): number {
  return typeof v === 'string' ? parseFloat(v) : v
}

/** 该周期 PnL% = realized_pnl / initial_total_invested × 100 */
function pnlPct(h: ClosedHolding): number | null {
  const total = toNum(h.initial_total_invested)
  if (!total || total === 0) return null
  return (toNum(h.realized_pnl) / total) * 100
}

/** 公共头部：返回按钮 + 标题 */
function PageHeader() {
  const navigate = useNavigate()
  return (
    <div className="flex items-center gap-3">
      <Button variant="ghost" size="icon-sm" onClick={() => navigate('/holdings')}>
        <ArrowLeft className="w-4 h-4" />
      </Button>
      <h1 className="text-2xl font-bold">历史持仓</h1>
    </div>
  )
}

export function HistoryPage() {
  const { data, isLoading, isError, error, refetch } = useClosedHoldings()
  const [detailId, setDetailId] = useState<number | null>(null)

  // ---- 加载态 ----
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                {['代码', '名称', '市场', '首买日', '清仓日', '持仓天数', '总投入', '已实现盈亏', '盈亏率', '操作'].map((h) => (
                  <th key={h} className="text-left p-3 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, i) => (
                <tr key={i} className="border-t">
                  {[...Array(10)].map((_, j) => (
                    <td key={j} className="p-3"><Skeleton className="h-4 w-full" /></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // ---- 错误态 ----
  if (isError) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <p className="text-destructive font-medium">加载失败</p>
          <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : '未知错误'}</p>
          <Button variant="outline" onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    )
  }

  // ---- 空态 ----
  if (!data || data.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-muted/20 gap-4">
          <p className="text-muted-foreground text-lg">暂无历史持仓</p>
          <p className="text-sm text-muted-foreground">完成一笔从建仓到清仓的完整周期后将在此显示</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader />

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left p-3 whitespace-nowrap">代码</th>
              <th className="text-left p-3">名称</th>
              <th className="text-left p-3 whitespace-nowrap">市场</th>
              <th className="text-left p-3 whitespace-nowrap">首买日</th>
              <th className="text-left p-3 whitespace-nowrap">清仓日</th>
              <th className="text-right p-3 whitespace-nowrap">持仓天数</th>
              <th className="text-right p-3 whitespace-nowrap">总投入</th>
              <th className="text-right p-3 whitespace-nowrap">已实现盈亏</th>
              <th className="text-right p-3 whitespace-nowrap">盈亏率</th>
              <th className="p-3 w-16 whitespace-nowrap">操作</th>
            </tr>
          </thead>
          <tbody>
            {data.map((h) => {
              const pct = pnlPct(h)
              const positive = toNum(h.realized_pnl) >= 0
              return (
                <tr key={h.id} className="border-t hover:bg-muted/30">
                  <td className="p-3 font-medium whitespace-nowrap">{h.ticker}</td>
                  <td className="p-3">
                    <Tooltip content={h.name}>
                      <span className="block max-w-40 truncate">{h.name}</span>
                    </Tooltip>
                  </td>
                  <td className="p-3 whitespace-nowrap">
                    <Badge variant="outline">{marketLabel[h.market] || h.market}</Badge>
                  </td>
                  <td className="p-3 whitespace-nowrap text-muted-foreground">{h.first_buy_date}</td>
                  <td className="p-3 whitespace-nowrap text-muted-foreground">{h.closed_at}</td>
                  <td className="p-3 text-right whitespace-nowrap">{h.holding_days} 天</td>
                  <td className="p-3 text-right whitespace-nowrap">{formatPrice(h.initial_total_invested, h.currency, 2)}</td>
                  <td className="p-3 text-right whitespace-nowrap">
                    <span className={`font-medium ${positive ? 'text-green-600' : 'text-red-600'}`}>
                      {formatPrice(h.realized_pnl, h.currency, 2)}
                    </span>
                  </td>
                  <td className="p-3 text-right whitespace-nowrap">
                    {pct === null ? (
                      <span className="text-muted-foreground">N/A</span>
                    ) : (
                      <span className={`font-medium ${positive ? 'text-green-600' : 'text-red-600'}`}>
                        {formatPct(pct)}
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    <Button variant="ghost" size="icon-sm" onClick={() => setDetailId(h.id)}>
                      <Eye className="w-3.5 h-3.5" />
                    </Button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <p className="text-sm text-muted-foreground">共 {data.length} 笔历史持仓</p>

      <ClosedHoldingDetailDialog
        id={detailId}
        open={detailId !== null}
        onOpenChange={(open) => !open && setDetailId(null)}
      />
    </div>
  )
}
