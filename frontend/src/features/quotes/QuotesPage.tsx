import { useEffect, useState, useCallback } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useQuoteSearch } from '@/hooks/useQuote'
import { cn, formatPrice } from '@/lib/utils'
import { useColors } from '@/lib/settings'
import type { AssetQuote } from '@/types'

// 已知加密货币符号
const CRYPTO_SYMBOLS = new Set([
  'BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'ADA', 'DOT', 'LTC', 'BCH', 'BNB',
  'AVAX', 'MATIC', 'LINK', 'UNI', 'ATOM', 'ETC', 'XLM', 'FIL', 'TRX', 'APT',
])

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

const sourceBadgeVariant: Record<string, 'default' | 'secondary' | 'outline'> = {
  TENCENT: 'default',
  SINA: 'outline',
  COINGLASS: 'secondary',
  EASTMONEY_FUND: 'secondary',
  AKSHARE: 'outline',
}

function QuoteCard({ quote }: { quote: AssetQuote }) {
  const { upColor, downColor } = useColors()
  const price = typeof quote.price === 'string' ? parseFloat(quote.price as unknown as string) : quote.price
  const changePrice = quote.change_price != null
    ? (typeof quote.change_price === 'string' ? parseFloat(quote.change_price as unknown as string) : quote.change_price)
    : null
  const changeColor =
    quote.change_ratio != null
      ? quote.change_ratio >= 0
        ? upColor
        : downColor
      : 'text-muted-foreground'

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lg">{quote.name}</h3>
          <p className="text-sm text-muted-foreground">{quote.ticker}</p>
        </div>
        <Badge variant={sourceBadgeVariant[quote.source] || 'outline'}>
          {quote.source}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-muted-foreground">最新价</span>
          <div className="text-2xl font-bold">
            {price > 0 ? formatPrice(price) : 'N/A'}
          </div>
        </div>
        <div>
          <span className="text-muted-foreground">涨跌</span>
          <div className={cn('text-lg font-semibold', changeColor)}>
            {changePrice != null
              ? `${changePrice >= 0 ? '+' : ''}${formatPrice(changePrice)}`
              : '-'}
            {quote.change_ratio != null &&
              ` (${quote.change_ratio >= 0 ? '+' : ''}${quote.change_ratio.toFixed(2)}%)`}
          </div>
        </div>
        <div>
          <span className="text-muted-foreground">货币</span>
          <div>{quote.currency}</div>
        </div>
        <div>
          <span className="text-muted-foreground">更新时间</span>
          <div className="text-xs">
            {new Date(quote.updated_at).toLocaleString('zh-CN')}
          </div>
        </div>
      </div>
    </div>
  )
}

export function QuotesPage() {
  const [input, setInput] = useState('')
  const [selectedOption, setSelectedOption] = useState<string>('cn_stock')

  // 入场动画
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])

  const quoteMutation = useQuoteSearch()

  const handleSearch = useCallback(() => {
    const code = input.trim().toUpperCase()
    if (!code) return

    const option = MARKET_OPTIONS.find((o) => o.value === selectedOption)
    if (!option) return

    quoteMutation.mutate({
      market: option.market,
      codes: [code],
      assetClass: option.assetClass,
    })
  }, [input, selectedOption, quoteMutation])

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

  const results: AssetQuote[] = quoteMutation.data || []

  return (
    <div className="space-y-6">
      <div className={`transition-all duration-500 ease-out ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
        <h1 className="text-2xl font-bold">行情查询</h1>
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
          <Select value={selectedOption} onValueChange={setSelectedOption}>
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
          <Button onClick={handleSearch} disabled={quoteMutation.isPending}>
            <Search className="w-4 h-4 mr-2" />
            查询
          </Button>
        </div>
      </div>

      {/* 加载态 */}
      {quoteMutation.isPending && (
        <div className="space-y-3">
          <Skeleton className="h-32 w-full max-w-md" />
        </div>
      )}

      {/* 错误态 */}
      {quoteMutation.isError && (
        <div className="flex flex-col items-start gap-2 p-4 border border-destructive/50 rounded-md bg-destructive/10 max-w-md">
          <p className="text-destructive font-medium">查询失败</p>
          <p className="text-sm text-muted-foreground">
            {quoteMutation.error instanceof Error
              ? quoteMutation.error.message
              : '未知错误'}
          </p>
        </div>
      )}

      {/* 查询结果 */}
      {!quoteMutation.isPending && !quoteMutation.isError && results.length > 0 && (
        <div className={`transition-all duration-500 ease-out delay-100 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
          <div className="space-y-3 max-w-md">
            {results.map((q) => (
              <QuoteCard key={q.ticker} quote={q} />
            ))}
          </div>
        </div>
      )}

      {/* 初始空态 — 没有任何查询时显示 */}
      {!quoteMutation.isPending && !quoteMutation.isError && results.length === 0 && (
        <div className="flex items-center justify-center h-64 border rounded-md bg-muted/20">
          <p className="text-muted-foreground">输入标的代码查看实时行情</p>
        </div>
      )}
    </div>
  )
}
