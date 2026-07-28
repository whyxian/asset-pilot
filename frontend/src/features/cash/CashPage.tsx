import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { DollarSign, Plus, Minus, TrendingUp, TrendingDown } from 'lucide-react'
import { CountUp } from '@/components/ui/countup'
import { formatPrice, toNum } from '@/lib/utils'
import { useColors } from '@/lib/settings'
import { useCashBalances, useCashFlows, useCashDeposit, useCashWithdraw } from '@/hooks/useCashFlows'
import { toast } from 'sonner'
import type { CashBalance } from '@/types'

const CURRENCY = 'CNY'

const typeLabel: Record<string, string> = {
  deposit: '入金',
  withdraw: '出金',
  buy: '买入',
  sell: '卖出',
}

/** 入金 / 出金弹窗 */
function CashDialog({
  open,
  onOpenChange,
  mode,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  mode: 'deposit' | 'withdraw'
}) {
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('USD')
  const [notes, setNotes] = useState('')
  const depositMut = useCashDeposit()
  const withdrawMut = useCashWithdraw()
  const isPending = depositMut.isPending || withdrawMut.isPending

  async function handleSubmit() {
    const num = parseFloat(amount)
    if (!num || num <= 0) {
      toast.error('请输入有效金额')
      return
    }
    const mut = mode === 'deposit' ? depositMut : withdrawMut
    try {
      await mut.mutateAsync({ amount: num, currency, notes: notes || null })
      toast.success(mode === 'deposit' ? '入金成功' : '出金成功')
      setAmount('')
      setNotes('')
      onOpenChange(false)
    } catch {
      toast.error(mode === 'deposit' ? '入金失败' : '出金失败')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === 'deposit' ? '入金' : '出金'}</DialogTitle>
          <DialogDescription>
            {mode === 'deposit' ? '记录一笔外部资金注入' : '记录一笔资金取出'}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <span className="text-sm font-medium">金额</span>
            <Input
              type="number"
              step="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <span className="text-sm font-medium">币种</span>
            <select
              className="flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm mt-1"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              <option value="USD">USD</option>
              <option value="CNY">CNY</option>
              <option value="HKD">HKD</option>
            </select>
          </div>
          <div>
            <span className="text-sm font-medium">备注（可选）</span>
            <Input
              placeholder="如：工资、日常消费"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-1"
            />
          </div>
          <Button className="w-full" onClick={handleSubmit} disabled={isPending}>
            {isPending ? '处理中…' : mode === 'deposit' ? '确认入金' : '确认出金'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function CashPage() {
  const { data: balancesData, isLoading: balancesLoading, isError, error, refetch } = useCashBalances(CURRENCY)
  const { data: flows, isLoading: flowsLoading } = useCashFlows(100)
  const [mounted, setMounted] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<'deposit' | 'withdraw'>('deposit')
  const { upColor, downColor } = useColors()

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])

  const total = balancesData?.total ?? 0
  const displayCurrency = balancesData?.display_currency ?? CURRENCY
  const balances = balancesData?.balances ?? []
  const isPositive = total >= 0

  function fmtDate(d: string | null): string {
    if (!d) return '-'
    return d.slice(0, 10)
  }

  // ---- 错误态 ----
  if (isError) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">现金</h1>
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

  return (
    <div className="space-y-6 tabular-nums">
      {/* 标题 + 操作按钮 */}
      <div className={`transition-all duration-500 ease-out ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">现金</h1>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { setDialogMode('withdraw'); setDialogOpen(true) }}>
              <Minus className="w-4 h-4 mr-2" />出金
            </Button>
            <Button onClick={() => { setDialogMode('deposit'); setDialogOpen(true) }}>
              <Plus className="w-4 h-4 mr-2" />入金
            </Button>
          </div>
        </div>
      </div>

      {/* 左右分栏：左侧 sticky 余额，右侧流水 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：余额（sticky） */}
        <div className={`lg:col-span-1 transition-all duration-500 ease-out delay-50 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
          <div className="lg:sticky lg:top-8 space-y-4">
            {/* 总额卡片 */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  现金总额（{displayCurrency}）
                </CardTitle>
                <DollarSign className="w-4 h-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {balancesLoading ? (
                  <Skeleton className="h-8 w-40" />
                ) : (
                  <>
                    <div className={`${isPositive ? upColor : downColor} text-2xl font-bold`}>
                      <CountUp end={toNum(total)} duration={0.8} decimals={2} formattingFn={(v: number) => formatPrice(v, displayCurrency, 2)} />
                    </div>
                    {balancesData?.rate_stale && (
                      <p className="text-xs text-amber-600 mt-1">汇率可能过时（走了兜底）</p>
                    )}
                  </>
                )}
              </CardContent>
            </Card>

            {/* 各币种明细（始终展示） */}
            {balances.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-medium text-muted-foreground px-1">各币种明细</p>
                {balances.map((b: CashBalance) => (
                  <Card key={b.currency}>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardTitle className="text-sm text-muted-foreground">{b.currency}</CardTitle>
                      {b.balance >= 0
                        ? <TrendingUp className={`w-3.5 h-3.5 ${upColor}`} />
                        : <TrendingDown className={`w-3.5 h-3.5 ${downColor}`} />}
                    </CardHeader>
                    <CardContent>
                      <div className={`${b.balance >= 0 ? upColor : downColor} text-lg font-bold`}>
                        <CountUp end={toNum(b.balance)} duration={0.8} decimals={2} formattingFn={(v: number) => formatPrice(v, b.currency, 2)} />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 右侧：流水表 */}
        <div className={`lg:col-span-2 transition-all duration-500 ease-out delay-100 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm tabular-nums">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left p-3 whitespace-nowrap">日期</th>
                  <th className="text-left p-3 whitespace-nowrap">类型</th>
                  <th className="text-right p-3 whitespace-nowrap">金额</th>
                  <th className="text-left p-3 whitespace-nowrap">币种</th>
                  <th className="text-left p-3">备注</th>
                </tr>
              </thead>
              <tbody>
                {flowsLoading ? (
                  [...Array(8)].map((_, i) => (
                    <tr key={i} className="border-t">
                      {[...Array(5)].map((_, j) => (
                        <td key={j} className="p-3"><Skeleton className="h-4 w-full" /></td>
                      ))}
                    </tr>
                  ))
                ) : flows?.length ? (
                  flows.map((f) => {
                    const positive = f.amount >= 0
                    return (
                      <tr key={f.id} className="border-t hover:bg-muted/30">
                        <td className="p-3 text-muted-foreground whitespace-nowrap">{fmtDate(f.created_at)}</td>
                        <td className="p-3 whitespace-nowrap">
                          <Badge variant="outline">{typeLabel[f.type] || f.type}</Badge>
                        </td>
                        <td className={`p-3 text-right font-medium whitespace-nowrap ${positive ? upColor : downColor}`}>
                          {formatPrice(f.amount, f.currency, 2)}
                        </td>
                        <td className="p-3 whitespace-nowrap">{f.currency}</td>
                        <td className="p-3 text-muted-foreground max-w-48 truncate">{f.notes || '-'}</td>
                      </tr>
                    )
                  })
                ) : (
                  <tr>
                    <td colSpan={5} className="p-6 text-center text-muted-foreground">暂无资金流水，点击右上角「入金」开始记录</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {flows && flows.length > 0 && (
            <p className="text-sm text-muted-foreground mt-2">共 {flows.length} 笔流水</p>
          )}
        </div>
      </div>

      <CashDialog open={dialogOpen} onOpenChange={setDialogOpen} mode={dialogMode} />
    </div>
  )
}
