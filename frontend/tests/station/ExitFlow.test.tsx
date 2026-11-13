import { createRef } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import StationPage from '../../src/modules/station/StationPage'
import ExitSummary from '../../src/modules/station/components/ExitSummary'
import ImageComparison from '../../src/modules/station/components/ImageComparison'
import { useStationShortcuts } from '../../src/modules/station/hooks/useStationShortcuts'
import { AuthContext, type AuthContextValue } from '../../src/modules/auth/AuthContext'
import { can } from '../../src/lib/permissions'
import type { ExitSession } from '../../src/modules/station/api'

const session = {
  session_id: 'parked', license_plate: '29A12345', ticket_code: null,
  check_in_time: '2026-11-01T00:00:00Z', check_in_image_url: 'data:image/png;base64,AA==',
  laneId: 'out', exit_time: '2026-11-02T01:30:45Z', exit_image_url: 'data:image/png;base64,AQ==',
  duration_minutes: 1530, fee: 17000, status: 'PARKED', vehicle_type_mismatch: false, message: '',
} as ExitSession
const response = (body: unknown) => new Response(JSON.stringify(body))
const completed = { transaction: { id: 'parked', exit_lane_id: 'out', exit_time: '2026-11-02T01:31:00Z' }, fee: 17000, status: 'COMPLETED', barrier_opened: true, message: 'Done' }
const user = { id: 'operator', username: 'operator', display_name: 'Operator', active: true, building_id: 'building', role: 'OPERATOR' as const }
const auth = { user, initialized: true, isAuthenticated: true, loading: false } as AuthContextValue
const summaryProps = { onBusyChange: vi.fn(), onCompleted: vi.fn(), onNext: vi.fn(), onRequireExitImage: vi.fn() }

function confirmCheckout() {
  fireEvent.click(screen.getByRole('button', { name: /Xác nhận thu tiền/ }))
  fireEvent.click(screen.getByRole('button', { name: /Xác nhận đã thu/ }))
}

