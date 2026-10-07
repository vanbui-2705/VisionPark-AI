import { apiClient } from '../api/client'
import { setLanguage } from './i18n'
export type Preferences = { theme: 'light' | 'dark'; language: 'vi' | 'en' }
export function applyPreferences(pref: Preferences) {
  document.documentElement.dataset.theme = pref.theme
  document.documentElement.lang = pref.language
  setLanguage(pref.language)
  localStorage.setItem('vp.preferences', JSON.stringify(pref))
  window.dispatchEvent(new CustomEvent('vp-preferences', { detail: pref }))
}
export async function loadPreferences() {
  const pref = await apiClient.get<Preferences>('/api/v1/auth/preferences')
  if (!['light', 'dark'].includes(pref.theme) || !['vi', 'en'].includes(pref.language)) throw new Error('Invalid preferences response')
  applyPreferences(pref)
  return pref
}
