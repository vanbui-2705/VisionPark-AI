import { afterEach, expect, it, vi } from 'vitest'
import { apiClient } from '../../src/api/client'
import { loadPreferences } from '../../src/lib/preferences'
import { setLanguage, t } from '../../src/lib/i18n'

afterEach(() => { vi.restoreAllMocks(); setLanguage('vi'); localStorage.clear(); })
it('restores the server preference after the local cache is removed', async () => {
  localStorage.clear()
  vi.spyOn(apiClient, 'get').mockResolvedValue({ theme: 'dark', language: 'en' })
  await loadPreferences()
  expect(document.documentElement.dataset.theme).toBe('dark')
  expect(document.documentElement.lang).toBe('en')
  expect(t('Lịch sử nhận diện')).toBe('Recognition history')
  expect(JSON.parse(localStorage.getItem('vp.preferences')!)).toEqual({ theme: 'dark', language: 'en' })
})
