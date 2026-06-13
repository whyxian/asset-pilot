import { useState, useEffect, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useHoldings } from '@/hooks/useHoldings'
import type { Transaction } from '@/types'

interface TransactionFormData {
  ticker: string
  transaction_date: string
  type: 'buy' | 'sell'
  quantity: string
  unit_price: string
  amount: string
  notes: string
}

function emptyForm(): TransactionFormData {
  return {
    ticker: '',
    transaction_date: new Date().toISOString().slice(0, 10),
    type: 'buy',
    quantity: '',
    unit_price: '',
    amount: '',
    notes: '',
  }
}

function transactionToForm(t: Transaction): TransactionFormData {
  return {
    ticker: t.ticker,
    transaction_date: t.transaction_date,
    type: t.type,
    quantity: t.quantity != null ? String(t.quantity) : '',
    unit_price: t.unit_price != null ? String(t.unit_price) : '',
    amount: t.amount != null ? String(t.amount) : '',
    notes: t.notes ?? '',
  }
}

const marketOptionLabel: Record<string, string> = {
  CN: 'A 股',
  US: '美股',
  CRYPTO: '加密货币',
}

interface TransactionFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: TransactionFormData) => void
  /** 编辑模式：传入已有交易数据 */
  transaction?: Transaction
  /** 预填数据 — 持仓页"清仓"按钮打开时传入，覆盖默认 emptyForm */
  presetData?: Partial<TransactionFormData>
  /** 后端返回的错误信息 */
  error?: string | null
  /** 是否正在提交 */
  isPending?: boolean
}

export function TransactionFormDialog({
  open,
  onOpenChange,
  onSubmit,
  transaction,
  presetData,
  error,
  isPending,
}: TransactionFormDialogProps) {
  const isEdit = !!transaction
  const [form, setForm] = useState<TransactionFormData>(emptyForm())

  // 持仓清单作为 ticker 下拉来源（含已清仓品种，便于补录历史交易）
  const { data: holdings } = useHoldings()

  // 对话框打开/关闭时重置表单内容
  useEffect(() => {
    if (open) {
      if (transaction) {
        setForm(transactionToForm(transaction))
      } else if (presetData) {
        setForm({ ...emptyForm(), ...presetData })
      } else {
        setForm(emptyForm())
      }
    }
  }, [open, transaction, presetData])

  const updateField = useCallback(
    (key: keyof TransactionFormData, value: string) => {
      setForm((prev) => {
        const next = { ...prev, [key]: value }

        // quantity × unit_price → amount 自动联动（用户可后续手改 amount 覆盖）
        if (key === 'quantity' || key === 'unit_price') {
          const qty = parseFloat(key === 'quantity' ? value : prev.quantity)
          const price = parseFloat(key === 'unit_price' ? value : prev.unit_price)
          if (!isNaN(qty) && !isNaN(price)) {
            next.amount = String(qty * price)
          }
        }

        return next
      })
    },
    [],
  )

  const handleSubmit = () => {
    if (!form.ticker.trim()) return
    if (!form.transaction_date) return
    // 后端硬性约束：(quantity + unit_price) 或 amount 至少一组；不在前端硬挡，让后端报错展示在底部
    onSubmit(form)
  }

  // 编辑模式下当前 ticker 不在持仓中（理论上不应发生），添加 disabled 占位避免 select 显示空
  const tickerOptions = (holdings ?? []).map((h) => ({
    ticker: h.ticker,
    name: h.name,
    market: h.market,
    isOrphan: false,
  }))
  if (form.ticker && !tickerOptions.some((o) => o.ticker === form.ticker)) {
    tickerOptions.unshift({
      ticker: form.ticker,
      name: '(持仓中找不到该 ticker)',
      market: '',
      isOrphan: true,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑交易' : '新增交易'}</DialogTitle>
          <DialogDescription>
            {isEdit ? '修改交易记录' : '录入一笔买入或卖出交易（仅可选当前持仓品种）'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {/* 持仓品种下拉 */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">代码</label>
            <Select
              value={form.ticker}
              onValueChange={(v) => updateField('ticker', v)}
            >
              <SelectTrigger>
                <SelectValue placeholder={tickerOptions.length === 0 ? '尚无持仓 — 请先在持仓页建仓' : '选择持仓品种'} />
              </SelectTrigger>
              <SelectContent>
                {tickerOptions.map((o) => (
                  <SelectItem key={o.ticker} value={o.ticker} disabled={o.isOrphan}>
                    <span className="font-medium">{o.ticker}</span>
                    <span className="ml-2 text-muted-foreground">{o.name}</span>
                    {o.market && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {marketOptionLabel[o.market] || o.market}
                      </span>
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 交易日 + 方向 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">交易日</label>
              <Input
                type="date"
                value={form.transaction_date}
                onChange={(e) => updateField('transaction_date', e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">方向</label>
              <Select
                value={form.type}
                onValueChange={(v) => updateField('type', v as 'buy' | 'sell')}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="buy">买入</SelectItem>
                  <SelectItem value="sell">卖出</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* 数量 + 成交价 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">数量</label>
              <Input
                type="number"
                step="any"
                placeholder="100"
                value={form.quantity}
                onChange={(e) => updateField('quantity', e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">成交价</label>
              <Input
                type="number"
                step="any"
                placeholder="1700.00"
                value={form.unit_price}
                onChange={(e) => updateField('unit_price', e.target.value)}
              />
            </div>
          </div>

          {/* 金额（默认 = quantity × unit_price，可手改用于含手续费场景） */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">交易金额</label>
            <Input
              type="number"
              step="any"
              placeholder="自动计算: 数量 × 成交价（可手改含手续费）"
              value={form.amount}
              onChange={(e) => updateField('amount', e.target.value)}
            />
          </div>

          {/* 备注 */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">备注</label>
            <Input
              placeholder="可选"
              value={form.notes}
              onChange={(e) => updateField('notes', e.target.value)}
            />
          </div>

          {/* 后端错误（先建仓 / 卖超 / 字段缺失等都在此展示） */}
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={isPending}>
            {isPending ? '提交中...' : isEdit ? '保存' : '创建'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export type { TransactionFormData }
