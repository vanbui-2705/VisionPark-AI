import { describe, it, expect } from 'vitest'
import { can } from '../../src/lib/permissions.ts'
import type { CurrentUser } from '../../src/api/types.ts'

const operator: CurrentUser = {
  id: 'op-1',
  username: 'operator',
  display_name: 'Operator',
  role: 'OPERATOR',
  active: true,
}

const admin: CurrentUser = {
  id: 'admin-1',
  username: 'admin',
  display_name: 'Admin',
  role: 'ADMIN',
  active: true,
}

describe('Operations permissions', () => {
  it('allows OPERATOR to read parking transactions', () => {
    expect(can(operator, 'transactions.read')).toBe(true)
  })

  it('allows ADMIN to read parking transactions', () => {
    expect(can(admin, 'transactions.read')).toBe(true)
  })

  it('does not allow OPERATOR to read audit logs', () => {
    expect(can(operator, 'audit.read')).toBe(false)
  })

  it('allows ADMIN to read audit logs', () => {
    expect(can(admin, 'audit.read')).toBe(true)
  })
})