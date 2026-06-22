import { useState } from 'react'
import { useTransactions } from '@/hooks/useTransactions'
import {
  useCreateTransaction,
  useUpdateTransaction,
  useDeleteTransaction,
} from '@/hooks/useTransactionMutations'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { TransactionFormDialog } from './TransactionFormDialog'
import { Plus, Pencil, Trash2, Archive } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { toNum, formatPrice } from '@/lib/utils'
import type {
  Transaction,
  TransactionCreate,
  TransactionUpdate,
} from '@/types'

const typeLabel: Record<string, string> = {
  buy: '买入',
  sell: '卖出',
}

const marketLabel: Record<string, string> = {
  CN: 'A 股',
  US: '美股',
  CRYPTO: '加密',
}

/** 各市场 Tab：label + 交易条数 */
function marketTabs(transactions: Transaction[]) {
  const counts = { CN: 0, US: 0, CRYPTO: 0 } as Record<string, number>
  for (const t of transactions) {
    counts[t.market] = (counts[t.market] || 0) + 1
  }
  return [
    { key: 'ALL', label: '全部', count: transactions.length },
    { key: 'CN', label: 'A 股', count: counts.CN },
    { key: 'US', label: '美股', count: counts.US },
    { key: 'CRYPTO', label: '加密', count: counts.CRYPTO },
  ]
}

/** 表单字符串 → 用于比较的 number（不用于提交） */
function toNumForCompare(v: string | null | undefined): number | null {
  if (!v || !v.trim()) return null
  const n = parseFloat(v)
  return Number.isNaN(n) ? null : n
}

