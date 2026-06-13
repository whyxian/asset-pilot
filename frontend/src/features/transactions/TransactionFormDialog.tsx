import { useState, useEffect, useCallback, useRef } from 'react'
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
import { searchVarieties } from '@/api/endpoints'
import type { AssetVariety, Transaction } from '@/types'

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
  error,
  isPending,
}: TransactionFormDialogProps) {
  const isEdit = !!transaction
  const [form, setForm] = useState<TransactionFormData>(emptyForm())

  // ---- 品种搜索下拉（与 HoldingFormDialog 同款逻辑） ----
  const [searchResults, setSearchResults] = useState<AssetVariety[]>([])
  const [searching, setSearching] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()
  const wrapperRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭下拉
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 对话框打开/关闭时重置
  useEffect(() => {
    if (open) {
      setForm(transaction ? transactionToForm(transaction) : emptyForm())
      setSearchResults([])
      setShowDropdown(false)
    }
  }, [open, transaction])

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSearchResults([])
      setShowDropdown(false)
      return
    }
    setSearching(true)
    try {
      const results = await searchVarieties(q)
      setSearchResults(results)
      setShowDropdown(results.length > 0)
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }, [])

  const updateField = useCallback(
    (key: keyof TransactionFormData, value: string) => {
      setForm((prev) => {
        const next = { ...prev, [key]: value }

        // ticker 变更 → debounce 搜索（编辑模式也允许改）
        if (key === 'ticker') {
          if (debounceRef.current) clearTimeout(debounceRef.current)
          debounceRef.current = setTimeout(() => doSearch(value), 300)
        }

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
    [doSearch],
  )

  /** 选中搜索结果 → 仅填 ticker（交易表单不需要其他品种字段） */
  const handleSelect = useCallback((v: AssetVariety) => {
    setForm((prev) => ({ ...prev, ticker: v.ticker }))
    setShowDropdown(false)
  }, [])

  /** ticker 失焦：延迟关下拉，让点击选项先触发 */
  const handleTickerBlur = useCallback(() => {
    setTimeout(() => setShowDropdown(false), 200)
  }, [])

  const handleSubmit = () => {
    if (!form.ticker.trim()) return
    if (!form.transaction_date) return
    // 后端硬性约束：(quantity + unit_price) 或 amount 至少一组；不在前端硬挡，让后端报错展示在底部
    onSubmit(form)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑交易' : '新增交易'}</DialogTitle>
          <DialogDescription>
            {isEdit ? '修改交易记录' : '录入一笔买入或卖出交易（需先在持仓页建仓）'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {/* 代码 + 搜索下拉 */}
          <div ref={wrapperRef} className="relative">
            <label className="text-xs font-medium text-muted-foreground">代码</label>
            <Input
              placeholder="600519 / AAPL / BTC"
              value={form.ticker}
              onChange={(e) => updateField('ticker', e.target.value.toUpperCase())}
              onBlur={handleTickerBlur}
            />
            {searching && (
              <div className="absolute z-10 mt-1 w-full rounded-md border bg-popover p-2 text-sm text-muted-foreground shadow-md">
                搜索中...
              </div>
            )}
            {showDropdown && searchResults.length > 0 && !searching && (
              <div className="absolute z-10 mt-1 max-h-48 w-full overflow-y-auto rounded-md border bg-popover shadow-md">
                {searchResults.map((v) => (
                  <button
                    key={`${v.ticker}-${v.asset_class}-${v.market}`}
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground"
                    onMouseDown={() => handleSelect(v)}
                  >
                    <span className="font-medium">{v.ticker}</span>
                    <span className="truncate text-muted-foreground">{v.name}</span>
                    <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                      {marketOptionLabel[v.market] || v.market} · {v.asset_class}
                    </span>
                  </button>
                ))}
              </div>
            )}
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
