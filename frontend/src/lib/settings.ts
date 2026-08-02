"use client"

import { createContext, useContext } from 'react'
import { TOAST_DURATION } from '@/lib/config'

export type ColorScheme = 'rise-green' | 'rise-red'

export interface Settings {
  colorScheme: ColorScheme
  toastDuration: number  // toast 显示时长（毫秒），0 = 不自动消失
}

export interface SettingsContextType {
  settings: Settings
  setColorScheme: (s: ColorScheme) => void
  setToastDuration: (n: number) => void
  upColor: string
  downColor: string
  toastDuration: number
}

const STORAGE_KEY = 'assetpilot-settings'
const DEFAULT: Settings = { colorScheme: 'rise-green', toastDuration: TOAST_DURATION }

export const SettingsContext = createContext<SettingsContextType | null>(null)

export function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...DEFAULT, ...JSON.parse(raw) }
  } catch { /* ignore */ }
  return DEFAULT
}

export function saveSettings(s: Settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
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
