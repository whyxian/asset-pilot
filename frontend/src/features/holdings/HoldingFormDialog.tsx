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
import type { HoldingWithQuote } from '@/types'

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
  }
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

  // 当对话框打开/关闭时重置表单
  useEffect(() => {
    if (open) {
      setForm(holding ? holdingToForm(holding) : emptyForm())
    }
  }, [open, holding])

  const updateField = useCallback(
    (key: keyof HoldingFormData, value: string) => {
      setForm((prev) => {
        const next = { ...prev, [key]: value }

        // 市场 → 货币 自动联动
        if (key === 'market') {
          next.currency = value === 'CN' ? 'CNY' : 'USD'
        }

        // quantity × cost_price → total_invested 自动计算
        if (key === 'quantity' || key === 'cost_price') {
          const qty = parseFloat(key === 'quantity' ? value : prev.quantity)
          const price = parseFloat(key === 'cost_price' ? value : prev.cost_price)
          if (!isNaN(qty) && !isNaN(price)) {
            next.total_invested = String(qty * price)
          }
        }

        return next
      })
    },
    [],
  )

  const handleSubmit = () => {
    // 基本校验
    if (!form.ticker.trim()) return
    if (!form.quantity || parseFloat(form.quantity) <= 0) return
    onSubmit(form)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑持仓' : '新增持仓'}</DialogTitle>
          <DialogDescription>
            {isEdit ? '修改持仓信息' : '添加新的持仓品种'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {/* 代码 */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">代码</label>
            <Input
              placeholder="600519 / AAPL"
              value={form.ticker}
              onChange={(e) => updateField('ticker', e.target.value.toUpperCase())}
              disabled={isEdit}
            />
          </div>

          {/* 名称 */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">名称</label>
            <Input
              placeholder="贵州茅台"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
            />
          </div>

          {/* 市场 + 类别 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">市场</label>
              <Select
                value={form.market}
                onValueChange={(v) => updateField('market', v)}
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
                onValueChange={(v) => updateField('asset_class', v)}
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
              <label className="text-xs font-medium text-muted-foreground">持仓量</label>
              <Input
                type="number"
                step="any"
                placeholder="100"
                value={form.quantity}
                onChange={(e) => updateField('quantity', e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">成本价</label>
              <Input
                type="number"
                step="any"
                placeholder="150.00"
                value={form.cost_price}
                onChange={(e) => updateField('cost_price', e.target.value)}
              />
            </div>
          </div>

          {/* 总投入（自动计算，只读） */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">
              总投入（自动计算）
            </label>
            <Input
              type="number"
              step="any"
              value={form.total_invested}
              onChange={(e) => updateField('total_invested', e.target.value)}
              placeholder="quantity × cost_price"
            />
          </div>

          {/* 首次买入日期 */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">首次买入日期</label>
            <Input
              type="date"
              value={form.first_buy_date}
              onChange={(e) => updateField('first_buy_date', e.target.value)}
            />
          </div>

          {/* 货币（自动联动，只读） */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">货币（自动）</label>
            <Input value={form.currency} disabled />
          </div>

          {/* 后端错误 */}
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
