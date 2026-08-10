import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Search } from 'lucide-react'
import { WatchlistGrid } from './WatchlistGrid'
import { QuoteDialog } from './QuoteDialog'
import { useWatchlistQuotes, useRemoveWatchlist } from '@/hooks/useWatchlist'
import type { WatchlistWithQuote } from '@/types'

interface MarketOption {
  value: string
  label: string
  market: 'CN' | 'US' | 'CRYPTO'
  assetClass: 'STOCK' | 'FUND' | 'CRYPTO'
}

const MARKET_OPTIONS: MarketOption[] = [
  { value: 'cn_stock', label: 'A 股', market: 'CN', assetClass: 'STOCK' },
  { value: 'cn_fund', label: 'A 股基金', market: 'CN', assetClass: 'FUND' },
  { value: 'us_stock', label: '美股', market: 'US', assetClass: 'STOCK' },
  { value: 'us_fund', label: '美股 ETF', market: 'US', assetClass: 'FUND' },
  { value: 'crypto', label: '加密货币', market: 'CRYPTO', assetClass: 'CRYPTO' },
]

const CRYPTO_SYMBOLS = new Set([
  'BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'ADA', 'DOT', 'LTC', 'BCH', 'BNB',
  'AVAX', 'MATIC', 'LINK', 'UNI', 'ATOM', 'ETC', 'XLM', 'FIL', 'TRX', 'APT',
])

/** 自动识别输入代码的市场和品种类型 */
function detectMarket(input: string): MarketOption | null {
  const code = input.trim().toUpperCase()
  if (!code) return null

  // 加密货币：已知符号
  if (CRYPTO_SYMBOLS.has(code)) {
    return MARKET_OPTIONS[4] // crypto
  }

  // 6 位纯数字 → A 股（默认），用户可手动切到 A 股基金
  if (/^\d{6}$/.test(code)) {
    return MARKET_OPTIONS[0] // cn_stock
  }

  // 纯字母 1-5 位（可能带 .后缀）→ 美股
  if (/^[A-Z]{1,5}(\.[A-Z]{1,3})?$/.test(code)) {
    return MARKET_OPTIONS[2] // us_stock
  }

  return null
}

export function QuotesPage() {
  const [input, setInput] = useState('')
  const [selectedOption, setSelectedOption] = useState<string>('cn_stock')

  // 弹窗状态：search 模式（携带查询参数）或 detail 模式（携带已有行情）
  const [dialog, setDialog] = useState<{
    open: boolean
    query?: { market: 'CN' | 'US' | 'CRYPTO'; codes: string[]; assetClass: 'STOCK' | 'FUND' | 'CRYPTO' }
    detail?: WatchlistWithQuote
  }>({ open: false })

  const { data: watchlist, isLoading } = useWatchlistQuotes()
  const removeWatchlist = useRemoveWatchlist()

  // 入场动画
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])

  const handleSearch = useCallback(() => {
    const code = input.trim().toUpperCase()
    if (!code) return

    const option = MARKET_OPTIONS.find((o) => o.value === selectedOption)
    if (!option) return

    setDialog({
      open: true,
      query: { market: option.market, codes: [code], assetClass: option.assetClass },
    })
  }, [input, selectedOption])

  // 输入变化时自动检测市场类型
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setInput(value)
    const detected = detectMarket(value)
    if (detected) {
      setSelectedOption(detected.value)
    }
  }

  // 回车触发查询
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  function handleCardClick(item: WatchlistWithQuote) {
    setDialog({ open: true, detail: item })
  }

  return (
    <div className="space-y-6">
      <div className={`transition-all duration-500 ease-out ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <h1 className="text-2xl font-bold">行情</h1>
      </div>

      {/* 搜索栏 */}
      <div className={`transition-all duration-500 ease-out delay-50 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <div className="flex gap-2">
          <Input
            placeholder="输入代码查询，如 600519 / AAPL / BTC"
            className="max-w-xs"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
          />
          <Select value={selectedOption} onValueChange={(v) => setSelectedOption(v ?? '')}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MARKET_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleSearch}>
            <Search className="w-4 h-4 mr-2" />
            查询
          </Button>
        </div>
      </div>

      {/* 自选区（页面主体，30s 轮询） */}
      <div className={`transition-all duration-500 ease-out delay-100 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <WatchlistGrid
          items={watchlist ?? []}
          loading={isLoading}
          onCardClick={handleCardClick}
          onRemove={(id) => removeWatchlist.mutate(id)}
        />
      </div>

      {/* 查询结果 / 卡片详情 弹窗（key 随标的+开关变化，重挂载以重置弹窗内部状态） */}
      <QuoteDialog
        key={`${dialog.detail?.ticker ?? dialog.query?.codes[0] ?? ''}-${dialog.open}`}
        open={dialog.open}
        onOpenChange={(v) => setDialog({ open: v })}
        query={dialog.query}
        quote={dialog.detail?.quote ?? null}
      />
    </div>
  )
}
