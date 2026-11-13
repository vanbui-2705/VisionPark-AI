
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from '../../src/app/router.tsx'
import { AuthProvider } from '../../src/modules/auth/AuthContext.tsx'

function j(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function renderApp(
  initial: string,
  fetcher?: (url: unknown) => Promise<Response>,
) {
  if (fetcher) {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      fetcher as unknown as typeof fetch,
    )
  }

  return render(
    <MemoryRouter initialEntries={[initial]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('Route guards', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('guest -> /admin/lanes redirects to /login', async () => {
    renderApp('/admin/lanes')

    await waitFor(() =>
      expect(screen.getByText(/VisionPark/i)).toBeInTheDocument(),
    )

    expect(
      screen.getByRole('button', { name: /đăng nhập/i }),
    ).toBeInTheDocument()
  })

  it('OPERATOR can read lanes but cannot create them', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    renderApp('/admin/lanes', async (u) => {
      const s = String(u)

      if (s.includes('/auth/me')) {
        return j({
          id: '1',
          username: 'op',
          display_name: 'Op',
          role: 'OPERATOR',
          active: true,
        })
      }

      if (s.includes('/lanes')) return j([])

      return j({})
    })

    expect(await screen.findByText(/Quản lý làn/i)).toBeInTheDocument()

    expect(
      screen.queryByRole('button', { name: /Tạo làn/i }),
    ).not.toBeInTheDocument()
  })

  it('ACCOUNTANT cannot access station operations', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    renderApp(
      '/station/scan',
      async (u) =>
        String(u).includes('/auth/me')
          ? j({
              id: '1',
              username: 'accountant',
              role: 'ACCOUNTANT',
              is_active: true,
            })
          : j({}),
    )

    expect(await screen.findByText(/403/i)).toBeInTheDocument()
  })

  it('ACCOUNTANT can use dashboard without requesting forbidden lane or detection data', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    const calls: string[] = []

    renderApp('/admin/dashboard', async (u) => {
      const url = String(u)
      calls.push(url)

      if (url.includes('/auth/me')) {
        return j({
          id: '1',
          username: 'accountant',
          display_name: 'Accountant',
          role: 'ACCOUNTANT',
          active: true,
        })
      }

      // FIX PR #26:
      // API danh sách tòa nhà phải trả về mảng.
      if (url.includes('/api/v1/buildings')) {
        return j([])
      }

      if (url.includes('/parking/summary')) {
        return j({
          total: 0,
          parked: 0,
          manual: 0,
        })
      }

      if (url.includes('/parking/transactions')) {
        return j([])
      }

      if (url.includes('/health/ready')) {
        return j({
          status: 'ready',
          alpr: {
            status: 'ready',
            provider: 'real',
          },
        })
      }

      return j({})
    })

    expect(
      await screen.findByText('Parking Operations'),
    ).toBeInTheDocument()

    expect(screen.queryByText(/403/)).not.toBeInTheDocument()

    expect(
      calls.some(
        (url) =>
          url.includes('/alpr/detections') ||
          url.includes('/lanes'),
      ),
    ).toBe(false)
  })

  it('ACCOUNTANT can open audit', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    const accountant = renderApp('/admin/audit-logs', async (u) => {
      const url = String(u)

      if (url.includes('/auth/me')) {
        return j({
          id: '1',
          username: 'accountant',
          display_name: 'Accountant',
          role: 'ACCOUNTANT',
          active: true,
        })
      }

      if (url.includes('/audit-logs')) {
        return j({
          items: [],
          total: 0,
          page: 0,
          pageSize: 20,
          totalPages: 1,
        })
      }

      return j({})
    })

    expect(
      await screen.findByRole('heading', {
        name: 'Nhật ký kiểm tra',
      }),
    ).toBeInTheDocument()

    accountant.unmount()
  })

  it('OPERATOR can inspect a detection without requesting audit data', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    const calls: string[] = []

    renderApp('/detections/123', async (u) => {
      const url = String(u)
      calls.push(url)

      if (url.includes('/auth/me')) {
        return j({
          id: '1',
          username: 'operator',
          display_name: 'Operator',
          role: 'OPERATOR',
          active: true,
        })
      }

      if (url.includes('/alpr/detections/123')) {
        return j({
          id: '123',
          status: 'PENDING',
          created_at: '2026-10-08T00:00:00Z',
        })
      }

      return j({})
    })

    expect(
      await screen.findByRole('button', { name: 'Raw Data' }),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole('button', { name: 'Audit' }),
    ).not.toBeInTheDocument()

    expect(
      calls.some((url) => url.includes('/audit-logs')),
    ).toBe(false)
  })

  it('SYSTEM_ADMIN can access /admin/lanes', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    renderApp('/admin/lanes', async (u) => {
      const s = String(u)

      if (s.includes('/auth/me')) {
        return j({
          id: '1',
          username: 'admin',
          display_name: 'Admin',
          role: 'SYSTEM_ADMIN',
          active: true,
        })
      }

      if (s.includes('/lanes')) {
        return j([])
      }

      if (s.includes('/health/ready')) {
        return j({
          status: 'ready',
          alpr: {
            ready: true,
            provider: 'real',
          },
        })
      }

      return j({})
    })

    await waitFor(() =>
      expect(
        screen.getByText(/Quản lý làn/i),
      ).toBeInTheDocument(),
    )
  })

  it('BUILDING_ADMIN can access user management without a false 403', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderApp('/admin/users', async (u) => {
      const url = String(u)
      if (url.includes('/auth/me')) return j({ id: '1', username: 'ba', display_name: 'Building admin', role: 'BUILDING_ADMIN', building_id: 'b1', active: true })
      if (url.includes('/users')) return j([])
      return j({})
    })
    expect(await screen.findByText(/User Management/i)).toBeInTheDocument()
    expect(screen.queryByText(/403/)).not.toBeInTheDocument()
  })

  it('forced-password users are redirected before the application shell loads', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    const calls: string[] = []
    renderApp('/admin/dashboard', async (u) => {
      const url = String(u)
      calls.push(url)
      if (url.includes('/auth/me')) return j({ id: '1', username: 'ba', display_name: 'Building admin', role: 'BUILDING_ADMIN', active: true, must_change_password: true })
      return j({})
    })
    expect(await screen.findByRole('heading', { name: /Đổi mật khẩu/i })).toBeInTheDocument()
    expect(calls.some((url) => url.includes('/health/ready'))).toBe(false)
  })

  it('root / redirects OPERATOR to /station', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    renderApp('/', async (u) => {
      const s = String(u)

      if (s.includes('/auth/me')) {
        return j({
          id: '1',
          username: 'op',
          display_name: 'Op',
          role: 'OPERATOR',
          active: true,
        })
      }

      if (s.includes('/lanes/active')) {
        return j([])
      }

      if (s.includes('/parking/transactions')) {
        return j([])
      }

      if (s.includes('/health/ready')) {
        return j({
          status: 'ready',
          alpr: {
            provider: 'real',
          },
        })
      }

      return j({})
    })

    expect(
      await screen.findByRole('heading', { name: /Trạm quét biển số/i, timeout: 10000 }),
    ).toBeInTheDocument()
  })
})
