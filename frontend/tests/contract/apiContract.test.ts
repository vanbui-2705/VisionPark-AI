import { describe, it, expect } from 'vitest'
import type { PaginatedResponse, ParkingTransaction, ManagedUser } from '../../src/api/domain.ts'
import { can, PERMISSION_MATRIX } from '../../src/lib/permissions.ts'
import type { CurrentUser } from '../../src/api/types.ts'

describe('API Contract Tests — VisionPark Phase 2', () => {
  it('validates PaginatedResponse contract shape', () => {
    const samplePagination: PaginatedResponse<ParkingTransaction> = {
      items: [],
      total: 0,
      page: 0,
      pageSize: 20,
      totalPages: 1,
    }
    expect(samplePagination).toHaveProperty('items')
    expect(samplePagination).toHaveProperty('total')
    expect(samplePagination).toHaveProperty('page')
    expect(samplePagination).toHaveProperty('pageSize')
    expect(samplePagination).toHaveProperty('totalPages')
    expect(Array.isArray(samplePagination.items)).toBe(true)
    expect(typeof samplePagination.total).toBe('number')
  })

  it('validates ManagedUser contract contains 4 allowed roles and active flag', () => {
    const roles: ManagedUser['role'][] = ['ADMIN', 'OPERATOR', 'ACCOUNTANT', 'TECHNICIAN']
    roles.forEach((r) => {
      const u: ManagedUser = {
        id: 'u-1',
        username: 'test',
        display_name: 'Test',
        role: r,
        active: true,
      }
      expect(u.role).toBe(r)
      expect(typeof u.active).toBe('boolean')
    })
  })

  it('validates permission matrix covers 4 roles for every permission', () => {
    PERMISSION_MATRIX.forEach((entry) => {
      expect(entry).toHaveProperty('perm')
      expect(entry).toHaveProperty('label')
      expect(typeof entry.admin).toBe('boolean')
      expect(typeof entry.operator).toBe('boolean')
      expect(typeof entry.accountant).toBe('boolean')
      expect(typeof entry.technician).toBe('boolean')
    })
  })

  it('validates can() evaluation across all 4 roles', () => {
    const makeUser = (role: 'ADMIN' | 'OPERATOR' | 'ACCOUNTANT' | 'TECHNICIAN'): CurrentUser => ({
      id: '1',
      username: 'u',
      display_name: 'U',
      role,
      active: true,
    })

    // ADMIN has full access
    expect(can(makeUser('ADMIN'), 'dashboard.read')).toBe(true)
    expect(can(makeUser('ADMIN'), 'users.manage')).toBe(true)

    // OPERATOR has operations access, no users.manage
    expect(can(makeUser('OPERATOR'), 'station.use')).toBe(true)
    expect(can(makeUser('OPERATOR'), 'users.manage')).toBe(false)

    // ACCOUNTANT has dashboard & transactions & audit, no lanes.create
    expect(can(makeUser('ACCOUNTANT'), 'dashboard.read')).toBe(true)
    expect(can(makeUser('ACCOUNTANT'), 'transactions.read')).toBe(true)
    expect(can(makeUser('ACCOUNTANT'), 'lanes.create')).toBe(false)

    // TECHNICIAN has station, lanes, system health, no dashboard
    expect(can(makeUser('TECHNICIAN'), 'station.use')).toBe(true)
    expect(can(makeUser('TECHNICIAN'), 'system.read')).toBe(true)
    expect(can(makeUser('TECHNICIAN'), 'dashboard.read')).toBe(false)
  })
})
