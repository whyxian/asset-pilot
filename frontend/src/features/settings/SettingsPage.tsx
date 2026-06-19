import { useColors, type ColorScheme } from '@/lib/settings'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export function SettingsPage() {
  return (
    <div className="space-y-6 max-w-lg">
      <h1 className="text-2xl font-bold">常规设置</h1>
      <ColorSchemeSelector />
    </div>
  )
}

function ColorSchemeSelector() {
  const { settings, setColorScheme } = useColors()

  const handleChange = (v: string) => {
    setColorScheme(v as ColorScheme)
  }

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-muted-foreground">涨跌颜色</label>
      <Select value={settings.colorScheme} onValueChange={handleChange}>
        <SelectTrigger className="w-60">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="rise-green">
            <span className="flex items-center gap-2">
              <span className="text-green-600">▲ 红涨</span>
              <span className="text-red-600">▼ 绿跌</span>
            </span>
          </SelectItem>
          <SelectItem value="rise-red">
            <span className="flex items-center gap-2">
              <span className="text-red-600">▲ 绿涨</span>
              <span className="text-green-600">▼ 红跌</span>
            </span>
          </SelectItem>
        </SelectContent>
      </Select>
      <p className="text-xs text-muted-foreground">
        {settings.colorScheme === 'rise-green' ? '涨=绿色（A股惯例）' : '涨=红色（国际市场惯例）'}
      </p>
    </div>
  )
}
