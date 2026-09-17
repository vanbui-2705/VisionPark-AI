import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider, useAuth } from '../../src/modules/auth/AuthContext.tsx'

function Probe() {
  const { initialized, isAuthenticated, user, isAdmin } = useAuth()
  return <div data-testid="probe">{JSON.stringify({ initialized, isAuthenticated, role: user?.role ?? null, isAdmin })}</div>
}
function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }

describe('AuthProvider', () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('startup without token -> initialized + not authenticated', async () => {
    render(<MemoryRouter><AuthProvider><Probe /></AuthProvider></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId('probe').textContent).toContain('"initialized":true'))
    expect(screen.getByTestId('probe').textContent).toContain('"isAuthenticated":false')
  })

  it('startup with valid token -> authenticated', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      if (String(u).includes('/auth/me')) return json({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      return json({})
    })
    render(<MemoryRouter><AuthProvider><Probe /></AuthProvider></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId('probe').textContent).toContain('"isAuthenticated":true'))
    expect(screen.getByTestId('probe').textContent).toContain('"ADMIN"')
  })

  it('startup with expired token (401) -> clears token', async () => {
    localStorage.setItem('visionpark.access_token', 'bad')
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json({ code: 'UNAUTHENTICATED', message: 'x' }, 401))
    render(<MemoryRouter><AuthProvider><Probe /></AuthProvider></MemoryRouter>)
    await waitFor(() => expect(screen.getByTestId('probe').textContent).toContain('"initialized":true'))
    await waitFor(() => expect(localStorage.getItem('visionpark.access_token')).toBeNull())
  })
})