beforeEach(() => { localStorage.clear() })
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Station OUT flow', () => {
  it('runs OUT preview, cash, gate and next vehicle, then preserves manual IN', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const path = String(url)
      if (path.includes('/lanes/active')) return response([
        { id: 'in', name: 'Entry', direction: 'IN', is_active: true, building_id: 'building' },
        { id: 'out', name: 'Exit', direction: 'OUT', is_active: true, building_id: 'building' },
      ])
      if (path.includes('/customer-classes')) return response([{ id: 'class', name: 'Visitor' }])
      if (path.endsWith('/check-out/preview')) return response(session)
      if (path.endsWith('/check-out')) return response(completed)
      if (path.endsWith('/check-in')) return response({ transaction: { id: 'new-entry' } })
      return response([])
    })
    render(<AuthContext.Provider value={auth}><StationPage /></AuthContext.Provider>)
    await screen.findByRole('option', { name: 'Exit - OUT' })
    fireEvent.change(screen.getByLabelText('Lane'), { target: { value: 'out' } })
    fireEvent.change(screen.getByLabelText('Biển số nhập tay'), { target: { value: '29A12345' } })
    fireEvent.click(screen.getByRole('button', { name: 'Tra xe và tính phí' }))
    await screen.findByRole('region', { name: 'Thông tin xe ra' })
    expect(screen.getByText(/Chờ đối chiếu và xác nhận checkout/)).toBeInTheDocument()
    expect(screen.queryByText(/OUT · SUCCESS/)).not.toBeInTheDocument()
    expect(screen.getByText('1 ngày 1 giờ 30 phút')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mở cổng (F10)' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('img')).toHaveLength(2)
    fireEvent.keyDown(window, { key: 'F8' })
    expect(screen.getByRole('dialog', { name: 'Thu tiền và mở cổng' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Xác nhận đã thu/ }))
    await screen.findByText('Backend đã xác nhận checkout và ghi nhận mở barrier mô phỏng.')
    fireEvent.keyDown(window, { key: 'F9' })
    expect(screen.queryByRole('region', { name: 'Thông tin xe ra' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Lane'), { target: { value: 'in' } })
    await screen.findByRole('option', { name: 'Visitor' })
    fireEvent.change(screen.getByLabelText('Biển số nhập tay'), { target: { value: '30A11111' } })
    fireEvent.click(screen.getByRole('button', { name: 'Tạo check-in' }))
    await screen.findByText('new-entry')
    const request = fetch.mock.calls.find(([url]) => String(url).endsWith('/check-in'))!
    expect(JSON.parse(String(request[1]?.body))).toMatchObject({ lane_id: 'in', license_plate: '30A11111', customer_class_id: 'class' })
  })

  it('blocks duplicate cash requests and retries the same checkout after an unacknowledged response', async () => {
    let finish!: (value: Response) => void
    const fetch = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
      .mockResolvedValueOnce(response(completed))
    const done = vi.fn()
    const busy = vi.fn()
    render(<ExitSummary session={session} onBusyChange={busy} onCompleted={done} onNext={vi.fn()} onRequireExitImage={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Xác nhận thu tiền/ }))
    const confirm = screen.getByRole('button', { name: /Xác nhận đã thu/ })
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(confirm)
    fireEvent.click(confirm)
    expect(fetch).toHaveBeenCalledTimes(1)
    await act(async () => finish(response({ ...completed, barrier_opened: false })))
    await screen.findByRole('alert')
    expect(done).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /Xác nhận đã thu/ }))
    await waitFor(() => expect(done).toHaveBeenCalledOnce())
    expect(fetch.mock.calls[0][1]?.headers).toEqual(fetch.mock.calls[1][1]?.headers)
    expect(busy).toHaveBeenLastCalledWith(false)
  })

  it('rejects mismatched fees and resumes a paid session without sending CASH', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({ ...completed, fee: 1 }))
    const { rerender } = render(<ExitSummary session={session} {...summaryProps} />)
    confirmCheckout()
    await screen.findByRole('alert')
    expect(screen.queryByText(/Backend đã xác nhận checkout/)).not.toBeInTheDocument()
    rerender(<ExitSummary key="paid" session={{ ...session, status: 'PAID' }} {...summaryProps} />)
    expect(screen.getByRole('button', { name: /Mở cổng/ })).toBeEnabled()
    fetch.mockResolvedValueOnce(response(completed))
    fireEvent.click(screen.getByRole('button', { name: /Mở cổng/ }))
    fireEvent.click(screen.getByRole('button', { name: /Xác nhận mở cổng/ }))
    await screen.findByText(/Backend đã xác nhận checkout/)
    expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).not.toHaveProperty('payment_method')
  })

  it('requires reviewing the refreshed fee after a tariff boundary and handles network failure', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new TypeError('offline'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ code: 'FEE_CHANGED', message: 'Phí đã thay đổi' }), { status: 409 }))
      .mockResolvedValueOnce(response({ ...session, fee: 18000 }))
      .mockResolvedValueOnce(response({ ...completed, fee: 18000 }))
    render(<ExitSummary session={session} {...summaryProps} />)
    confirmCheckout()
    await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button', { name: /Xác nhận đã thu/ }))
    await screen.findByRole('button', { name: 'Cập nhật phí' })
    expect(screen.getByRole('button', { name: /Xác nhận thu tiền/ })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cập nhật phí' }))
    await waitFor(() => expect(screen.getByRole('button', { name: /Xác nhận thu tiền/ })).toBeEnabled())
    expect(fetch).toHaveBeenCalledTimes(3)
    confirmCheckout()
    await screen.findByText(/Backend đã xác nhận checkout/)
    expect(JSON.parse(String(fetch.mock.calls[3][1]?.body)).expected_fee).toBe(18000)
  })

  it('shows missing photos explicitly and restricts checkout permission', () => {
    render(<ImageComparison plate="29A12345" />)
    expect(screen.getByText(/Không có ảnh lúc vào/)).toBeInTheDocument()
    expect(screen.getByText(/Chưa có ảnh lúc ra/)).toBeInTheDocument()
    for (const role of ['TECHNICIAN', 'ACCOUNTANT'] as const) expect(can({ ...user, role }, 'checkout.create')).toBe(false)
    expect(can(user, 'checkout.create')).toBe(true)
    expect(can({ ...user, role: 'BUILDING_ADMIN' }, 'checkout.create')).toBe(true)
    expect(can({ ...user, role: 'SYSTEM_ADMIN' }, 'checkout.create')).toBe(true)
  })

  it('blocks checkout without an exit image and explains how to continue', () => {
    const requireImage = vi.fn()
    render(<ExitSummary session={{ ...session, exit_image_url: null }} {...summaryProps} onRequireExitImage={requireImage} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Chưa có ảnh xe ra')
    expect(screen.getByRole('button', { name: /Xác nhận thu tiền/ })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Chụp hoặc chọn ảnh xe ra' }))
    expect(requireImage).toHaveBeenCalledOnce()
  })

  it('blocks checkout when the detected vehicle type does not match', () => {
    render(<ExitSummary session={{ ...session, vehicle_type_mismatch: true }} {...summaryProps} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Loại xe không khớp')
    expect(screen.getByRole('button', { name: /Xác nhận thu tiền/ })).toBeDisabled()
  })
})

describe('Station shortcuts', () => {
  it('uses active buttons and ignores text editing, dialogs, repeats, modifiers and unmount', () => {
    const click = vi.fn()
    const root = createRef<HTMLElement>()
    function Controls() {
      useStationShortcuts(root)
      return <section ref={root}><input aria-label="plate" /><div contentEditable data-testid="editor" />
        <button data-station-shortcut="capture" onClick={click}>Capture</button>
        <button data-station-shortcut="cash" disabled onClick={click}>Cash</button>
      </section>
    }
    const { unmount } = render(<Controls />)
    fireEvent.keyDown(window, { key: 'F2' })
    expect(click).toHaveBeenCalledOnce()
    fireEvent.keyDown(screen.getByLabelText('plate'), { key: 'F2' })
    fireEvent.keyDown(screen.getByTestId('editor'), { key: 'F2' })
    fireEvent.keyDown(window, { key: 'F2', repeat: true })
    fireEvent.keyDown(window, { key: 'F2', ctrlKey: true })
    fireEvent.keyDown(window, { key: 'F8' })
    const dialog = document.createElement('dialog'); dialog.open = true; document.body.append(dialog)
    fireEvent.keyDown(window, { key: 'F2' }); dialog.remove()
    expect(click).toHaveBeenCalledOnce()
    unmount()
    fireEvent.keyDown(window, { key: 'F2' })
    expect(click).toHaveBeenCalledOnce()
  })
})
