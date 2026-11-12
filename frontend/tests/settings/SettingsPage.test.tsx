import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SettingsPage } from '../../src/modules/settings/SettingsPage.tsx'
import { AuthContext, type AuthContextValue } from '../../src/modules/auth/AuthContext.tsx'

const response = (body: unknown) => new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } })

function renderFor(role: 'SYSTEM_ADMIN' | 'BUILDING_ADMIN', buildingId: string | null) {
  const user = { id: 'user', username: 'user', display_name: 'User', active: true, role, building_id: buildingId }
  const auth = { user, initialized: true, isAuthenticated: true, loading: false } as AuthContextValue
  return render(<MemoryRouter><AuthContext.Provider value={auth}><SettingsPage /></AuthContext.Provider></MemoryRouter>)
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.clear() })

describe('Settings building context', () => {
  it('does not call building-scoped APIs for a system administrator', async () => {
    const calls: string[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async url => { calls.push(String(url)); return response({ theme: 'light', language: 'vi' }) })
    renderFor('SYSTEM_ADMIN', null)
    expect(screen.getByText('Giá vé và vé tháng')).toBeInTheDocument()
    expect(screen.getByText(/chỉ cho phép tài khoản/)).toBeInTheDocument()
    await waitFor(() => expect(calls.some(url => url.includes('/preferences'))).toBe(true))
    expect(calls.some(url => url.includes('/pricing/') || url.includes('/tickets/'))).toBe(false)
  })

  it('shows an assignment empty state without firing scoped requests', async () => {
    const calls: string[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async url => { calls.push(String(url)); return response({ theme: 'light', language: 'vi' }) })
    renderFor('BUILDING_ADMIN', null)
    expect(screen.getByText('Chưa thể tải cấu hình vận hành')).toBeInTheDocument()
    await waitFor(() => expect(calls.some(url => url.includes('/preferences'))).toBe(true))
    expect(calls.some(url => url.includes('/pricing/') || url.includes('/tickets/'))).toBe(false)
  })
})
