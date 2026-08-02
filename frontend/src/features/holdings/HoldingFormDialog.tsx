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
import type { AssetVariety, HoldingWithQuote } from '@/types'

interface HoldingFormData {
  ticker: string
  name: string
  market: string
  asset_class: string
  currency: string
  quantity: string
  cost_price: string
  total_invested: string
  first_buy_date: string
  cash_account_enabled: boolean
}

function emptyForm(): HoldingFormData {
  return {
    ticker: '',
    name: '',
    market: 'CN',
    asset_class: 'STOCK',
    currency: 'CNY',
    quantity: '',
    cost_price: '',
    total_invested: '',
    first_buy_date: new Date().toISOString().slice(0, 10),
    cash_account_enabled: true,
  }
}

function holdingToForm(h: HoldingWithQuote): HoldingFormData {
  return {
    ticker: h.ticker,
    name: h.name,
    market: h.market,
    asset_class: h.asset_class,
    currency: h.currency,
    quantity: String(Number(h.quantity)),
    cost_price: String(Number(h.cost_price)),
    total_invested: String(Number(h.total_invested)),
    first_buy_date: h.first_buy_date,
    cash_account_enabled: false, // 编辑时不可改，值无意义
  }
}

/** 选中搜索结果时填充表单 */
function applyVariety(form: HoldingFormData, v: AssetVariety): HoldingFormData {
  return {
    ...form,
    ticker: v.ticker,
    name: v.name,
    market: v.market,
    asset_class: v.asset_class,
    currency: v.currency,
  }
}

const marketOptionLabel: Record<string, string> = {
  CN: 'A 股',
  US: '美股',
  CRYPTO: '加密货币',
}

interface HoldingFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: HoldingFormData) => void
  /** 编辑模式：传入已有持仓数据 */
  holding?: HoldingWithQuote
  /** 后端返回的错误信息 */
  error?: string | null
  /** 是否正在提交 */
  isPending?: boolean
}

