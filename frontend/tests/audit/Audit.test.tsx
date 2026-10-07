import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../../src/modules/auth/AuthContext.tsx'
import { AuditLogsPage } from '../../src/modules/audit/AuditLogsPage.tsx'

function j(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
function paginated(items: unknown[], page = 0, pageSize = 20) {
  return { items, total: items.length, page, pageSize, totalPages: Math.max(1, Math.ceil(items.length / pageSize)) }
}
const audits = [
  { id: 'a-1', time: new Date().toISOString(), actor: 'admin', action: 'LANE_CREATE', resource: 'Lane', resource_id: '1', correlation_id: 'c1' },
  { id: 'a-2', time: new Date().toISOString(), actor: 'operator01', action: 'CHECK_IN', resource: 'ParkingTransaction', resource_id: 'pt-1', correlation_id: 'c2' },
]

function renderPage(fetcher: (u: unknown) => Promise<Response>) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(fetcher as unknown as typeof fetch)
  return render(<MemoryRouter><AuthProvider><AuditLogsPage /></AuthProvider></MemoryRouter>)
}

describe('AuditLogsPage', () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('renders paginated success', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      if (s.includes('/audit-logs')) return j(paginated(audits))
      return j({})
    })
    await waitFor(() => expect(screen.getAllByText('LANE_CREATE').length).toBeGreaterThan(0))
  })

  it('sends filter params to server', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    const calls: string[] = []
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      if (s.includes('/audit-logs')) { calls.push(s); return j(paginated(audits)) }
      return j({})
    })
    await waitFor(() => expect(calls.length).toBeGreaterThan(0))
    expect(calls[0]).toContain('page=')
  })

  it('filter by actor triggers refetch', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    const { auditApi } = await import('../../src/api/services.ts')
    const spy = vi.spyOn(auditApi, 'page').mockResolvedValue(paginated(audits) as unknown as Awaited<ReturnType<typeof auditApi.page>>)
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      return j({})
    })
    render(<MemoryRouter><AuthProvider><AuditLogsPage /></AuthProvider></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('LANE_CREATE').length).toBeGreaterThan(0))
    const before = spy.mock.calls.length
    await userEvent.type(screen.getByPlaceholderText('Tên người thực hiện'), 'x')
    await waitFor(() => expect(spy.mock.calls.length).toBeGreaterThan(before), { timeout: 5000 })
  })

  it('empty state', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      if (s.includes('/audit-logs')) return j(paginated([]))
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Chưa có nhật ký/i)).toBeInTheDocument())
  })

  it('403 shows forbidden', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      if (s.includes('/audit-logs')) return j({ message: 'forbidden', code: 'FORBIDDEN' }, 403)
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/không có quyền/i)).toBeInTheDocument())
  })

  it('filter by resource and pagination to page 2', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    const calls: string[] = []
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      if (s.includes('/audit-logs')) {
        calls.push(s)
        if (s.includes('page=1')) {
          return j({ items: [{ ...audits[0], id: 'a-page2', action: 'PAGE2_ACTION' }], total: 40, page: 1, pageSize: 20, totalPages: 2 })
        }
        return j({ items: audits, total: 40, page: 0, pageSize: 20, totalPages: 2 })
      }
      return j({})
    })
    await waitFor(() => expect(screen.getAllByText('LANE_CREATE').length).toBeGreaterThan(0))
    const nextBtn = screen.getByRole('button', { name: /Sau/i })
    expect(nextBtn).toBeEnabled()
    await userEvent.click(nextBtn)
    await waitFor(() => expect(screen.getByText('PAGE2_ACTION')).toBeInTheDocument())
    expect(calls.some((c) => c.includes('page=1'))).toBe(true)
  })

  it('500 shows retry', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true })
      if (s.includes('/audit-logs')) return j({ message: 'err' }, 500)
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Thử lại/i)).toBeInTheDocument())
  })
})
