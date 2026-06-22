import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useHoldings } from '@/hooks/useHoldings'
import {
  useCreateHolding,
  useUpdateHolding,
} from '@/hooks/useHoldingMutations'
import { useCreateTransaction } from '@/hooks/useTransactionMutations'
import { fetchHoldingsWithQuotes } from '@/api/endpoints'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { HoldingFormDialog } from './HoldingFormDialog'
import { HoldingDetailDialog } from './HoldingDetailDialog'
import { TransactionFormDialog } from '@/features/transactions/TransactionFormDialog'
import { Plus, Pencil, Eye, HandCoins, Archive, RefreshCw } from 'lucide-react'
import { Tooltip } from '@/components/ui/tooltip'
import { useNavigate } from 'react-router-dom'
import { formatPrice, formatPct } from '@/lib/utils'
import { useColors } from '@/lib/settings'
import type { HoldingCreate, HoldingUpdate, HoldingWithQuote, TransactionCreate } from '@/types'

const marketLabel: Record<string, string> = {
  CN: 'A 股',
  US: '美股',
  CRYPTO: '加密',
}

// 市场固定展示顺序：A 股 → 美股 → 加密货币
const marketOrder: Record<string, number> = { CN: 0, US: 1, CRYPTO: 2 }
// 品种展示顺序：股票 → 基金（同市场内股票在前）
const assetClassOrder: Record<string, number> = { STOCK: 0, FUND: 1 }

/** 把 string|number 安全转 number（用于来自后端的 Decimal 字段） */
function toNum(v: number | string): number {
  return typeof v === 'string' ? parseFloat(v) : v
}

/** 排序：市场（A 股→美股→加密）→ 品种（股票→基金）→ 市值降序 */
function sortByMarketThenValue(holdings: HoldingWithQuote[]): HoldingWithQuote[] {
  return [...holdings].sort((a, b) => {
    const mo = (marketOrder[a.market] ?? 99) - (marketOrder[b.market] ?? 99)
    if (mo !== 0) return mo
    const ac = (assetClassOrder[a.asset_class] ?? 99) - (assetClassOrder[b.asset_class] ?? 99)
    if (ac !== 0) return ac
    return toNum(b.market_value) - toNum(a.market_value)
  })
}

function PnlPctCell({ holding }: { holding: HoldingWithQuote }) {
  const { upColor, downColor } = useColors()
  const pct = formatPct(holding.pnl_pct)
  if (pct === 'N/A') return <span className="text-muted-foreground">N/A</span>
  const positive = holding.pnl >= 0
  return (
    <span className={`font-medium ${positive ? upColor : downColor}`}>
      {pct}
    </span>
  )
}

function PnlAmountCell({ holding }: { holding: HoldingWithQuote }) {
  const { upColor, downColor } = useColors()
  if (holding.pnl == null) return <span className="text-muted-foreground">N/A</span>
  const positive = toNum(holding.pnl) >= 0
  return (
    <span className={`font-medium ${positive ? upColor : downColor}`}>
      {formatPrice(holding.pnl, holding.currency, 2)}
    </span>
  )
}

/** 行情数值 + 状态标记 — HISTORICAL 时追加小字"历史"，UNAVAILABLE 时显示"—" */
function QuoteValueCell({
  value,
  currency,
  status,
}: {
  value: number
  currency: string
  status: string
}) {
  if (status === 'UNAVAILABLE') {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <span className="inline-flex items-center gap-1">
      {formatPrice(value, currency, 2)}
      {status === 'HISTORICAL' && (
        <span className="text-xs text-muted-foreground opacity-50">历史</span>
      )}
    </span>
  )
}

