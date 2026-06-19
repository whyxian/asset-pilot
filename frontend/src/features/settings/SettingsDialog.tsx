import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useSettings, type ColorScheme } from '@/lib/settings'

const COLOR_OPTIONS: { value: ColorScheme; label: string; desc: string; up: string; down: string }[] = [
  { value: 'rise-green', label: '绿涨红跌', desc: '国际市场', up: '#16a34a', down: '#dc2626' },
  { value: 'rise-red', label: '红涨绿跌', desc: 'A股惯例', up: '#dc2626', down: '#16a34a' },
]

export function SettingsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { settings, setColorScheme } = useSettings()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>设置</DialogTitle>
        </DialogHeader>
        <div className="space-y-6 pt-2">
          {/* 涨跌颜色 */}
          <fieldset className="space-y-3">
            <legend className="text-sm font-medium text-muted-foreground">涨跌颜色</legend>
            <Select value={settings.colorScheme} onValueChange={(v) => setColorScheme(v as ColorScheme)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COLOR_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} className="py-2">
                    <span className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <span className="text-sm font-bold" style={{ color: opt.up }}>↑</span>
                        <span className="text-xs text-muted-foreground">涨</span>
                        <span className="text-sm font-bold" style={{ color: opt.down }}>↓</span>
                        <span className="text-xs text-muted-foreground">跌</span>
                      </span>
                      <span className="text-xs text-muted-foreground">· {opt.desc}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </fieldset>
        </div>
      </DialogContent>
    </Dialog>
  )
}
