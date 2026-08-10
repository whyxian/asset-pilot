import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Heart, Library } from 'lucide-react'
import { cn, formatPrice, toNum } from '@/lib/utils'
import { useColors } from '@/lib/settings'
import { searchVarieties } from '@/api/endpoints'
import { useQuoteSearch } from '@/hooks/useQuote'
import { useAddVariety, useAddWatchlist, useRemoveWatchlist, useWatchlistQuotes } from '@/hooks/useWatchlist'
import { toast } from 'sonner'
import type { AssetQuote } from '@/types'

const sourceBadgeVariant: Record<string, 'default' | 'secondary' | 'outline'> = {
  TENCENT: 'default',
  SINA: 'outline',
  COINGLASS: 'secondary',
  EASTMONEY_FUND: 'secondary',
  AKSHARE: 'outline',
}

/** 行情展示区（弹窗共用） */
function QuoteInfo({ quote }: { quote: AssetQuote }) {
  const { upColor, downColor } = useColors()
  const changeRatio = quote.change_ratio
  const isUp = changeRatio != null && changeRatio >= 0
  const changeColor = changeRatio == null ? 'text-muted-foreground' : isUp ? upColor : downColor

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold">{quote.name}</h3>
          <p className="text-sm text-muted-foreground">{quote.ticker}</p>
        </div>
        <Badge variant={sourceBadgeVariant[quote.source] || 'outline'}>{quote.source}</Badge>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-muted-foreground">现价</span>
          <p className={cn('text-2xl font-bold tabular-nums', changeColor)}>
            {formatPrice(toNum(quote.price), quote.currency, 2)}
          </p>
        </div>
        <div>
          <span className="text-muted-foreground">涨跌</span>
          <p className={cn('text-lg font-semibold', changeColor)}>
            {quote.change_price != null
              ? `${quote.change_price >= 0 ? '+' : ''}${formatPrice(toNum(quote.change_price))}`
              : '-'}
            {changeRatio != null && ` (${changeRatio >= 0 ? '+' : ''}${changeRatio.toFixed(2)}%)`}
          </p>
        </div>
        <div>
          <span className="text-muted-foreground">货币</span>
          <p>{quote.currency}</p>
        </div>
        <div>
          <span className="text-muted-foreground">更新时间</span>
          <p className="text-xs">{new Date(quote.updated_at).toLocaleString('zh-CN')}</p>
        </div>
      </div>
    </div>
  )
}

/**
 * 查询结果 / 卡片详情 共用弹窗
 *
 * - search 模式：传入 query 参数，内部拉取行情（query 变化即触发）
 * - detail 模式：直接传入 quote，不再请求
 * - 操作区：♥ 收藏（乐观更新，已收藏态可取消）+「添加到品种库」（仅注册）
 */