export function HoldingsPage() {
  const { data, isLoading, isError, error, refetch } = useHoldings()
  const holdings = data?.holdings
  const marketSummary = data?.market_summary ?? []
  const createMut = useCreateHolding()
  const updateMut = useUpdateHolding()
  const createTxnMut = useCreateTransaction()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // 手动刷新：force_refresh=true 绕过基金 15 分钟缓存，强制拉最新行情后写回缓存
  const refreshMut = useMutation({
    mutationFn: () => fetchHoldingsWithQuotes(true),
    onSuccess: (data) => {
      queryClient.setQueryData(['holdings', 'with-quotes'], data)
      queryClient.invalidateQueries({ queryKey: ['overview'] })
      toast.success('行情已刷新')
    },
    onError: (e: unknown) => toast.error('刷新失败', {
      description: e instanceof Error ? e.message : '未知错误',
    }),
  })

  // 持仓增改对话框
  const [dialogOpen, setDialogOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailHolding, setDetailHolding] = useState<HoldingWithQuote | null>(null)
  const [editingHolding, setEditingHolding] = useState<HoldingWithQuote | undefined>(undefined)

  // 市场筛选 Tab：ALL / CN / US / CRYPTO
  const [marketFilter, setMarketFilter] = useState<string>('ALL')
  const allHoldings = holdings ?? []
  const filteredHoldings = marketFilter === 'ALL'
    ? allHoldings
    : allHoldings.filter((h) => h.market === marketFilter)
  // 主表"清仓"对话框 — 复用 TransactionFormDialog，传入预填数据
  const [liquidating, setLiquidating] = useState<HoldingWithQuote | null>(null)

  function handleCreate() {
    setEditingHolding(undefined)
    setDialogOpen(true)
  }

  function handleView(h: HoldingWithQuote) {
    setDetailHolding(h)
    setDetailOpen(true)
  }

  function handleEdit(h: HoldingWithQuote) {
    setEditingHolding(h)
    setDialogOpen(true)
  }

  function handleLiquidateClick(h: HoldingWithQuote) {
    createTxnMut.reset()
    setLiquidating(h)
  }

  function handleLiquidateSubmit(data: {
    ticker: string; asset_class: string; market: string
    transaction_date: string; type: 'buy' | 'sell'
    quantity: string; unit_price: string; amount: string; notes: string
  }) {
    const toNumOrNull = (v: string) => {
      if (!v.trim()) return null
      const n = parseFloat(v)
      return Number.isNaN(n) ? null : n
    }
    const payload: TransactionCreate = {
      ticker: data.ticker,
      asset_class: data.asset_class,
      market: data.market,
      transaction_date: data.transaction_date,
      type: data.type,
      quantity: toNumOrNull(data.quantity),
      unit_price: toNumOrNull(data.unit_price),
      amount: toNumOrNull(data.amount),
      notes: data.notes.trim() || null,
    }
    createTxnMut.mutate(payload, {
      onSuccess: () => setLiquidating(null),
    })
  }

  function handleFormSubmit(data: {
    ticker: string; name: string; market: string; asset_class: string
    currency: string; quantity: string; cost_price: string; total_invested: string; first_buy_date: string
  }) {
    if (editingHolding) {
      const updateData: HoldingUpdate = {}
      if (data.name !== editingHolding.name) updateData.name = data.name
      if (parseFloat(data.quantity) !== toNum(editingHolding.quantity)) updateData.quantity = data.quantity
      if (parseFloat(data.cost_price) !== toNum(editingHolding.cost_price)) updateData.cost_price = data.cost_price
      if (parseFloat(data.total_invested) !== toNum(editingHolding.total_invested))
        updateData.total_invested = data.total_invested
      if (data.first_buy_date !== editingHolding.first_buy_date)
        updateData.first_buy_date = data.first_buy_date
      updateMut.mutate(
        {
          ticker: editingHolding.ticker,
          asset_class: editingHolding.asset_class,
          market: editingHolding.market,
          data: updateData,
        },
        { onSuccess: () => setDialogOpen(false) },
      )
    } else {
      const createData: HoldingCreate = {
        ticker: data.ticker, name: data.name, market: data.market,
        asset_class: data.asset_class, currency: data.currency,
        quantity: data.quantity, cost_price: data.cost_price,
        total_invested: data.total_invested, first_buy_date: data.first_buy_date,
      }
      createMut.mutate(createData, { onSuccess: () => setDialogOpen(false) })
    }
  }

  const dialogError = editingHolding ? updateMut.error?.message : createMut.error?.message

  // 清仓对话框预填：ticker / type=sell / 全量数量 / 现价 / 自动算金额
  const liquidatePreset = liquidating
    ? {
        ticker: liquidating.ticker,
        asset_class: liquidating.asset_class,
        market: liquidating.market,
        type: 'sell' as const,
        transaction_date: new Date().toISOString().slice(0, 10),
        quantity: String(toNum(liquidating.quantity)),
        unit_price: String(toNum(liquidating.current_price)),
        amount: String(toNum(liquidating.quantity) * toNum(liquidating.current_price)),
        fee_rate: '',
        notes: '',
      }
    : undefined

  // ---- 加载态 ----
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">持仓</h1>
          <Skeleton className="h-9 w-28" />
        </div>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm [font-variant-numeric:tabular-nums]">
            <thead>
              <tr className="bg-muted">
                {['代码','名称','市场','类型','市值','持仓量','成本价','现价','盈亏金额','盈亏率','持仓天数','操作'].map((h) => (
                  <th key={h} className={`text-${h==='操作'?'center':'left'} p-3 whitespace-nowrap`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, i) => (
                <tr key={i} className="border-t">
                  {[...Array(12)].map((_, j) => (
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
  if (allHoldings.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">持仓</h1>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate('/holdings/history')}>
              <Archive className="w-4 h-4 mr-2" />历史持仓
            </Button>
            <Button onClick={handleCreate}><Plus className="w-4 h-4 mr-2" />新增持仓</Button>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-muted/20 gap-4">
          <p className="text-muted-foreground text-lg">暂无持仓</p>
          <p className="text-sm text-muted-foreground">点击「新增持仓」添加第一个品种；已清仓品种见上方「历史持仓」</p>
        </div>
        <HoldingFormDialog open={dialogOpen} onOpenChange={setDialogOpen} onSubmit={handleFormSubmit} error={dialogError} isPending={createMut.isPending} />
        <HoldingDetailDialog open={detailOpen} onOpenChange={setDetailOpen} holding={detailHolding} />
      </div>
    )
  }

  // ---- 正常渲染 ----
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">持仓</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => refreshMut.mutate()}
            disabled={refreshMut.isPending}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshMut.isPending ? 'animate-spin' : ''}`} />
            {refreshMut.isPending ? '刷新中...' : '刷新'}
          </Button>
          <Button variant="outline" onClick={() => navigate('/holdings/history')}>
            <Archive className="w-4 h-4 mr-2" />历史持仓
          </Button>
          <Button onClick={handleCreate}><Plus className="w-4 h-4 mr-2" />新增持仓</Button>
        </div>
      </div>

      {/* 市场筛选 Tab（标注各市场市值占比） */}
      <div className="flex gap-1 border-b">
        {([
          { key: 'ALL', label: '全部' },
          { key: 'CN', label: 'A 股' },
          { key: 'US', label: '美股' },
          { key: 'CRYPTO', label: '加密' },
        ] as const).map((tab) => {
          // 各市场 Tab 标注市值占比；全部 Tab 不显示占比
          const summary = marketSummary.find((m) => m.market === tab.key)
          const pctText = tab.key === 'ALL' || !summary ? '' : `${summary.pct.toFixed(1)}%`
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setMarketFilter(tab.key)}
              className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors flex items-baseline gap-1.5 ${
                marketFilter === tab.key
                  ? 'border-primary text-foreground font-medium'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
              {pctText && <span className="text-xs opacity-60">{pctText}</span>}
            </button>
          )
        })}
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm tabular-nums">
          <thead>
            <tr className="bg-muted">
              <th className="text-left p-3 whitespace-nowrap">代码</th>
              <th className="text-left p-3">名称</th>
              {marketFilter === 'ALL' && <th className="text-left p-3 whitespace-nowrap">市场</th>}
              <th className="text-left p-3 whitespace-nowrap">类型</th>
              <th className="text-right p-3 whitespace-nowrap">市值</th>
              <th className="text-right p-3 whitespace-nowrap">持仓量</th>
              <th className="text-right p-3 whitespace-nowrap">成本价</th>
              <th className="text-right p-3 whitespace-nowrap">现价</th>
              <th className="text-right p-3 whitespace-nowrap">盈亏金额</th>
              <th className="text-right p-3 whitespace-nowrap">盈亏率</th>
              <th className="text-right p-3 whitespace-nowrap">持仓天数</th>
              <th className="p-3 w-24 whitespace-nowrap sticky right-0 bg-muted">操作</th>
            </tr>
          </thead>
          <tbody>
            {sortByMarketThenValue(filteredHoldings).map((h) =>
              <tr key={h.ticker} className="border-t hover:bg-muted/30">
                <td className="p-3 font-medium whitespace-nowrap">{h.ticker}</td>
                <td className="p-3">
                  <Tooltip content={h.name}>
                    <span className="block max-w-40 truncate">{h.name}</span>
                  </Tooltip>
                </td>
                {marketFilter === 'ALL' && (
                  <td className="p-3 whitespace-nowrap"><Badge variant="outline">{marketLabel[h.market] || h.market}</Badge></td>
                )}
	                <td className="p-3 text-muted-foreground whitespace-nowrap">{h.asset_class}</td>
                <td className="p-3 text-right whitespace-nowrap"><QuoteValueCell value={toNum(h.market_value)} currency={h.currency} status={h.quote_status} /></td>
                <td className="p-3 text-right whitespace-nowrap">{toNum(h.quantity).toString()}</td>
                <td className="p-3 text-right whitespace-nowrap">{formatPrice(h.cost_price, h.currency)}</td>
                <td className="p-3 text-right whitespace-nowrap"><QuoteValueCell value={toNum(h.current_price)} currency={h.currency} status={h.quote_status} /></td>
                <td className="p-3 text-right whitespace-nowrap"><PnlAmountCell holding={h} /></td>
                <td className="p-3 text-right whitespace-nowrap"><PnlPctCell holding={h} /></td>
                <td className="p-3 text-right">{Math.floor((Date.now() - new Date(h.first_buy_date).getTime()) / 86400000) + 1}天</td>
                <td className="p-3 sticky right-0 bg-background">
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon-sm" onClick={() => handleView(h)}>
                      <Eye className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => handleEdit(h)}>
                      <Pencil className="w-3.5 h-3.5" />
                    </Button>
                    <Tooltip content="清仓（以现价全部卖出，自动归档到历史持仓）">
                      <Button variant="ghost" size="icon-sm" onClick={() => handleLiquidateClick(h)}>
                        <HandCoins className="w-3.5 h-3.5 text-orange-600" />
                      </Button>
                    </Tooltip>
                  </div>
                </td>
              </tr>
            )}
            {filteredHoldings.length === 0 && (
              <tr>
                <td colSpan={marketFilter === 'ALL' ? 12 : 11} className="p-8 text-center text-muted-foreground">
                  该市场暂无持仓
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="text-sm text-muted-foreground">共 {filteredHoldings.length} 个品种</p>

      <HoldingFormDialog
        open={dialogOpen} onOpenChange={setDialogOpen} onSubmit={handleFormSubmit}
        holding={editingHolding} error={dialogError} isPending={createMut.isPending || updateMut.isPending}
      />
      <HoldingDetailDialog
        open={detailOpen} onOpenChange={setDetailOpen}
        holding={detailHolding}
      />

      {/* 清仓对话框 — 复用交易表单 */}
      <TransactionFormDialog
        open={liquidating !== null}
        onOpenChange={(open) => !open && setLiquidating(null)}
        onSubmit={handleLiquidateSubmit}
        presetData={liquidatePreset}
        error={createTxnMut.error?.message}
        isPending={createTxnMut.isPending}
      />
    </div>
  )
}
