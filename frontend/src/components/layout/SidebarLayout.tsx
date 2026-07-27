import { useState } from 'react'
import { DollarSign, LayoutDashboard, Wallet, ArrowLeftRight, Search, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { SettingsDialog } from '@/features/settings/SettingsDialog'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '概览' },
  { to: '/holdings', icon: Wallet, label: '持仓' },
  { to: '/cash', icon: DollarSign, label: '现金' },
  { to: '/transactions', icon: ArrowLeftRight, label: '交易' },
  { to: '/quotes', icon: Search, label: '行情' },
]

export function SidebarLayout({ children }: { children: React.ReactNode }) {
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <div className="flex h-screen">
      {/* 侧边栏 */}
      <aside className="w-56 border-r bg-sidebar flex flex-col shrink-0">
        {/* 项目名称 */}
        <div className="h-14 flex items-center px-5 border-b">
          <span className="font-bold text-base">AssetPilot</span>
        </div>

        {/* 导航 */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                  isActive
                    ? 'bg-accent text-accent-foreground font-medium'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                )
              }
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* 左下角设置 */}
        <div className="p-3 border-t">
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <Settings className="w-4 h-4" />
            设置
          </button>
        </div>
      </aside>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />

      {/* 主内容区 */}
      <main className="flex-1 overflow-auto bg-background">
        <div className="py-8 px-10">
          {children}
        </div>
      </main>
    </div>
  )
}
