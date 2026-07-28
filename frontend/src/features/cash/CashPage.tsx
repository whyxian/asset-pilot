import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Plus, Minus, ArrowLeft, ArrowRight, TrendingUp, TrendingDown } from 'lucide-react'
import { formatPrice } from '@/lib/utils'
import { useColors } from '@/lib/settings'
import { useCashBalances, useCashFlows, useCashDeposit, useCashWithdraw } from '@/hooks/useCashFlows'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import type { CashBalance } from '@/types'

const CURRENCY = 'CNY'

const typeLabel: Record<string, string> = {
  deposit: '入金',
  withdraw: '出金',
  buy: '买入',
  sell: '卖出',
}

const typeIcon: Record<string, typeof ArrowLeft> = {
  deposit: TrendingUp,
  withdraw: TrendingDown,
  buy: ArrowRight,
  sell: ArrowLeft,
}

const typeColor: Record<string, string> = {
  deposit: 'text-green-600',
  withdraw: 'text-red-600',
  buy: 'text-red-600',
  sell: 'text-green-600',
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
            />
          </div>
          <div>
            <span className="text-sm font-medium">币种</span>
            <select
              className="flex h-10 w-full rounded-md border bg-background px-3 py-2 text-sm"
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
  const { data: balancesData, isLoading: balancesLoading } = useCashBalances(CURRENCY)
  const { data: flows, isLoading: flowsLoading } = useCashFlows(100)
  const [mounted, setMounted] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<'deposit' | 'withdraw'>('deposit')
  const [showDetail, setShowDetail] = useState(false)
  const { upColor, downColor } = useColors()
  const navigate = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])

  /** 格式时间 */
  function fmtDate(d: string | null): string {
    if (!d) return '-'
    return d.slice(0, 10)
  }

  const total = balancesData?.total ?? 0
  const displayCurrency = balancesData?.display_currency ?? CURRENCY
  const balances = balancesData?.balances ?? []
  const hasMultipleCurrencies = balances.length > 1

  return (
    <div className="space-y-6">
      <div className={`flex items-center gap-3 transition-all duration-500 ease-out ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <Button variant="ghost" size="icon-sm" onClick={() => navigate('/')}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <h1 className="text-2xl font-bold">现金管理</h1>
      </div>

      {/* 余额卡片 */}
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 transition-all duration-500 ease-out delay-50 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        {balancesLoading ? (
          <Skeleton className="h-24" />
        ) : (
          <Card>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-sm text-muted-foreground">
                现金总额（{displayCurrency}）
              </CardTitle>
              {hasMultipleCurrencies && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setShowDetail((v) => !v)}
                >
                  {showDetail ? '收起明细' : '查看各币种'}
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <span className={`text-2xl font-bold ${total >= 0 ? upColor : downColor}`}>
                {formatPrice(total, displayCurrency, 2)}
              </span>
              {balancesData?.rate_stale && (
                <p className="text-xs text-amber-600 mt-1">汇率可能过时（走了兜底）</p>
              )}
            </CardContent>
          </Card>
        )}

        {/* 各币种明细（点按钮才显示） */}
        {showDetail && balances.map((b: CashBalance) => (
          <Card key={b.currency}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">{b.currency} 现金</CardTitle>
            </CardHeader>
            <CardContent>
              <span className={`text-2xl font-bold ${b.balance >= 0 ? upColor : downColor}`}>
                {formatPrice(b.balance, b.currency, 2)}
              </span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 操作按钮 */}
      <div className={`flex gap-3 transition-all duration-500 ease-out delay-75 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <Button
          onClick={() => { setDialogMode('deposit'); setDialogOpen(true) }}
        >
          <Plus className="w-4 h-4 mr-1" /> 入金
        </Button>
        <Button
          variant="outline"
          onClick={() => { setDialogMode('withdraw'); setDialogOpen(true) }}
        >
          <Minus className="w-4 h-4 mr-1" /> 出金
        </Button>
      </div>

      {/* 流水列表 */}
      <div className={`transition-all duration-500 ease-out delay-100 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <h2 className="text-lg font-semibold mb-3">资金流水</h2>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm tabular-nums">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left p-3">日期</th>
                <th className="text-left p-3">类型</th>
                <th className="text-right p-3">金额</th>
                <th className="text-left p-3">币种</th>
                <th className="text-left p-3">备注</th>
              </tr>
            </thead>
            <tbody>
              {flowsLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-t">
                    <td colSpan={5} className="p-3"><Skeleton className="h-4 w-full" /></td>
                  </tr>
                ))
              ) : flows?.length ? (
                flows.map((f) => {
                  const IconComp = typeIcon[f.type] || ArrowLeft
                  return (
                    <tr key={f.id} className="border-t hover:bg-muted/30">
                      <td className="p-3 text-muted-foreground whitespace-nowrap">{fmtDate(f.created_at)}</td>
                      <td className="p-3 whitespace-nowrap">
                        <Badge variant="outline" className={typeColor[f.type]}>
                          <IconComp className="w-3 h-3 mr-1 inline" />
                          {typeLabel[f.type] || f.type}
                        </Badge>
                      </td>
                      <td className={`p-3 text-right font-medium whitespace-nowrap ${f.amount >= 0 ? upColor : downColor}`}>
                        {formatPrice(f.amount, f.currency, 2)}
                      </td>
                      <td className="p-3 whitespace-nowrap">{f.currency}</td>
                      <td className="p-3 text-muted-foreground max-w-48 truncate">{f.notes || '-'}</td>
                    </tr>
                  )
                })
              ) : (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-muted-foreground">暂无资金流水</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <CashDialog open={dialogOpen} onOpenChange={setDialogOpen} mode={dialogMode} />
    </div>
  )
}
