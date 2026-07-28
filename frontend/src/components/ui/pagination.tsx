import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
}

const PAGE_SIZE_OPTIONS = [20, 50, 100]

/** 计算页码按钮：超过 7 页时中间省略 */
function getPageButtons(current: number, totalPages: number): (number | '...')[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }
  const buttons: (number | '...')[] = [1]
  const start = Math.max(2, current - 1)
  const end = Math.min(totalPages - 1, current + 1)
  if (start > 2) buttons.push('...')
  for (let i = start; i <= end; i++) buttons.push(i)
  if (end < totalPages - 1) buttons.push('...')
  buttons.push(totalPages)
  return buttons
}

export function Pagination({ page, pageSize, total, onPageChange, onPageSizeChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  if (total === 0) return null

  const buttons = getPageButtons(page, totalPages)

  return (
    <div className="flex items-center justify-between gap-4 mt-3">
      {/* 左：总条数 + 每页条数 */}
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span>共 {total} 条</span>
        <select
          className="h-7 rounded-md border bg-background px-2 text-xs"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          {PAGE_SIZE_OPTIONS.map((s) => (
            <option key={s} value={s}>{s} 条/页</option>
          ))}
        </select>
      </div>

      {/* 右：页码导航 */}
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft className="w-4 h-4" />
        </Button>
        {buttons.map((b, i) =>
          b === '...' ? (
            <span key={`ellipsis-${i}`} className="px-2 text-muted-foreground">…</span>
          ) : (
            <Button
              key={b}
              variant={b === page ? 'default' : 'outline'}
              size="sm"
              className={cn('min-w-8', b === page && 'pointer-events-none')}
              onClick={() => onPageChange(b)}
            >
              {b}
            </Button>
          ),
        )}
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  )
}
