import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MonthlyTickets } from '../../src/modules/settings/MonthlyTickets.tsx'

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json' },
})

afterEach(() => { cleanup(); vi.restoreAllMocks(); localStorage.clear() })

describe('MonthlyTickets', () => {
  it('uses managed classes/zones and renews after the previous inclusive end time', async () => {
    const submitted: Record<string, unknown>[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.endsWith('/pricing/ticket-products')) return json([
        { id: 'monthly-bike', code: 'MB', name: 'Vé tháng xe máy', kind: 'MONTHLY', vehicle_type: 'MOTORBIKE', customer_class_id: 'class-1', active: true },
        { id: 'monthly-car', code: 'MC', name: 'Vé tháng ô tô', kind: 'MONTHLY', vehicle_type: 'CAR', customer_class_id: null, active: true },
      ])
      if (url.endsWith('/tickets/vehicles')) return json([
        { id: 'vehicle-1', normalized_plate: '30A12345', ticket_code: null, vehicle_type: 'MOTORBIKE', customer_class_id: 'class-1' },
      ])
      if (url.endsWith('/tickets/subscriptions') && init?.method === 'POST') {
        submitted.push(JSON.parse(String(init.body)))
        return json({ id: 'sub-2' }, 201)
      }
      if (url.endsWith('/tickets/subscriptions')) return json([
        { id: 'sub-1', product_id: 'monthly-bike', vehicle_id: 'vehicle-1', zone_id: 'zone-1', valid_from: '2098-12-01T00:00:00.000Z', valid_until: '2099-01-01T00:00:00.000Z', grace_days: 3 },
      ])
      if (url.endsWith('/pricing/customer-classes')) return json([
        { id: 'class-1', code: 'RESIDENT', name: 'Cư dân', active: true },
      ])
      if (url.endsWith('/tickets/zones')) return json([
        { id: 'zone-1', code: 'A', name: 'Tầng hầm A', active: true },
      ])
      throw new Error(`Unexpected request: ${url}`)
    })

    const user = userEvent.setup()
    render(<MonthlyTickets />)

    expect(await screen.findByRole('option', { name: 'Cư dân (RESIDENT)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Tầng hầm A (A)' })).toBeInTheDocument()
    expect(screen.queryByText(/UUID/)).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Vé tháng ô tô' })).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Biển số xe'), '30A-123.45')
    await user.click(screen.getByRole('button', { name: 'Đăng ký / gia hạn' }))

    await waitFor(() => expect(submitted).toHaveLength(1))
    expect(submitted[0]).toMatchObject({
      product_id: 'monthly-bike',
      vehicle_id: 'vehicle-1',
      zone_id: 'zone-1',
      valid_from: '2099-01-01T00:00:00.001Z',
    })
    expect(new Date(String(submitted[0].valid_until)).getTime()).toBeGreaterThan(new Date(String(submitted[0].valid_from)).getTime())
  })
})
