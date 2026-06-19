import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useSettings, type ColorScheme } from '@/lib/settings'

const COLOR_OPTIONS: { value: ColorScheme; label: string; up: string; down: string; upLabel: string; downLabel: string }[] = [
  { value: 'rise-green', label: '红涨绿跌（A股惯例）', up: 'text-green-600', down: 'text-red-600', upLabel: '涨', downLabel: '跌' },
  { value: 'rise-red', label: '绿涨红跌（国际市场）', up: 'text-red-600', down: 'text-green-600', upLabel: '涨', downLabel: '跌' },
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
                      <span className="flex items-center gap-1.5">
                        <span className={`${opt.up} font-medium`}>▲{opt.upLabel}</span>
                        <span className={`${opt.down} font-medium`}>▼{opt.downLabel}</span>
                      </span>
                      <span className="text-muted-foreground text-xs">{opt.label}</span>
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
