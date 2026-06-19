"use client"

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type ColorScheme = 'rise-green' | 'rise-red'

interface Settings {
  colorScheme: ColorScheme
}

interface SettingsContextType {
  settings: Settings
  setColorScheme: (s: ColorScheme) => void
  upColor: string   // 涨的颜色（text-green/red-600）
  downColor: string  // 跌的颜色（text-green/red-600）
}

const STORAGE_KEY = 'assetpilot-settings'
const DEFAULT: Settings = { colorScheme: 'rise-green' }

const SettingsContext = createContext<SettingsContextType | null>(null)

function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...DEFAULT, ...JSON.parse(raw) }
  } catch { /* ignore */ }
  return DEFAULT
}

function saveSettings(s: Settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(loadSettings)

  useEffect(() => { saveSettings(settings) }, [settings])

  const setColorScheme = (colorScheme: ColorScheme) =>
    setSettings((prev) => ({ ...prev, colorScheme }))

  const isGreenUp = settings.colorScheme === 'rise-green'
  const upColor = isGreenUp ? 'text-green-600' : 'text-red-600'
  const downColor = isGreenUp ? 'text-red-600' : 'text-green-600'

  return (
    <SettingsContext.Provider value={{ settings, setColorScheme, upColor, downColor }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useColors() {
  const ctx = useContext(SettingsContext)
  if (!ctx) return { upColor: 'text-green-600', downColor: 'text-red-600' }
  return { upColor: ctx.upColor, downColor: ctx.downColor }
}

export function useSettings() {
  const ctx = useContext(SettingsContext)
  if (!ctx) return { settings: DEFAULT, setColorScheme: () => {} }
  return { settings: ctx.settings, setColorScheme: ctx.setColorScheme }
}
