import { describe, it, expect } from 'vitest'
import { can } from '../../src/lib/permissions.ts'

describe('can()', () => {
  it('ADMIN has audit.read', () => expect(can({ id: '1', username: 'a', display_name: 'A', role: 'ADMIN', active: true } as never, 'audit.read')).toBe(true))
  it('OPERATOR denied audit.read', () => expect(can({ id: '2', username: 'o', display_name: 'O', role: 'OPERATOR', active: true } as never, 'audit.read')).toBe(false))
  it('OPERATOR allowed transactions.read', () => expect(can({ id: '2', username: 'o', display_name: 'O', role: 'OPERATOR', active: true } as never, 'transactions.read')).toBe(true))
  it('null user denied', () => expect(can(null, 'audit.read')).toBe(false))
})
