import transactionsData from '@/data/transactions.json'
import type { Transaction } from '@/types'
import { Badge } from '@/components/ui/badge'

const data: Transaction[] = transactionsData as Transaction[]

export function TransactionsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">交易记录</h1>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left p-3">日期</th>
              <th className="text-left p-3">代码</th>
              <th className="text-left p-3">名称</th>
              <th className="text-left p-3">方向</th>
              <th className="text-right p-3">数量</th>
              <th className="text-right p-3">成交价</th>
              <th className="text-right p-3">金额</th>
              <th className="text-left p-3">备注</th>
            </tr>
          </thead>
          <tbody>
            {data.map((t) => (
              <tr key={t.id} className="border-t hover:bg-muted/30">
                <td className="p-3">{t.date}</td>
                <td className="p-3 font-medium">{t.ticker}</td>
                <td className="p-3">{t.name}</td>
                <td className="p-3">
                  <Badge variant={t.type === 'buy' ? 'default' : 'destructive'}>
                    {t.type === 'buy' ? '买入' : '卖出'}
                  </Badge>
                </td>
                <td className="p-3 text-right">{t.quantity}</td>
                <td className="p-3 text-right">¥{t.unit_price.toFixed(2)}</td>
                <td className="p-3 text-right">¥{t.amount.toLocaleString()}</td>
                <td className="p-3 text-muted-foreground">{t.notes || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-sm text-muted-foreground">
        共 {data.length} 条记录
      </p>
    </div>
  )
}
