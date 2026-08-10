import { Badge } from '@/components/ui/badge'
import { Heart } from 'lucide-react'
import { cn, formatPrice, toNum } from '@/lib/utils'
import { useColors } from '@/lib/settings'
import type { WatchlistWithQuote } from '@/types'

/** 自选卡片 — 复刻原 QuoteCard 样式：名称/代码 + 四格信息（最新价/涨跌/货币/更新时间）+ ♥ */
function WatchlistCard({
  item,
  onCardClick,
  onRemove,
}: {
  item: WatchlistWithQuote
  onCardClick: (item: WatchlistWithQuote) => void
  onRemove: (id: number) => void
}) {
  const { upColor, downColor } = useColors()
  const q = item.quote
  const changePrice = q?.change_price != null ? toNum(q.change_price) : null
  const changeRatio = q?.change_ratio
  const changeColor = changeRatio == null ? 'text-muted-foreground' : changeRatio >= 0 ? upColor : downColor

  return (
    <div
      className="rounded-lg border p-4 space-y-3 cursor-pointer hover:border-primary/50 transition-colors"
      onClick={() => onCardClick(item)}
    >
      {/* 头部：名称 + 代码 + ♥ */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-semibold truncate">{item.name || item.ticker}</h3>
          <p className="text-sm text-muted-foreground">{item.ticker}</p>
        </div>
        <button
          className={cn(
            'shrink-0 rounded-full p-1.5 transition-colors',
            'hover:bg-destructive/10 hover:text-destructive',
          )}
          title="取消收藏"
          onClick={(e) => {
            e.stopPropagation()
            onRemove(item.id)
          }}
        >
          <Heart className="w-4 h-4 fill-current text-destructive" />
        </button>
      </div>

      {/* 四格信息：最新价 / 涨跌 / 货币 / 更新时间 */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-muted-foreground">最新价</span>
          <div className={cn('text-xl font-bold tabular-nums', changeColor)}>
            {q && toNum(q.price) > 0 ? formatPrice(toNum(q.price), q.currency, 2) : 'N/A'}
          </div>
        </div>
        <div>
          <span className="text-muted-foreground">涨跌</span>
          <div className={cn('text-lg font-semibold tabular-nums', changeColor)}>
            {changePrice != null ? `${changePrice >= 0 ? '+' : ''}${formatPrice(changePrice)}` : '-'}
            {changeRatio != null && ` (${changeRatio >= 0 ? '+' : ''}${changeRatio.toFixed(2)}%)`}
            {q && item.status === 'HISTORICAL' && (
              <span className="ml-1 align-middle">
                <Badge variant="outline" className="text-[10px] px-1.5">历史</Badge>
              </span>
            )}
            {!q && <span className="ml-1 align-middle"><Badge variant="outline" className="text-[10px] px-1.5">无行情</Badge></span>}
          </div>
        </div>
        <div>
          <span className="text-muted-foreground">货币</span>
          <div>{q ? q.currency : '-'}</div>
        </div>
        <div>
          <span className="text-muted-foreground">更新时间</span>
          <div className="text-xs">
            {q ? new Date(q.updated_at).toLocaleString('zh-CN') : '-'}
          </div>
        </div>
      </div>
    </div>
  )
}

/** 自选区网格 — 响应式多列占满宽度；空态引导文案 */
export function WatchlistGrid({
  items,
  loading,
  onCardClick,
  onRemove,
}: {
  items: WatchlistWithQuote[]
  loading: boolean
  onCardClick: (item: WatchlistWithQuote) => void
  onRemove: (id: number) => void
}) {
  if (loading && items.length === 0) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-32 rounded-lg bg-muted/40 animate-pulse" />
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 border rounded-md bg-muted/20">
        <div className="text-center space-y-1">
          <p className="text-muted-foreground">暂无自选标的</p>
          <p className="text-sm text-muted-foreground/70">在上方输入代码查询，点击 ♥ 收藏</p>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      {items.map((item) => (
        <WatchlistCard
          key={item.id}
          item={item}
          onCardClick={onCardClick}
          onRemove={onRemove}
        />
      ))}
    </div>
  )
}
