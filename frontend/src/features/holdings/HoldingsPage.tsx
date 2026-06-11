import { useState } from 'react'
import { useHoldings } from '@/hooks/useHoldings'
import {
  useCreateHolding,
  useUpdateHolding,
  useDeleteHolding,
} from '@/hooks/useHoldingMutations'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { HoldingFormDialog } from './HoldingFormDialog'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { formatPrice, formatPct } from '@/lib/utils'
import type { HoldingCreate, HoldingUpdate, HoldingWithQuote } from '@/types'

const marketLabel: Record<string, string> = {
  CN: 'A 股/基金',
  US: '美股',
  CRYPTO: '加密货币',
}

function PnlCell({ holding }: { holding: HoldingWithQuote }) {
  const pct = formatPct(holding.pnl_pct)
  if (pct === 'N/A') return <span className="text-muted-foreground">N/A</span>
  const positive = holding.pnl >= 0
  return (
    <span className={`font-medium ${positive ? 'text-green-600' : 'text-red-600'}`}>
      {pct}
    </span>
  )
}

function AnnualizedCell({ holding }: { holding: HoldingWithQuote }) {
  if (holding.annualized_return == null) return <span className="text-muted-foreground">N/A</span>
  const positive = holding.annualized_return >= 0
  return (
    <span className={positive ? 'text-green-600' : 'text-red-600'}>
      {formatPct(holding.annualized_return)}
    </span>
  )
}

export function HoldingsPage() {
  const { data: holdings, isLoading, isError, error, refetch } = useHoldings()
  const createMut = useCreateHolding()
  const updateMut = useUpdateHolding()
  const deleteMut = useDeleteHolding()

  // 对话框状态
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingHolding, setEditingHolding] = useState<HoldingWithQuote | undefined>(undefined)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  function handleCreate() {
    setEditingHolding(undefined)
    setDialogOpen(true)
  }

  function handleEdit(h: HoldingWithQuote) {
    setEditingHolding(h)
    setDialogOpen(true)
  }

  function handleDeleteClick(ticker: string) {
    setDeleteConfirm(ticker)
  }

  function confirmDelete() {
    if (deleteConfirm) {
      deleteMut.mutate(deleteConfirm)
      setDeleteConfirm(null)
    }
  }

  function handleFormSubmit(data: {
    ticker: string; name: string; market: string; asset_class: string
    currency: string; quantity: string; cost_price: string; total_invested: string; first_buy_date: string
  }) {
    if (editingHolding) {
      const toNum = (v: number | string): number => typeof v === 'string' ? parseFloat(v) : v
      const updateData: HoldingUpdate = {}
      if (data.name !== editingHolding.name) updateData.name = data.name
      if (parseFloat(data.quantity) !== toNum(editingHolding.quantity)) updateData.quantity = parseFloat(data.quantity)
      if (parseFloat(data.cost_price) !== toNum(editingHolding.cost_price)) updateData.cost_price = parseFloat(data.cost_price)
      if (parseFloat(data.total_invested) !== toNum(editingHolding.total_invested))
        updateData.total_invested = parseFloat(data.total_invested)
      if (data.first_buy_date !== editingHolding.first_buy_date)
        updateData.first_buy_date = data.first_buy_date
      updateMut.mutate(
        { ticker: editingHolding.ticker, data: updateData },
        { onSuccess: () => setDialogOpen(false) },
      )
    } else {
      const createData: HoldingCreate = {
        ticker: data.ticker, name: data.name, market: data.market,
        asset_class: data.asset_class, currency: data.currency,
        quantity: parseFloat(data.quantity), cost_price: parseFloat(data.cost_price),
        total_invested: parseFloat(data.total_invested), first_buy_date: data.first_buy_date,
      }
      createMut.mutate(createData, { onSuccess: () => setDialogOpen(false) })
    }
  }

  const dialogError = editingHolding ? updateMut.error?.message : createMut.error?.message

  // ---- 加载态 ----
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">持仓</h1>
          <Skeleton className="h-9 w-28" />
        </div>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                {['代码','名称','市场','持仓量','成本价','现价','市值','盈亏','年化回报','操作'].map((h) => (
                  <th key={h} className={`text-${h==='操作'?'center':'left'} p-3`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, i) => (
                <tr key={i} className="border-t">
                  {[...Array(10)].map((_, j) => (
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
        <h1 className="text-2xl font-bold">持仓</h1>
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <p className="text-destructive font-medium">加载失败</p>
          <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : '未知错误'}</p>
          <Button variant="outline" onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    )
  }

  // ---- 空持仓 ----
  if (!holdings || holdings.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">持仓</h1>
          <Button onClick={handleCreate}><Plus className="w-4 h-4 mr-2" />新增持仓</Button>
        </div>
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-muted/20 gap-4">
          <p className="text-muted-foreground text-lg">暂无持仓</p>
          <p className="text-sm text-muted-foreground">点击「新增持仓」添加第一个品种</p>
        </div>
        <HoldingFormDialog open={dialogOpen} onOpenChange={setDialogOpen} onSubmit={handleFormSubmit} error={dialogError} isPending={createMut.isPending} />
      </div>
    )
  }

  // ---- 正常渲染 ----
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">持仓</h1>
        <Button onClick={handleCreate}><Plus className="w-4 h-4 mr-2" />新增持仓</Button>
      </div>

      {deleteConfirm && (
        <div className="flex items-center justify-between rounded-md border border-destructive/50 bg-destructive/10 p-3">
          <p className="text-sm">确定删除 <span className="font-medium">{deleteConfirm}</span> 的持仓记录？此操作不可撤销。</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setDeleteConfirm(null)}>取消</Button>
            <Button variant="destructive" size="sm" onClick={confirmDelete} disabled={deleteMut.isPending}>
              {deleteMut.isPending ? '删除中...' : '确认删除'}
            </Button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left p-3">代码</th>
              <th className="text-left p-3">名称</th>
              <th className="text-left p-3">市场</th>
              <th className="text-right p-3">持仓量</th>
              <th className="text-right p-3">成本价</th>
              <th className="text-right p-3">现价</th>
              <th className="text-right p-3">市值</th>
              <th className="text-right p-3">盈亏</th>
              <th className="text-right p-3">年化回报</th>
              <th className="p-3 w-20">操作</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.ticker} className="border-t hover:bg-muted/30">
                <td className="p-3 font-medium">{h.ticker}</td>
                <td className="p-3">{h.name}</td>
                <td className="p-3"><Badge variant="outline">{marketLabel[h.market] || h.market}</Badge></td>
                <td className="p-3 text-right">{h.quantity.toLocaleString()}</td>
                <td className="p-3 text-right">{formatPrice(h.cost_price, h.currency)}</td>
                <td className="p-3 text-right">{formatPrice(h.current_price, h.currency)}</td>
                <td className="p-3 text-right">{formatPrice(h.market_value, h.currency)}</td>
                <td className="p-3 text-right"><PnlCell holding={h} /></td>
                <td className="p-3 text-right"><AnnualizedCell holding={h} /></td>
                <td className="p-3">
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon-sm" onClick={() => handleEdit(h)}><Pencil className="w-3.5 h-3.5" /></Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteClick(h.ticker)}><Trash2 className="w-3.5 h-3.5 text-destructive" /></Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-sm text-muted-foreground">共 {holdings.length} 个品种</p>

      <HoldingFormDialog
        open={dialogOpen} onOpenChange={setDialogOpen} onSubmit={handleFormSubmit}
        holding={editingHolding} error={dialogError} isPending={createMut.isPending || updateMut.isPending}
      />
    </div>
  )
}
