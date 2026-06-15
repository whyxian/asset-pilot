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
  // 按三元组过滤该持仓的关联交易
  const { data: transactions, isLoading: txnsLoading } = useTransactions(
    holding?.ticker,
    holding?.asset_class,
    holding?.market,
  )

  if (!holding) return null

  const holdingDays = Math.floor((Date.now() - new Date(holding.first_buy_date).getTime()) / 86400000) + 1

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle>{holding.name}</DialogTitle>
            <Badge variant="outline">{holding.ticker}</Badge>
          </div>
          <DialogDescription>
            {marketLabel[holding.market] || holding.market} · {holding.asset_class}
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4 text-sm">
          {/* 基本信息 */}
          <div className="col-span-2">
            <h4 className="text-xs font-medium text-muted-foreground mb-2">基本信息</h4>
            <div className="grid grid-cols-2 gap-y-2">
              <div><span className="text-muted-foreground">品种代码</span></div>
              <div className="text-right font-medium">{holding.ticker}</div>
              <div><span className="text-muted-foreground">品种名称</span></div>
              <div className="text-right font-medium">{holding.name}</div>
              <div><span className="text-muted-foreground">市场</span></div>
              <div className="text-right">{marketLabel[holding.market] || holding.market}</div>
              <div><span className="text-muted-foreground">类别</span></div>
              <div className="text-right">{holding.asset_class}</div>
              <div><span className="text-muted-foreground">货币</span></div>
              <div className="text-right">{holding.currency}</div>
            </div>
          </div>

          <div className="col-span-2 border-t pt-3">
            <h4 className="text-xs font-medium text-muted-foreground mb-2">持仓与行情</h4>
            <div className="grid grid-cols-2 gap-y-2">
              <div><span className="text-muted-foreground">持仓量</span></div>
              <div className="text-right font-medium">{holding.quantity.toLocaleString()}</div>
              <div><span className="text-muted-foreground">成本价</span></div>
              <div className="text-right">{formatPrice(holding.cost_price, holding.currency)}</div>
              <div><span className="text-muted-foreground">现价</span></div>
              <div className="text-right">{formatPrice(holding.current_price, holding.currency)}</div>
              <div><span className="text-muted-foreground">市值</span></div>
              <div className="text-right font-medium">{formatPrice(holding.market_value, holding.currency, 2)}</div>
              <div><span className="text-muted-foreground">总投入</span></div>
              <div className="text-right">{formatPrice(holding.total_invested, holding.currency, 2)}</div>
            </div>
          </div>

          <div className="col-span-2 border-t pt-3">
            <h4 className="text-xs font-medium text-muted-foreground mb-2">盈亏与回报</h4>
            <div className="grid grid-cols-2 gap-y-2">
              <div><span className="text-muted-foreground">盈亏额</span></div>
              <div className={`text-right font-medium ${holding.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPrice(holding.pnl, holding.currency, 2)}
              </div>
              <div><span className="text-muted-foreground">盈亏率</span></div>
              <div className={`text-right font-medium ${(holding.pnl_pct ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPct(holding.pnl_pct)}
              </div>
              <div><span className="text-muted-foreground">首次买入</span></div>
              <div className="text-right">{holding.first_buy_date}</div>
              <div><span className="text-muted-foreground">持有天数</span></div>
              <div className="text-right">{holdingDays} 天</div>
              <div><span className="text-muted-foreground">年化回报率</span></div>
              <div className={`text-right font-medium ${(holding.annualized_return ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPct(holding.annualized_return)}
              </div>
            </div>
          </div>

          {/* 关联交易流水 */}
          <div className="col-span-2 border-t pt-3">
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
        </div>
      </DialogContent>
    </Dialog>
  )
}
