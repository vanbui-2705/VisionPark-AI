import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from '../../src/app/router.tsx'
import { AuthProvider } from '../../src/modules/auth/AuthContext.tsx'

function j(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }

function renderApp(initial: string, fetcher?: (url: unknown) => Promise<Response>) {
  if (fetcher) vi.spyOn(globalThis, 'fetch').mockImplementation(fetcher as unknown as typeof fetch)
  return render(<MemoryRouter initialEntries={[initial]}><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter>)
}

describe('Route guards', () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('guest -> /admin/lanes redirects to /login', async () => {
    renderApp('/admin/lanes')
    await waitFor(() => expect(screen.getByText(/VisionPark/i)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /đăng nhập/i })).toBeInTheDocument()
  })

  it('OPERATOR cannot access /admin/lanes (403)', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderApp('/admin/lanes', async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'op', display_name: 'Op', role: 'OPERATOR', active: true })
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/403/i)).toBeInTheDocument())
  })

  it('ADMIN can access /admin/lanes', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderApp('/admin/lanes', async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      if (s.includes('/lanes')) return j([])
      if (s.includes('/health/ready')) return j({ status: 'ready', alpr: { ready: true, provider: 'real' } })
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Quản lý làn/i)).toBeInTheDocument())
  })

  it('root / redirects OPERATOR to /station', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderApp('/', async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'op', display_name: 'Op', role: 'OPERATOR', active: true })
      if (s.includes('/health/ready')) return j({ status: 'ready', alpr: { provider: 'real' } })
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Trạm quét biển số/i)).toBeInTheDocument())
  })
})
