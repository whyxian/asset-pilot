import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { SidebarLayout } from '@/components/layout/SidebarLayout'
import { OverviewPage } from '@/features/overview/OverviewPage'
import { HoldingsPage } from '@/features/holdings/HoldingsPage'
import { TransactionsPage } from '@/features/transactions/TransactionsPage'
import { QuotesPage } from '@/features/quotes/QuotesPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <SidebarLayout>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/holdings" element={<HoldingsPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/quotes" element={<QuotesPage />} />
        </Routes>
      </SidebarLayout>
    </BrowserRouter>
  )
}