export function TransactionsPage() {
  const { data: transactions, isLoading, isError, error, refetch } = useTransactions()
  const createMut = useCreateTransaction()
  const updateMut = useUpdateTransaction()
  const deleteMut = useDeleteTransaction()
  const navigate = useNavigate()

  // 市场筛选 Tab
  const [marketFilter, setMarketFilter] = useState<string>('ALL')
  const txnList = transactions ?? []
  const filteredTxns = marketFilter === 'ALL'
    ? txnList
    : txnList.filter((t) => t.market === marketFilter)

  // 对话框状态
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTxn, setEditingTxn] = useState<Transaction | undefined>(undefined)
  const [deleteConfirm, setDeleteConfirm] = useState<Transaction | null>(null)

  function handleCreate() {
    setEditingTxn(undefined)
    createMut.reset()
    setDialogOpen(true)
  }

  function handleEdit(t: Transaction) {
    setEditingTxn(t)
    updateMut.reset()
    setDialogOpen(true)
  }

  function handleDeleteClick(t: Transaction) {
    setDeleteConfirm(t)
  }

  function confirmDelete() {
    if (deleteConfirm) {
      deleteMut.mutate(deleteConfirm.id, {
        onSuccess: () => setDeleteConfirm(null),
      })
    }
  }

  function handleFormSubmit(data: {
    ticker: string
    asset_class: string
    market: string
    transaction_date: string
    type: 'buy' | 'sell'
    quantity: string
    unit_price: string
    amount: string
    notes: string
  }) {
    if (editingTxn) {
      // 仅提交变更字段（与持仓页 update 风格一致）
      const payload: TransactionUpdate = {}
      if (data.ticker !== editingTxn.ticker) payload.ticker = data.ticker
      if (data.asset_class !== editingTxn.asset_class) payload.asset_class = data.asset_class
      if (data.market !== editingTxn.market) payload.market = data.market
      if (data.transaction_date !== editingTxn.transaction_date)
        payload.transaction_date = data.transaction_date
      if (data.type !== editingTxn.type) payload.type = data.type
      if (toNumForCompare(data.quantity) !== editingTxn.quantity) payload.quantity = data.quantity || null
      if (toNumForCompare(data.unit_price) !== editingTxn.unit_price) payload.unit_price = data.unit_price || null
      if (toNumForCompare(data.amount) !== editingTxn.amount) payload.amount = data.amount || null
      const newNotes = data.notes.trim() || null
      if (newNotes !== editingTxn.notes) payload.notes = newNotes

      updateMut.mutate(
        { id: editingTxn.id, data: payload },
        { onSuccess: () => setDialogOpen(false) },
      )
    } else {
      const payload: TransactionCreate = {
        ticker: data.ticker,
        asset_class: data.asset_class,
        market: data.market,
        transaction_date: data.transaction_date,
        type: data.type,
        quantity: data.quantity || null,
        unit_price: data.unit_price || null,
        amount: data.amount || null,
        notes: data.notes.trim() || null,
      }
      createMut.mutate(payload, { onSuccess: () => setDialogOpen(false) })
    }
  }

  const dialogError = editingTxn ? updateMut.error?.message : createMut.error?.message
  const dialogPending = createMut.isPending || updateMut.isPending

  // ---- 加载态 ----
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">交易记录</h1>
          <div className="flex gap-2">
            <Skeleton className="h-9 w-24" />
            <Skeleton className="h-9 w-28" />
          </div>
        </div>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm tabular-nums">
            <thead>
              <tr className="bg-muted/50">
                {['日期', '代码', '市场', '类型', '方向', '数量', '成交价', '金额', '费率', '备注', '操作'].map((h) => (
                  <th key={h} className="text-left p-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, i) => (
                <tr key={i} className="border-t">
                  {[...Array(10)].map((_, j) => (
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
  if (txnList.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">交易记录</h1>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate('/transactions/history')}>
              <Archive className="w-4 h-4 mr-2" />历史记录
            </Button>
            <Button onClick={handleCreate}><Plus className="w-4 h-4 mr-2" />新增交易</Button>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-muted/20 gap-4">
          <p className="text-muted-foreground text-lg">暂无交易记录</p>
          <p className="text-sm text-muted-foreground">先在持仓页建仓，再点「新增交易」录入流水</p>
        </div>
        <TransactionFormDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          onSubmit={handleFormSubmit}
          error={dialogError}
          isPending={dialogPending}
        />
      </div>
    )
  }

  // ---- 正常渲染 ----
  const tabs = marketTabs(txnList)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">交易记录</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/transactions/history')}>
            <Archive className="w-4 h-4 mr-2" />历史记录
          </Button>
          <Button onClick={handleCreate}><Plus className="w-4 h-4 mr-2" />新增交易</Button>
        </div>
      </div>

      {/* 市场筛选 Tab */}
      <div className="flex gap-1 border-b">
        {tabs.map((tab) => (
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
            <span className="text-xs opacity-60">{tab.count} 条</span>
          </button>
        ))}
      </div>

      {deleteConfirm && (
        <div className="flex items-center justify-between rounded-md border border-destructive/50 bg-destructive/10 p-3">
          <p className="text-sm">
            确定删除 <span className="font-medium">{deleteConfirm.ticker}</span> 在{' '}
            <span className="font-medium">{deleteConfirm.transaction_date}</span> 的{' '}
            <span className="font-medium">{typeLabel[deleteConfirm.type] || deleteConfirm.type}</span>{' '}
            交易？删除后该 ticker 持仓会自动重算。
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setDeleteConfirm(null)}>取消</Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={confirmDelete}
              disabled={deleteMut.isPending}
            >
              {deleteMut.isPending ? '删除中...' : '确认删除'}
            </Button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm tabular-nums">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left p-3">日期</th>
              <th className="text-left p-3">代码</th>
              {marketFilter === 'ALL' && <th className="text-left p-3">市场</th>}
              <th className="text-left p-3">类型</th>
              <th className="text-left p-3">方向</th>
              <th className="text-right p-3">数量</th>
              <th className="text-right p-3">成交价</th>
              <th className="text-right p-3">金额</th>
              <th className="text-right p-3">费率</th>
              <th className="text-left p-3">备注</th>
              <th className="p-3 w-20 sticky right-0 bg-muted/50">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredTxns.map((t) => (
              <tr key={t.id} className="border-t hover:bg-muted/30">
                <td className="p-3">{t.transaction_date}</td>
                <td className="p-3 font-medium">{t.ticker}</td>
                {marketFilter === 'ALL' && (
                  <td className="p-3"><Badge variant="outline">{marketLabel[t.market] || t.market}</Badge></td>
                )}
                <td className="p-3 text-muted-foreground">{t.asset_class}</td>
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
                <td className="p-3 text-right">
                  {t.fee_rate != null ? `${t.fee_rate}%` : '-'}
                </td>
                <td className="p-3 text-muted-foreground">{t.notes || '-'}</td>
                <td className="p-3 sticky right-0 bg-background">
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon-sm" onClick={() => handleEdit(t)}>
                      <Pencil className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteClick(t)}>
                      <Trash2 className="w-3.5 h-3.5 text-destructive" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-sm text-muted-foreground">共 {filteredTxns.length} 条记录</p>

      <TransactionFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={handleFormSubmit}
        transaction={editingTxn}
        error={dialogError}
        isPending={dialogPending}
      />
    </div>
  )
}
