import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuditLogsPage } from '../../src/modules/audit/AuditLogsPage.tsx'

const auditRecord = {
  id: 'audit-1',
  time: '2026-10-07T10:00:00Z',
  actor: 'operator',
  action: 'CREATE_CHECKIN',
  resource: 'ParkingTransaction',
  resource_id: 'transaction-1',
  source: null,
  before: null,
  after: {
    lane_id: 'lane-1',
    ai_plate: '30A12345',
    final_plate: '30A12346',
    source: 'OPERATOR_CORRECTED',
    actor_id: 'operator-1',
    detection_id: 'detection-1',
  },
  correlation_id: 'corr-1',
}

describe('Audit details', () => {
  beforeEach(() => {
    vi.restoreAllMocks()

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([auditRecord]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })

  it('shows AI plate, final plate, actor, source and timestamp', async () => {
    const user = userEvent.setup()

    render(<AuditLogsPage />)

    await waitFor(() => {
      expect(screen.getByText('CREATE_CHECKIN')).toBeInTheDocument()
    })

    expect(screen.getByText('operator')).toBeInTheDocument()
    expect(
  screen.getByText(new Date(auditRecord.time).toLocaleString('vi-VN')),
).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /chi tiết/i }))

    expect(screen.getByText('30A12345')).toBeInTheDocument()
    expect(screen.getByText('30A12346')).toBeInTheDocument()
    expect(screen.getByText('OPERATOR_CORRECTED')).toBeInTheDocument()
  })
})