import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
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

export function HoldingDetailDialog({ open, onOpenChange, holding }: HoldingDetailDialogProps) {
  if (!holding) return null

  const holdingDays = Math.floor((Date.now() - new Date(holding.first_buy_date).getTime()) / 86400000) + 1

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
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
              {holding.liquidated_at && (
                <>
                  <div><span className="text-muted-foreground">清仓日期</span></div>
                  <div className="text-right text-orange-600">{holding.liquidated_at}</div>
                </>
              )}
              <div><span className="text-muted-foreground">持有天数</span></div>
              <div className="text-right">{holdingDays} 天</div>
              <div><span className="text-muted-foreground">年化回报率</span></div>
              <div className={`text-right font-medium ${(holding.annualized_return ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPct(holding.annualized_return)}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
