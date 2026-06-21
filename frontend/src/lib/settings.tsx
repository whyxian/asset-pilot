"use client"

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { TOAST_DURATION } from '@/lib/config'

export type ColorScheme = 'rise-green' | 'rise-red'

interface Settings {
  colorScheme: ColorScheme
  toastDuration: number  // toast 显示时长（毫秒），0 = 不自动消失
}

interface SettingsContextType {
  settings: Settings
  setColorScheme: (s: ColorScheme) => void
  setToastDuration: (n: number) => void
  upColor: string
  downColor: string
  toastDuration: number
}

const STORAGE_KEY = 'assetpilot-settings'
const DEFAULT: Settings = { colorScheme: 'rise-green', toastDuration: TOAST_DURATION }

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

  const setToastDuration = (toastDuration: number) =>
    setSettings((prev) => ({ ...prev, toastDuration }))

  const isGreenUp = settings.colorScheme === 'rise-green'
  const upColor = isGreenUp ? 'text-green-600' : 'text-red-600'
  const downColor = isGreenUp ? 'text-red-600' : 'text-green-600'

  return (
    <SettingsContext.Provider value={{ settings, setColorScheme, setToastDuration, upColor, downColor, toastDuration: settings.toastDuration }}>
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
  if (!ctx) return { settings: DEFAULT, setColorScheme: () => {}, setToastDuration: () => {} }
  return { settings: ctx.settings, setColorScheme: ctx.setColorScheme, setToastDuration: ctx.setToastDuration }
}

export function useToastDuration() {
  const ctx = useContext(SettingsContext)
  return ctx?.toastDuration ?? TOAST_DURATION
}
