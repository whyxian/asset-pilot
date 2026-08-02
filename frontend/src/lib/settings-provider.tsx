"use client"

import { useEffect, useState, type ReactNode } from 'react'
import {
  loadSettings,
  saveSettings,
  SettingsContext,
  type ColorScheme,
  type Settings,
} from './settings'

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
