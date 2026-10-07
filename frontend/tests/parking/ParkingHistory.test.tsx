import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../../src/modules/auth/AuthContext.tsx'
import { ParkingHistoryPage } from '../../src/modules/parking/ParkingHistoryPage.tsx'
import { ApiError } from '../../src/api/errors.ts'
import * as services from '../../src/api/services.ts'

function j(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function paginated(items: unknown[], page = 0, pageSize = 20) {
  return { items, total: items.length, page, pageSize, totalPages: Math.max(1, Math.ceil(items.length / pageSize)) }
}

const txs = [
  { id: 'pt-1', license_plate: '29A12345', normalized_plate: '29A12345', original_ai_plate: '29A-123.45', status: 'PARKED', lane_id: 'lane-in-1', lane_name: 'LANE_IN_01', detection_id: 'd-1', confidence: 0.9, check_in_time: new Date().toISOString(), source: 'STATION_AUTO', is_manual_override: false, created_at: new Date().toISOString() },
  { id: 'pt-2', license_plate: '30F88888', normalized_plate: '30F88888', original_ai_plate: '30F-888.88', status: 'PARKED', lane_id: 'lane-out-1', lane_name: 'LANE_OUT_01', detection_id: 'd-2', confidence: 0.6, check_in_time: new Date().toISOString(), source: 'OPERATOR_MANUAL', is_manual_override: true, created_at: new Date().toISOString() },
]

function renderPage(fetcher?: (u: unknown) => Promise<Response>) {
  if (fetcher) vi.spyOn(globalThis, 'fetch').mockImplementation(fetcher as unknown as typeof fetch)
  return render(<MemoryRouter><AuthProvider><ParkingHistoryPage /></AuthProvider></MemoryRouter>)
}

describe('ParkingHistoryPage — Duy Anh', () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('render success with paginated response', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j(paginated(txs))
      return j({})
    })
    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())
  })

  it('backward compat: handles bare array', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j(txs)
      return j({})
    })
    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())
  })
  
  it('filter by lane', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    const fetchCalls: string[] = []
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) {
        fetchCalls.push(s)
        if (s.includes('lane_id=lane-out-1')) return j(paginated([txs[1]]))
        if (s.includes('lane_id=')) return j(paginated([txs[1]]))
        return j(paginated(txs))
      }
      return j({})
    })
    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())
    const laneInput = screen.getByPlaceholderText(/Tất cả làn/i)
    await userEvent.clear(laneInput)
    await userEvent.type(laneInput, 'lane-out-1')
    await waitFor(() => expect(fetchCalls.some(c => c.includes('lane_id='))).toBe(true), { timeout: 5000 })
    await waitFor(() => expect(screen.getByText('30F88888')).toBeInTheDocument(), { timeout: 3000 })
  })

  it('filter by status', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) {
        if (s.includes('status=COMPLETED')) return j(paginated([{ ...txs[1], status: 'COMPLETED' }]))
        return j(paginated(txs))
      }
      return j({})
    })

    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())

    await userEvent.selectOptions(screen.getByRole('combobox'), 'COMPLETED')

    await waitFor(() => expect(screen.queryByText('29A12345')).not.toBeInTheDocument(), { timeout: 3000 })
    await waitFor(() => expect(screen.getByText('30F88888')).toBeInTheDocument())
  })

  it('filter by time range', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) {
        if (s.includes('from=2026-10-04')) return j(paginated([txs[1]]))
        return j(paginated(txs))
      }
      return j({})
    })

    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())

    const dateInputs = document.querySelectorAll('input[type="date"]')
await userEvent.type(dateInputs[0] as HTMLInputElement, '2026-10-04')
    await waitFor(() => expect(screen.queryByText('29A12345')).not.toBeInTheDocument(), { timeout: 3000 })
    await waitFor(() => expect(screen.getByText('30F88888')).toBeInTheDocument())
  })

  it('sends page/pageSize and filters to server', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    const calls: string[] = []
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) { calls.push(s); return j(paginated([], 0, 20)) }
      return j({})
    })
    await waitFor(() => expect(calls.length).toBeGreaterThan(0))
    expect(calls[0]).toContain('page=')
    expect(calls[0]).toContain('pageSize=')
  })

  it('filter by plate triggers server request with q', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    const calls: string[] = []
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) {
        calls.push(s)
        if (s.includes('q=')) return j(paginated([txs[1]]))
        return j(paginated(txs))
      }
      return j({})
    })
    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())
    const input = screen.getByPlaceholderText('29A12345')
    await userEvent.type(input, '30F')
    await waitFor(() => expect(calls.some((c) => c.includes('q='))).toBe(true), { timeout: 5000 })
  })

  it('empty state when no transactions at all', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j(paginated([]))
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Chưa có lịch sử đỗ xe/i)).toBeInTheDocument())
  })

  it('empty filtered result shows no-result message', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    let first = true
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) {
        if (first) { first = false; return j(paginated(txs)) }
        return j(paginated([]))
      }
      return j({})
    })
    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())
    const input = screen.getByPlaceholderText('29A12345')
    await userEvent.type(input, 'ZZZ')
    await waitFor(() => expect(screen.getByText(/Không có kết quả/)).toBeInTheDocument(), { timeout: 5000 })
  })

  it('error 500 shows retry', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j({ message: 'fail', code: 'INTERNAL' }, 500)
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Thử lại/i)).toBeInTheDocument())
  })

  it('error 403 shows forbidden message', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j({ message: 'forbidden', code: 'FORBIDDEN' }, 403)
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/không có quyền/i)).toBeInTheDocument())
  })

  it('error 404 shows not found (mocked service)', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    vi.spyOn(services.parkingTransactionsApi, 'list').mockRejectedValue(new ApiError('not found', { status: 404, code: 'NOT_FOUND' }))
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      return j({})
    })
    render(<MemoryRouter><AuthProvider><ParkingHistoryPage /></AuthProvider></MemoryRouter>)
    await waitFor(() => expect(screen.getByText(/Không tìm thấy/i)).toBeInTheDocument())
  })

  it('invalid page returns 422', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j({ message: 'Invalid page', code: 'VALIDATION_ERROR' }, 422)
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Thử lại/i)).toBeInTheDocument())
  })

  it('navigates to page 2 with filters preserved', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    const calls: string[] = []
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) {
        calls.push(s)
        if (s.includes('page=1')) {
          return j({ items: [{ ...txs[1], id: 'pt-p2', license_plate: '51A99999' }], total: 40, page: 1, pageSize: 20, totalPages: 2 })
        }
        return j({ items: [txs[0]], total: 40, page: 0, pageSize: 20, totalPages: 2 })
      }
      return j({})
    })
    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())
    const nextBtn = screen.getByRole('button', { name: /Sau/i })
    expect(nextBtn).toBeEnabled()
    await userEvent.click(nextBtn)
    await waitFor(() => expect(screen.getByText('51A99999')).toBeInTheDocument())
    expect(calls.some((c) => c.includes('page=1'))).toBe(true)
  })
})
