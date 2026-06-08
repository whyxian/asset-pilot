import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export function QuotesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">行情查询</h1>

      <div className="flex gap-2">
        <Input
          placeholder="输入代码查询，如 600519 / AAPL / BTC"
          className="max-w-md"
        />
        <Button>
          <Search className="w-4 h-4 mr-2" />
          查询
        </Button>
      </div>

      <div className="flex items-center justify-center h-64 border rounded-md bg-muted/20">
        <p className="text-muted-foreground">输入标的代码查看实时行情</p>
      </div>
    </div>
  )
}
