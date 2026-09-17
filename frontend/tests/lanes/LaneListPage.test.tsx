import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../../src/modules/auth/AuthContext.tsx'
import { LaneListPage } from '../../src/modules/lanes/LaneListPage.tsx'

function j(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const ADMIN = { id: '1', username: 'admin', display_name: 'Admin', role: 'ADMIN', active: true }

function mockFetch(handler: (url: string, init?: RequestInit) => Response) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: string | URL | Request, init?: RequestInit) =>
    handler(String(url), init),
  )
}

function renderLanes() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <LaneListPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LaneListPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    localStorage.setItem('visionpark.access_token', 'tok')
  })

  it('renders empty state when no lanes', async () => {
    mockFetch((u) => (u.includes('/auth/me') ? j(ADMIN) : u.includes('/lanes') ? j([]) : j({})))
    renderLanes()
    expect(await screen.findByText(/Chưa có làn nào/i)).toBeInTheDocument()
  })

  it('renders error state with retry', async () => {
    mockFetch((u) => (u.includes('/auth/me') ? j(ADMIN) : u.includes('/lanes') ? j({ code: 'X', message: 'Lỗi server' }, 500) : j({})))
    renderLanes()
    expect(await screen.findByText(/Lỗi server/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Thử lại/i })).toBeInTheDocument()
  })

  it('filters by direction', async () => {
    mockFetch((u) =>
      u.includes('/auth/me')
        ? j(ADMIN)
        : u.includes('/lanes')
          ? j([
              { id: '1', name: 'LANE_IN_01', direction: 'IN', active: true },
              { id: '2', name: 'LANE_OUT_01', direction: 'OUT', active: false },
            ])
          : j({}),
    )
    renderLanes()
    expect(await screen.findByText('LANE_IN_01')).toBeInTheDocument()
    expect(screen.getByText('LANE_OUT_01')).toBeInTheDocument()

    const user = userEvent.setup()
    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'IN')
    expect(screen.getByText('LANE_IN_01')).toBeInTheDocument()
    expect(screen.queryByText('LANE_OUT_01')).not.toBeInTheDocument()
  })

  it('shows "Tên làn đã tồn tại" on 409 DUPLICATE_LANE_NAME', async () => {
    mockFetch((u, init) => {
      if (u.includes('/auth/me')) return j(ADMIN)
      if (u.endsWith('/api/v1/lanes') && init?.method === 'POST') return j({ code: 'DUPLICATE_LANE_NAME', message: 'exists' }, 409)
      if (u.includes('/lanes')) return j([])
      return j({})
    })
    renderLanes()
    expect(await screen.findByText(/Chưa có làn nào/i)).toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Tạo làn/i }))
    await user.type(screen.getByLabelText(/Tên làn/i), 'LANE_IN_01')
    await user.click(screen.getByRole('button', { name: /^Lưu$/i }))
    expect(await screen.findByText(/Tên làn đã tồn tại/i)).toBeInTheDocument()
  })

  it('inactive lane requires confirm then PATCH active=false', async () => {
    let patched: unknown = null
    mockFetch((u, init) => {
      if (u.includes('/auth/me')) return j(ADMIN)
      if (u.includes('/api/v1/lanes/1') && init?.method === 'PATCH') {
        patched = JSON.parse(String(init.body))
        return j({ id: '1', name: 'LANE_IN_01', direction: 'IN', active: false })
      }
      if (u.endsWith('/api/v1/lanes')) return j([{ id: '1', name: 'LANE_IN_01', direction: 'IN', active: true }])
      return j({})
    })
    renderLanes()
    expect(await screen.findByText('LANE_IN_01')).toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Ngưng hoạt động/i }))
    expect(await screen.findByText(/Bạn có chắc muốn ngưng hoạt động/i)).toBeInTheDocument()

    // list unchanged before confirming
    expect(screen.getAllByText('Active').length).toBeGreaterThan(0)

    await user.click(screen.getByRole('button', { name: /^Xác nhận$/i }))
    await waitFor(() => expect(patched).toEqual({ active: false }))
    await waitFor(() => expect(screen.getByText('Inactive')).toBeInTheDocument())
  })

  it('no DELETE request is ever issued', async () => {
    const spy = vi.fn()
    mockFetch((u, init) => {
      spy(init?.method)
      if (u.includes('/auth/me')) return j(ADMIN)
      if (u.includes('/lanes')) return j([{ id: '1', name: 'L1', direction: 'IN', active: true }])
      return j({})
    })
    renderLanes()
    expect(await screen.findByText('L1')).toBeInTheDocument()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Ngưng hoạt động/i }))
    await user.click(screen.getByRole('button', { name: /^Xác nhận$/i }))
    await waitFor(() => expect(spy).toHaveBeenCalledWith('PATCH'))
    expect(spy).not.toHaveBeenCalledWith('DELETE')
  })
})
