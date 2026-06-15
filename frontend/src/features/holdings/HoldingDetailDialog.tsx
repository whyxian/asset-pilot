import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useTransactions } from '@/hooks/useTransactions'
import { formatPrice, formatPct } from '@/lib/utils'
import type { HoldingWithQuote } from '@/types'

interface HoldingDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  holding: HoldingWithQuote | null
}

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

export function HoldingDetailDialog({ open, onOpenChange, holding }: HoldingDetailDialogProps) {
  const { data: transactions, isLoading: txnsLoading } = useTransactions(
    holding?.ticker,
    holding?.asset_class,
    holding?.market,
  )

  if (!holding) return null

  const holdingDays = Math.floor((Date.now() - new Date(holding.first_buy_date).getTime()) / 86400000) + 1
  const pnlPositive = toNum(holding.pnl) >= 0
  const pnlColor = pnlPositive ? 'text-green-600' : 'text-red-600'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle>{holding.name}</DialogTitle>
            <Badge variant="outline">{holding.ticker}</Badge>
          </div>
          <DialogDescription>
            {marketLabel[holding.market] || holding.market} · {holding.asset_class} · {holding.currency}
          </DialogDescription>
        </DialogHeader>

        {/* 核心指标统计卡 */}
        <div className="grid grid-cols-4 gap-3">
          <div className="rounded-lg border p-3">
            <div className="text-xs text-muted-foreground">市值</div>
            <div className="text-lg font-bold mt-0.5">{formatPrice(holding.market_value, holding.currency, 2)}</div>
          </div>
          <div className="rounded-lg border p-3">
            <div className="text-xs text-muted-foreground">盈亏</div>
            <div className={`text-lg font-bold mt-0.5 ${pnlColor}`}>
              {formatPrice(holding.pnl, holding.currency, 2)}
            </div>
          </div>
          <div className="rounded-lg border p-3">
            <div className="text-xs text-muted-foreground">盈亏率</div>
            <div className={`text-lg font-bold mt-0.5 ${pnlColor}`}>
              {formatPct(holding.pnl_pct)}
            </div>
          </div>
          <div className="rounded-lg border p-3">
            <div className="text-xs text-muted-foreground">年化回报</div>
            <div className={`text-lg font-bold mt-0.5 ${(typeof holding.annualized_return === 'string' || (holding.annualized_return ?? 0) >= 0) ? 'text-green-600' : 'text-red-600'}`}>
              {formatPct(holding.annualized_return)}
            </div>
          </div>
        </div>

        {/* 持仓明细 */}
        <div className="rounded-lg border px-3 py-2 flex items-baseline gap-x-5 text-sm text-muted-foreground">
          <span>持仓 <span className="text-foreground font-medium">{toNum(holding.quantity).toLocaleString()}</span></span>
          <span>成本 <span className="text-foreground">{formatPrice(holding.cost_price, holding.currency)}</span></span>
          <span>现价 <span className="text-foreground">{formatPrice(holding.current_price, holding.currency)}</span></span>
          <span>投入 <span className="text-foreground">{formatPrice(holding.total_invested, holding.currency, 2)}</span></span>
          <span>持有 <span className="text-foreground">{holdingDays} 天</span></span>
          <span>建仓 {holding.first_buy_date}</span>
        </div>

        {/* 关联交易流水 */}
        <div className="border-t pt-3">
          <h4 className="text-xs font-medium text-muted-foreground mb-2">
            关联交易流水{transactions ? `（${transactions.length} 笔）` : ''}
          </h4>

          {txnsLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : !transactions || transactions.length === 0 ? (
            <p className="text-muted-foreground text-sm py-2">暂无交易记录</p>
          ) : (
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
                  {transactions.map((t) => (
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
                        {t.unit_price != null ? formatPrice(t.unit_price, holding.currency) : '-'}
                      </td>
                      <td className="p-2 text-right">
                        {t.amount != null ? formatPrice(t.amount, holding.currency, 2) : '-'}
                      </td>
                      <td className="p-2 text-muted-foreground">{t.notes || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
