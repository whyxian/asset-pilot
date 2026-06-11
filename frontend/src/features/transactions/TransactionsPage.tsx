import { useTransactions } from '@/hooks/useTransactions'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { toNum, formatPrice } from '@/lib/utils'

const typeLabel: Record<string, string> = {
  buy: '买入',
  sell: '卖出',
}

export function TransactionsPage() {
  const { data: transactions, isLoading, isError, error, refetch } = useTransactions()

  // ---- 加载态 ----
  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">交易记录</h1>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left p-3">日期</th>
                <th className="text-left p-3">代码</th>
                <th className="text-left p-3">方向</th>
                <th className="text-right p-3">数量</th>
                <th className="text-right p-3">成交价</th>
                <th className="text-right p-3">金额</th>
                <th className="text-left p-3">备注</th>
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, i) => (
                <tr key={i} className="border-t">
                  {[...Array(7)].map((_, j) => (
                    <td key={j} className="p-3">
                      <Skeleton className="h-4 w-full" />
                    </td>
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
        <h1 className="text-2xl font-bold">交易记录</h1>
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <p className="text-destructive font-medium">加载失败</p>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : '未知错误'}
          </p>
          <Button variant="outline" onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    )
  }

  // ---- 空态 ----
  if (!transactions || transactions.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">交易记录</h1>
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-muted/20 gap-4">
          <p className="text-muted-foreground text-lg">暂无交易记录</p>
          <p className="text-sm text-muted-foreground">添加交易记录后将在此显示</p>
        </div>
      </div>
    )
  }

  // ---- 正常渲染 ----
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">交易记录</h1>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left p-3">日期</th>
              <th className="text-left p-3">代码</th>
              <th className="text-left p-3">方向</th>
              <th className="text-right p-3">数量</th>
              <th className="text-right p-3">成交价</th>
              <th className="text-right p-3">金额</th>
              <th className="text-left p-3">备注</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((t) => (
              <tr key={t.id} className="border-t hover:bg-muted/30">
                <td className="p-3">{t.transaction_date}</td>
                <td className="p-3 font-medium">{t.ticker}</td>
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
                <td className="p-3 text-muted-foreground">{t.notes || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-sm text-muted-foreground">
        共 {transactions.length} 条记录
      </p>
    </div>
  )
}
