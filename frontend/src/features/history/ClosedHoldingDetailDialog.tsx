import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useClosedHolding } from '@/hooks/useClosedHoldings'
import { formatPrice, formatPct } from '@/lib/utils'

const marketLabel: Record<string, string> = {
  CN: 'A 股',
  US: '美股',
  CRYPTO: '加密货币',
}

const typeLabel: Record<string, string> = {
  buy: '买入',
  sell: '卖出',
}

function toNum(v: number | string): number {
  return typeof v === 'string' ? parseFloat(v) : v
}

interface ClosedHoldingDetailDialogProps {
  id: number | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ClosedHoldingDetailDialog({ id, open, onOpenChange }: ClosedHoldingDetailDialogProps) {
  const { data, isLoading } = useClosedHolding(id)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          {data ? (
            <>
              <div className="flex items-center gap-2">
                <DialogTitle>{data.name}</DialogTitle>
                <Badge variant="outline">{data.ticker}</Badge>
              </div>
              <DialogDescription>
                {marketLabel[data.market] || data.market} · {data.asset_class} · 已归档
              </DialogDescription>
            </>
          ) : (
            <DialogTitle>历史持仓详情</DialogTitle>
          )}
        </DialogHeader>

        {isLoading || !data ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* 该周期统计 */}
            <div className="grid grid-cols-2 gap-y-2 text-sm">
              <div className="text-muted-foreground">建仓基线</div>
              <div className="text-right">
                {toNum(data.initial_quantity).toLocaleString()} 股 @ {formatPrice(data.initial_cost_price, data.currency)}
              </div>
              <div className="text-muted-foreground">初始投入</div>
              <div className="text-right">{formatPrice(data.initial_total_invested, data.currency, 2)}</div>
              <div className="text-muted-foreground">首次买入</div>
              <div className="text-right">{data.first_buy_date}</div>
              <div className="text-muted-foreground">清仓日期</div>
              <div className="text-right text-orange-600">{data.closed_at}</div>
              <div className="text-muted-foreground">持仓天数</div>
              <div className="text-right">{data.holding_days} 天</div>
              <div className="text-muted-foreground font-medium">已实现盈亏</div>
              <div className={`text-right font-medium ${toNum(data.realized_pnl) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPrice(data.realized_pnl, data.currency, 2)}
                {toNum(data.initial_total_invested) > 0 && (
                  <span className="ml-2">
                    ({formatPct((toNum(data.realized_pnl) / toNum(data.initial_total_invested)) * 100)})
                  </span>
                )}
              </div>
            </div>

            {/* 该周期完整交易流水 */}
            <div className="border-t pt-3">
              <h4 className="text-xs font-medium text-muted-foreground mb-2">该周期交易流水（{data.transactions.length} 笔）</h4>
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/50">
                      <th className="text-left p-2">日期</th>
                      <th className="text-left p-2">方向</th>
                      <th className="text-right p-2">数量</th>
                      <th className="text-right p-2">成交价</th>
                      <th className="text-right p-2">金额</th>
                      <th className="text-left p-2">备注</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.transactions.map((t) => (
                      <tr key={t.id} className="border-t">
                        <td className="p-2">{t.transaction_date}</td>
                        <td className="p-2">
                          <Badge variant={t.type === 'buy' ? 'default' : 'destructive'}>
                            {typeLabel[t.type] || t.type}
                          </Badge>
                        </td>
                        <td className="p-2 text-right">
                          {t.quantity != null ? toNum(t.quantity).toLocaleString() : '-'}
                        </td>
                        <td className="p-2 text-right">
                          {t.unit_price != null ? formatPrice(t.unit_price, data.currency) : '-'}
                        </td>
                        <td className="p-2 text-right">
                          {t.amount != null ? formatPrice(t.amount, data.currency, 2) : '-'}
                        </td>
                        <td className="p-2 text-muted-foreground">{t.notes || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
