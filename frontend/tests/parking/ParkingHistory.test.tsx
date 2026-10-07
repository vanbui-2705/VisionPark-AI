import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../../src/modules/auth/AuthContext.tsx'
import { ParkingHistoryPage } from '../../src/modules/parking/ParkingHistoryPage.tsx'

function j(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
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

  it('render success', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j(txs)
      return j({})
    })
    await waitFor(() => expect(screen.getAllByText(/Lịch sử đỗ xe/i).length).toBeGreaterThan(0))
    expect(screen.getByText('29A12345')).toBeInTheDocument()
  })

  it('filter by plate', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j(txs)
      return j({})
    })
    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())
    const input = screen.getByPlaceholderText('29A12345')
    await userEvent.type(input, '30F')
    expect(screen.queryByText('29A12345')).not.toBeInTheDocument()
    expect(screen.getByText('30F88888')).toBeInTheDocument()
  })
  
  it('filter by lane', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j(txs)
      return j({})
    })

    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())

    const laneInput = screen.getByPlaceholderText('ALL')
    await userEvent.type(laneInput, 'lane-out-1')

    expect(screen.queryByText('29A12345')).not.toBeInTheDocument()
    expect(screen.getByText('30F88888')).toBeInTheDocument()
  })

  it('filter by status', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) {
        return j([
          txs[0],
          { ...txs[1], status: 'COMPLETED' },
        ])
      }
      return j({})
    })

    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())

    await userEvent.selectOptions(screen.getByRole('combobox'), 'COMPLETED')

    expect(screen.queryByText('29A12345')).not.toBeInTheDocument()
    expect(screen.getByText('30F88888')).toBeInTheDocument()
  })

  it('filter by time range', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')

    const datedTxs = [
      { ...txs[0], check_in_time: '2026-10-01T10:00:00' },
      { ...txs[1], check_in_time: '2026-10-05T10:00:00' },
    ]

    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j(datedTxs)
      return j({})
    })

    await waitFor(() => expect(screen.getByText('29A12345')).toBeInTheDocument())

    const dateInputs = document.querySelectorAll('input[type="date"]')
await userEvent.type(dateInputs[0] as HTMLInputElement, '2026-10-04')

    expect(screen.queryByText('29A12345')).not.toBeInTheDocument()
    expect(screen.getByText('30F88888')).toBeInTheDocument()
  })

  it('empty state', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j([])
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Chưa có lịch sử đỗ xe/i)).toBeInTheDocument())
  })

  it('error state with retry', async () => {
    localStorage.setItem('visionpark.access_token', 'tok')
    renderPage(async (u) => {
      const s = String(u)
      if (s.includes('/auth/me')) return j({ id: '1', username: 'duyanh', display_name: 'Duy Anh', role: 'OPERATOR', active: true })
      if (s.includes('/parking/transactions')) return j({ message: 'fail' }, 500)
      return j({})
    })
    await waitFor(() => expect(screen.getByText(/Thử lại/i)).toBeInTheDocument())
  })
})
