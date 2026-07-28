import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClosedHoldings, useDeleteClosedHolding } from '@/hooks/useClosedHoldings'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ClosedHoldingDetailDialog } from './ClosedHoldingDetailDialog'
import { Eye, ArrowLeft, Trash2 } from 'lucide-react'
import { Tooltip } from '@/components/ui/tooltip'
import { formatPrice, formatPct } from '@/lib/utils'
import { useColors } from '@/lib/settings'
import { Pagination } from '@/components/ui/pagination'
import type { ClosedHolding } from '@/types'

const marketLabel: Record<string, string> = {
  CN: 'A 股',
  US: '美股',
  CRYPTO: '加密货币',
}

function toNum(v: number | string): number {
  return typeof v === 'string' ? parseFloat(v) : v
}

/** 公共头部：返回按钮 + 标题 */
function PageHeader() {
  const navigate = useNavigate()
  return (
    <div className="flex items-center gap-3">
      <Button variant="ghost" size="icon-sm" onClick={() => navigate('/holdings')}>
        <ArrowLeft className="w-4 h-4" />
      </Button>
      <h1 className="text-2xl font-bold">历史持仓</h1>
    </div>
  )
}

export function HistoryPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const { data: pageData, isLoading, isError, error, refetch } = useClosedHoldings(page, pageSize)
  const data = pageData?.data ?? []
  const total = pageData?.total ?? 0
  const deleteMut = useDeleteClosedHolding()
  const [detailId, setDetailId] = useState<number | null>(null)
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])
  const { upColor, downColor } = useColors()
  const [deleteConfirm, setDeleteConfirm] = useState<ClosedHolding | null>(null)

  function handlePageSizeChange(size: number) {
    setPageSize(size)
    setPage(1)
  }

  function handleDeleteClick(h: ClosedHolding) {
    setDeleteConfirm(h)
  }

  function confirmDelete() {
    if (deleteConfirm) {
      deleteMut.mutate(deleteConfirm.id, {
        onSuccess: () => setDeleteConfirm(null),
      })
    }
  }

  // ---- 加载态 ----
  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader />
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm tabular-nums">
            <thead>
              <tr className="bg-muted/50">
                {['代码', '名称', '市场', '类型', '首买日', '清仓日', '持仓天数', '总买入', '已实现盈亏', '盈亏率', '操作'].map((h) => (
                  <th key={h} className="text-left p-3 whitespace-nowrap">{h}</th>
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
        <PageHeader />
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <p className="text-destructive font-medium">加载失败</p>
          <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : '未知错误'}</p>
          <Button variant="outline" onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    )
  }

  // ---- 空态 ----
  if (total === 0 && !isLoading) {
    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-3 duration-500">
        <PageHeader />
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-muted/20 gap-4">
          <p className="text-muted-foreground text-lg">暂无历史持仓</p>
          <p className="text-sm text-muted-foreground">完成一笔从建仓到清仓的完整周期后将在此显示</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className={`transition-all duration-500 ease-out ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <PageHeader />
      </div>

      <div className={`transition-all duration-500 ease-out delay-50 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        {deleteConfirm && (
          <div className="flex items-center justify-between rounded-md border border-destructive/50 bg-destructive/10 p-3">
            <p className="text-sm">
              确定删除 <span className="font-medium">{deleteConfirm.ticker}</span>（{deleteConfirm.name}）的历史持仓记录？关联的归档交易也会一并删除。
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
      </div>

      <div className={`transition-all duration-500 ease-out delay-100 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm tabular-nums">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left p-3 whitespace-nowrap">代码</th>
              <th className="text-left p-3">名称</th>
              <th className="text-left p-3 whitespace-nowrap">市场</th>
              <th className="text-left p-3 whitespace-nowrap">类型</th>
              <th className="text-left p-3 whitespace-nowrap">首买日</th>
              <th className="text-left p-3 whitespace-nowrap">清仓日</th>
              <th className="text-right p-3 whitespace-nowrap">持仓天数</th>
              <th className="text-right p-3 whitespace-nowrap">总买入</th>
              <th className="text-right p-3 whitespace-nowrap">已实现盈亏</th>
              <th className="text-right p-3 whitespace-nowrap">盈亏率</th>
              <th className="p-3 w-20 whitespace-nowrap">操作</th>
            </tr>
          </thead>
          <tbody>
            {data.map((h) => {
              const pct = h.pnl_pct
              const positive = toNum(h.realized_pnl) >= 0
              return (
                <tr key={h.id} className="border-t hover:bg-muted/30">
                  <td className="p-3 font-medium whitespace-nowrap">{h.ticker}</td>
                  <td className="p-3">
                    <Tooltip content={h.name}>
                      <span className="block max-w-40 truncate">{h.name}</span>
                    </Tooltip>
                  </td>
                  <td className="p-3 whitespace-nowrap">
                    <Badge variant="outline">{marketLabel[h.market] || h.market}</Badge>
                  </td>
                  <td className="p-3 whitespace-nowrap text-muted-foreground">{h.asset_class}</td>
                  <td className="p-3 whitespace-nowrap text-muted-foreground">{h.first_buy_date}</td>
                  <td className="p-3 whitespace-nowrap text-muted-foreground">{h.closed_at}</td>
                  <td className="p-3 text-right whitespace-nowrap">{h.holding_days} 天</td>
                  <td className="p-3 text-right whitespace-nowrap">{formatPrice(h.total_buy_amount, h.currency, 2)}</td>
                  <td className="p-3 text-right whitespace-nowrap">
                    <span className={`font-medium ${positive ? upColor : downColor}`}>
                      {formatPrice(h.realized_pnl, h.currency, 2)}
                    </span>
                  </td>
                  <td className="p-3 text-right whitespace-nowrap">
                    {h.is_crazy_trader ? (
                      <span className="text-muted-foreground">--%</span>
                    ) : pct === null ? (
                      <span className="text-muted-foreground">N/A</span>
                    ) : (
                      <span className={`font-medium ${positive ? upColor : downColor}`}>
                        {formatPct(pct)}
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => setDetailId(h.id)}>
                        <Eye className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteClick(h)}>
                        <Trash2 className="w-3.5 h-3.5 text-destructive" />
                      </Button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      </div>

      <div className={`text-sm text-muted-foreground transition-all duration-500 ease-out delay-150 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <Pagination
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={handlePageSizeChange}
        />
      </div>

      <ClosedHoldingDetailDialog
        id={detailId}
        open={detailId !== null}
        onOpenChange={(open) => !open && setDetailId(null)}
      />
    </div>
  )
}
