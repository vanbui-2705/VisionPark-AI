import { describe, it, expect } from 'vitest'
import { can } from '../../src/lib/permissions.ts'

describe('can()', () => {
  it('ADMIN has audit.read', () => expect(can({ id: '1', username: 'a', display_name: 'A', role: 'ADMIN', active: true } as never, 'audit.read')).toBe(true))
  it('OPERATOR denied audit.read', () => expect(can({ id: '2', username: 'o', display_name: 'O', role: 'OPERATOR', active: true } as never, 'audit.read')).toBe(false))
  it('OPERATOR allowed transactions.read', () => expect(can({ id: '2', username: 'o', display_name: 'O', role: 'OPERATOR', active: true } as never, 'transactions.read')).toBe(true))
  it('null user denied', () => expect(can(null, 'audit.read')).toBe(false))
})

describe('mock pagination boundaries', () => {
  it('paginate validates', async () => {
    const { mockApi } = await import('../../src/api/mocks/fixtures.ts')
    await expect(mockApi.auditList({ page: -1, pageSize: 20 } as never)).rejects.toMatchObject({ status: 422 })
    await expect(mockApi.auditList({ page: 0, pageSize: 0 } as never)).rejects.toMatchObject({ status: 422 })
    await expect(mockApi.auditList({ page: 0, pageSize: 101 } as never)).rejects.toMatchObject({ status: 422 })
    const r = await mockApi.parkingTransactionsList({ page: 999, pageSize: 20 } as never)
    expect(r.items.length).toBe(0)
    expect(r.totalPages).toBeGreaterThanOrEqual(1)
  })
  it('audit filter + pagination', async () => {
    const { mockApi } = await import('../../src/api/mocks/fixtures.ts')
    const r = await mockApi.auditList({ actor: 'Duy Anh', page: 0, pageSize: 1 } as never)
    expect(r.items.length).toBeLessThanOrEqual(1)
    expect(r.total).toBeGreaterThanOrEqual(1)
  })
  it('combined filters', async () => {
    const { mockApi } = await import('../../src/api/mocks/fixtures.ts')
    const r = await mockApi.parkingTransactionsList({ q: '29A', lane_id: '1', status: 'PARKED', page: 0, pageSize: 20 } as never)
    expect(r.items.every((x) => x.lane_id === '1')).toBe(true)
  })
})