export function HoldingFormDialog({
  open,
  onOpenChange,
  onSubmit,
  holding,
  error,
  isPending,
}: HoldingFormDialogProps) {
  const isEdit = !!holding
  const [form, setForm] = useState<HoldingFormData>(emptyForm())
  const [errors, setErrors] = useState<Record<string, string>>({})

  // ---- 品种搜索下拉 ----
  const [searchResults, setSearchResults] = useState<AssetVariety[]>([])
  const [searching, setSearching] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
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

  // 对话框打开时重置表单 + 清空错误
  // （渲染期调整状态，React 官方推荐模式，避免在 effect 里同步 setState）
  const [prevOpen, setPrevOpen] = useState(open)
  if (open !== prevOpen) {
    setPrevOpen(open)
    if (open) {
      setForm(holding ? holdingToForm(holding) : emptyForm())
      setSearchResults([])
      setShowDropdown(false)
      setErrors({})
    }
  }

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
    (key: keyof HoldingFormData, value: string) => {
      setForm((prev) => {
        const next = { ...prev, [key]: value }

        // ticker 变更 → debounce 搜索品种
        if (key === 'ticker' && !isEdit) {
          if (debounceRef.current) clearTimeout(debounceRef.current)
          debounceRef.current = setTimeout(() => doSearch(value), 300)
        }

        // 市场 → 货币 联动
        if (key === 'market') {
          next.currency = value === 'CN' ? 'CNY' : 'USD'
        }

        // 三字段联动：输入任意两个，自动算出第三个
        const qty = parseFloat(next.quantity)
        const price = parseFloat(next.cost_price)
        const total = parseFloat(next.total_invested)
        if (key === 'quantity' || key === 'cost_price') {
          // qty × price → total
          if (!isNaN(qty) && !isNaN(price)) {
            next.total_invested = String(qty * price)
          }
        } else if (key === 'total_invested') {
          // total ÷ price → qty（优先算数量）
          if (!isNaN(total) && !isNaN(price) && price !== 0) {
            next.quantity = String(total / price)
          } else if (!isNaN(total) && !isNaN(qty) && qty !== 0) {
            // total ÷ qty → price
            next.cost_price = String(total / qty)
          }
        }

        return next
      })
      // 三字段联动时清掉被自动填充字段的错误
      setErrors((prev) => {
        const errs = { ...prev }
        const changed = new Set<string>([key])
        if (key === 'quantity' || key === 'cost_price') changed.add('total_invested')
        else if (key === 'total_invested') {
          const c = parseFloat(form.cost_price)
          const q = parseFloat(form.quantity)
          const v = parseFloat(value)
          if (!isNaN(v) && !isNaN(c) && c !== 0) changed.add('quantity')
          else if (!isNaN(v) && !isNaN(q) && q !== 0) changed.add('cost_price')
        }
        let dirty = false
        for (const k of changed) {
          if (errs[k]) { delete errs[k]; dirty = true }
        }
        return dirty ? errs : prev
      })
    },
    // 错误联动逻辑读取当前表单的成本价/数量，须纳入依赖
    [isEdit, doSearch, form.cost_price, form.quantity],
  )

  /** 选中搜索结果 */
  const handleSelect = useCallback((v: AssetVariety) => {
    setForm((prev) => applyVariety(prev, v))
    setShowDropdown(false)
    // 选中品种后清掉 ticker 错误
    setErrors((prev) => {
      if (!prev.ticker) return prev
      const next = { ...prev }
      delete next.ticker
      return next
    })
  }, [])

  /** ticker 失焦时：如果 name 为空，尝试精确匹配补填 */
  const handleTickerBlur = useCallback(() => {
    // 延迟关闭下拉，让点击选项先触发
    setTimeout(() => {
      setShowDropdown(false)
    }, 200)

    setForm((prev) => {
      if (prev.name || !prev.ticker.trim()) return prev

      // 搜索结果中精确匹配
      if (searchResults.length > 0) {
        const exact = searchResults.find(
          (r) => r.ticker.toUpperCase() === prev.ticker.toUpperCase(),
        )
        if (exact) return applyVariety(prev, exact)
      }
      return prev
    })
  }, [searchResults])

  /** 必填校验：返回错误 map（空表示通过） */
  function validate(): Record<string, string> {
    const e: Record<string, string> = {}
    if (!form.ticker.trim()) e.ticker = '请输入或搜索代码'
    const qty = parseFloat(form.quantity)
    if (!form.quantity || isNaN(qty) || qty <= 0) e.quantity = '持仓量必须大于 0'
    const cost = parseFloat(form.cost_price)
    if (!form.cost_price || isNaN(cost) || cost <= 0) e.cost_price = '成本价必须大于 0'
    const total = parseFloat(form.total_invested)
    if (!form.total_invested || isNaN(total) || total <= 0) e.total_invested = '总投入必须大于 0'
    if (!form.first_buy_date) e.first_buy_date = '请选择首次买入日期'
    return e
  }

  const handleSubmit = () => {
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length > 0) return
    onSubmit(form)
  }

  /** label 在有错误时变红 */
  const labelClass = (key: string) =>
    `text-xs font-medium ${errors[key] ? 'text-destructive' : 'text-muted-foreground'}`

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!isPending) onOpenChange(next) }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑持仓' : '新增持仓'}</DialogTitle>
          <DialogDescription>
            {isEdit ? '修改持仓信息' : '添加新的持仓品种'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {/* 代码 + 搜索下拉 */}
          <div ref={wrapperRef} className="relative">
            <label className={labelClass('ticker')}>代码</label>
            <Input
              placeholder="600519 / AAPL / BTC"
              value={form.ticker}
              onChange={(e) => updateField('ticker', e.target.value.toUpperCase())}
              onBlur={handleTickerBlur}
              disabled={isEdit}
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
            {errors.ticker && <p className="mt-1 text-xs text-destructive">{errors.ticker}</p>}
          </div>

          {/* 名称 */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">名称</label>
            <Input
              placeholder="贵州茅台"
              value={form.name}
              disabled
            />
          </div>

          {/* 市场 + 类别 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">市场</label>
              <Select
                value={form.market}
                onValueChange={(v) => updateField('market', v ?? '')}
                disabled={isEdit}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CN">A 股</SelectItem>
                  <SelectItem value="US">美股</SelectItem>
                  <SelectItem value="CRYPTO">加密货币</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">类别</label>
              <Select
                value={form.asset_class}
                onValueChange={(v) => updateField('asset_class', v ?? '')}
                disabled={isEdit}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="STOCK">股票</SelectItem>
                  <SelectItem value="FUND">基金</SelectItem>
                  <SelectItem value="CRYPTO">加密货币</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* 数量 + 成本价 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass('quantity')}>持仓量</label>
              <Input
                type="number"
                step="any"
                placeholder="100"
                value={form.quantity}
                onChange={(e) => updateField('quantity', e.target.value)}
              />
              {errors.quantity && <p className="mt-1 text-xs text-destructive">{errors.quantity}</p>}
            </div>
            <div>
              <label className={labelClass('cost_price')}>成本价</label>
              <Input
                type="number"
                step="any"
                placeholder="150.00"
                value={form.cost_price}
                onChange={(e) => updateField('cost_price', e.target.value)}
              />
              {errors.cost_price && <p className="mt-1 text-xs text-destructive">{errors.cost_price}</p>}
            </div>
          </div>

          {/* 总投入（自动计算，可手动改） */}
          <div>
            <label className={labelClass('total_invested')}>
              总投入
            </label>
            <Input
              type="number"
              step="any"
              value={form.total_invested}
              onChange={(e) => updateField('total_invested', e.target.value)}
              placeholder="自动计算: quantity × cost_price"
            />
            {errors.total_invested && <p className="mt-1 text-xs text-destructive">{errors.total_invested}</p>}
          </div>

          {/* 首次买入日期 */}
          <div>
            <label className={labelClass('first_buy_date')}>首次买入日期</label>
            <Input
              type="date"
              value={form.first_buy_date}
              onChange={(e) => updateField('first_buy_date', e.target.value)}
              disabled={isEdit}
            />
            {errors.first_buy_date && <p className="mt-1 text-xs text-destructive">{errors.first_buy_date}</p>}
          </div>

          {/* 货币（自动联动，只读） */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">货币（自动）</label>
            <Input value={form.currency} disabled />
          </div>

          {/* 现金账户选项（仅新建） */}
          {!isEdit && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="cash_account_enabled"
                className="w-4 h-4 rounded border-gray-300"
                checked={form.cash_account_enabled}
                onChange={(e) => setForm((prev) => ({ ...prev, cash_account_enabled: e.target.checked }))}
              />
              <label htmlFor="cash_account_enabled" className="text-sm cursor-pointer select-none">
                从现金账户扣除（建仓后不可更改）
              </label>
            </div>
          )}

          {/* 后端错误 */}
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
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
