import { describe, it, expect } from 'vitest'
import { can } from '../../src/lib/permissions.ts'

describe('can()', () => {
  it('SYSTEM_ADMIN has audit.read', () => expect(can({ id: '1', username: 'a', display_name: 'A', role: 'SYSTEM_ADMIN', active: true } as never, 'audit.read')).toBe(true))
  it('OPERATOR denied audit.read', () => expect(can({ id: '2', username: 'o', display_name: 'O', role: 'OPERATOR', active: true } as never, 'audit.read')).toBe(false))
  it('OPERATOR allowed transactions.read', () => expect(can({ id: '2', username: 'o', display_name: 'O', role: 'OPERATOR', active: true } as never, 'transactions.read')).toBe(true))
  it('SYSTEM_ADMIN does not mutate building lanes', () => expect(can({ id: '1', username: 'a', display_name: 'A', role: 'SYSTEM_ADMIN', active: true } as never, 'lanes.manage')).toBe(false))
  it('BUILDING_ADMIN manages lanes and users', () => {
    const user = { id: '3', username: 'ba', display_name: 'BA', role: 'BUILDING_ADMIN', active: true } as never
    expect(can(user, 'lanes.manage')).toBe(true)
    expect(can(user, 'users.manage')).toBe(true)
  })
  it('null user denied', () => expect(can(null, 'audit.read')).toBe(false))
})
