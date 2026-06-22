import { useNavigate } from 'react-router-dom'
import { useClosedTransactions } from '@/hooks/useClosedHoldings'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowLeft } from 'lucide-react'
import { toNum, formatPrice } from '@/lib/utils'

const marketLabel: Record<string, string> = {
  CN: 'A 股',
  US: '美股',
  CRYPTO: '加密',
}

const typeLabel: Record<string, string> = {
  buy: '买入',
  sell: '卖出',
}

/** 公共头部：返回按钮 + 标题 */
function PageHeader() {
  const navigate = useNavigate()
  return (
    <div className="flex items-center gap-3">
      <Button variant="ghost" size="icon-sm" onClick={() => navigate('/transactions')}>
        <ArrowLeft className="w-4 h-4" />
      </Button>
      <h1 className="text-2xl font-bold">交易历史记录</h1>
    </div>
  )
}

export function ClosedTransactionsPage() {
  const { data, isLoading, isError, error, refetch } = useClosedTransactions()

  // ---- 加载态 ----
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm tabular-nums">
            <thead>
              <tr className="bg-muted/50">
                {['日期', '代码', '市场', '类型', '方向', '数量', '成交价', '金额', '费率', '备注'].map((h) => (
                  <th key={h} className="text-left p-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, i) => (
                <tr key={i} className="border-t">
                  {[...Array(7)].map((_, j) => (
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
          <p className="text-muted-foreground text-lg">暂无历史交易</p>
          <p className="text-sm text-muted-foreground">完成清仓后该周期的全部交易会归档到此页</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader />
        <p className="text-sm text-muted-foreground">仅展示已清仓周期的归档交易（只读）</p>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm tabular-nums">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left p-3">日期</th>
              <th className="text-left p-3">代码</th>
              <th className="text-left p-3">市场</th>
              <th className="text-left p-3">类型</th>
              <th className="text-left p-3">方向</th>
              <th className="text-right p-3">数量</th>
              <th className="text-right p-3">成交价</th>
              <th className="text-right p-3">金额</th>
              <th className="text-right p-3">费率</th>
              <th className="text-left p-3">备注</th>
            </tr>
          </thead>
          <tbody>
            {data.map((t) => (
              <tr key={t.id} className="border-t hover:bg-muted/30">
                <td className="p-3">{t.transaction_date}</td>
                <td className="p-3 font-medium">{t.ticker}</td>
                <td className="p-3"><Badge variant="outline">{marketLabel[t.market] || t.market}</Badge></td>
                <td className="p-3 text-muted-foreground">{t.asset_class}</td>
                <td className="p-3">
                  <Badge variant={t.type === 'buy' ? 'default' : 'destructive'}>
                    {typeLabel[t.type] || t.type}
                  </Badge>
                </td>
                <td className="p-3 text-right">
                  {t.quantity != null ? toNum(t.quantity).toLocaleString() : '-'}
                </td>
                <td className="p-3 text-right">
                  {t.unit_price != null ? formatPrice(t.unit_price) : '-'}
                </td>
                <td className="p-3 text-right">
                  {t.amount != null ? formatPrice(t.amount) : '-'}
                </td>
                <td className="p-3 text-right">
                  {t.fee_rate != null ? `${t.fee_rate}%` : '-'}
                </td>
                <td className="p-3 text-muted-foreground">{t.notes || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-sm text-muted-foreground">共 {data.length} 笔历史交易</p>
    </div>
  )
}