export function QuoteDialog({
  open,
  onOpenChange,
  query,
  quote: presetQuote,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  /** search 模式：查询参数（open 时生效） */
  query?: { market: 'CN' | 'US' | 'CRYPTO'; codes: string[]; assetClass: 'STOCK' | 'FUND' | 'CRYPTO' } | null
  /** detail 模式：直接传入的行情 */
  quote?: AssetQuote | null
}) {
  const searchMut = useQuoteSearch()
  const { data: watchlist } = useWatchlistQuotes()
  const addWatchlist = useAddWatchlist()
  const removeWatchlist = useRemoveWatchlist()
  const addVariety = useAddVariety()
  const qc = useQueryClient()

  // search 模式：query 变化时重新查询
  // ref 防重：React StrictMode 开发模式下 effect 会执行两次（mount 双调用），
  // 同一 query key 只提交一次 mutation，避免发送重复请求
  const submittedKey = useRef('')
  useEffect(() => {
    if (open && query) {
      const key = `${query.market}-${query.codes.join(',')}-${query.assetClass}`
      if (submittedKey.current === key) return
      submittedKey.current = key
      searchMut.mutate(query)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, query?.market, query?.codes.join(','), query?.assetClass])

  const quote = presetQuote ?? searchMut.data?.[0] ?? null
  const isError = !presetQuote && searchMut.isError
  const isLoading = !presetQuote && searchMut.isPending
  const errorMessage = searchMut.error instanceof Error ? searchMut.error.message : '未知错误'

  // 品种库状态：弹窗打开时真实查询（收藏自动注册 / 导入 / 手动添加都算已添加）
  // 用 React Query 管理：无同步 setState 级联渲染问题，同 ticker 重复打开有缓存
  const varietyQuery = useQuery({
    queryKey: ['variety-check', quote?.ticker ?? '', quote?.asset_class ?? '', quote?.market ?? ''],
    queryFn: () => searchVarieties(quote!.ticker),
    enabled: open && !!quote,
  })
  // 按钮状态完全由后端品种库查询决定（前端不可信，不做任何推断）
  // 存在性检查按市场规则区分（2026-08-10 用户确认）：
  // - US/CRYPTO：ticker 不重复 → ticker 级匹配（SPY 以 STOCK 查询，库里 FUND 也算已添加）
  // - CN：FUND/STOCK/ETF 可能重复（000001 股票 vs 基金）→ 三元组精确匹配
  const inVarietyLib = (varietyQuery.data ?? []).some((v) => {
    if (quote?.market === 'CN') {
      return v.ticker === quote?.ticker && v.asset_class === quote?.asset_class
    }
    return v.ticker === quote?.ticker
  })
  const varietyAdded = inVarietyLib
  const invalidateVarietyCheck = () => qc.invalidateQueries({ queryKey: ['variety-check', quote?.ticker ?? ''] })

  // 收藏状态：从自选列表里找当前 ticker（三元组匹配）
  const watchEntry = quote
    ? watchlist?.find((w) => w.ticker === quote.ticker && w.market === quote.market && w.asset_class === quote.asset_class)
    : undefined
  const isWatched = watchEntry != null

  function handleToggleWatch() {
    if (!quote) return
    if (isWatched) {
      removeWatchlist.mutate(watchEntry.id)
    } else {
      addWatchlist.mutate(
        { ticker: quote.ticker, asset_class: quote.asset_class, market: quote.market, name: quote.name, quote },
        {
          // 收藏成功后重新查询品种库状态（以后端为准，前端不推断）
          onSuccess: invalidateVarietyCheck,
        },
      )
    }
  }

  function handleAddVariety() {
    if (!quote) return
    addVariety.mutate(
      { ticker: quote.ticker, name: quote.name, market: quote.market, asset_class: quote.asset_class },
      {
        onSuccess: () => {
          invalidateVarietyCheck()
          toast.success('已添加到品种库')
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{query ? '查询结果' : '行情详情'}</DialogTitle>
          <DialogDescription className="sr-only">
            {quote ? `${quote.name} ${quote.ticker} 行情详情` : '加载中'}
          </DialogDescription>
        </DialogHeader>

        {isLoading && <Skeleton className="h-36 w-full" />}

        {isError && (
          <div className="flex flex-col items-start gap-2 p-4 border border-destructive/50 rounded-md bg-destructive/10">
            <p className="text-destructive font-medium">查询失败</p>
            <p className="text-sm text-muted-foreground">{errorMessage}</p>
          </div>
        )}

        {quote && (
          <>
            <QuoteInfo quote={quote} />
            <div className="flex gap-2 pt-2">
              <Button
                variant={isWatched ? 'outline' : 'default'}
                className="flex-1"
                onClick={handleToggleWatch}
                disabled={addWatchlist.isPending || removeWatchlist.isPending}
              >
                <Heart className={cn('w-4 h-4 mr-2', isWatched && 'fill-current text-destructive')} />
                {isWatched ? '已收藏（点击取消）' : '收藏'}
              </Button>
              <Button variant="outline" className="flex-1" onClick={handleAddVariety} disabled={varietyAdded}>
                <Library className="w-4 h-4 mr-2" />
                {varietyAdded ? '已添加' : '添加到品种库'}
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
