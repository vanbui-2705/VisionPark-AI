import { useSyncExternalStore } from 'react'
import { EN } from './translations'
let language: 'vi' | 'en' = 'vi'
const listeners = new Set<() => void>()
export function setLanguage(value: 'vi' | 'en') {
  if (value === language) return
  language = value
  listeners.forEach(fn => fn())
}
export function t(value: string): string { return language === 'en' ? EN[value] ?? value : value }
export function useLanguage() {
  return useSyncExternalStore(fn => { listeners.add(fn); return () => listeners.delete(fn) }, () => language)
}
