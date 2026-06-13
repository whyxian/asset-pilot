import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { SidebarLayout } from '@/components/layout/SidebarLayout'

// 按页面 code-split：每个页面打成独立 chunk，按需加载，缩小首屏 bundle
// 页面是命名导出，用 .then() 桥接到 React.lazy 期望的 default 形态
const OverviewPage = lazy(() =>
  import('@/features/overview/OverviewPage').then((m) => ({ default: m.OverviewPage })),
)
const HoldingsPage = lazy(() =>
  import('@/features/holdings/HoldingsPage').then((m) => ({ default: m.HoldingsPage })),
)
const TransactionsPage = lazy(() =>
  import('@/features/transactions/TransactionsPage').then((m) => ({ default: m.TransactionsPage })),
)
const QuotesPage = lazy(() =>
  import('@/features/quotes/QuotesPage').then((m) => ({ default: m.QuotesPage })),
)

/** 懒加载页面切换时的占位符 */
function PageFallback() {
  return (
    <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
      加载中…
    </div>
  )
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <SidebarLayout>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/holdings" element={<HoldingsPage />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            <Route path="/quotes" element={<QuotesPage />} />
          </Routes>
        </Suspense>
      </SidebarLayout>
    </BrowserRouter>
  )
}
