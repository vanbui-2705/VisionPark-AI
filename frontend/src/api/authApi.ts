import { apiClient } from './client.ts'
import type { CurrentUser } from './types.ts'

export interface LoginResponse {
  access_token: string
  token_type: string
  [k: string]: unknown
}

export function mapUser(raw: unknown): CurrentUser {
  const r = raw as Record<string, unknown>
  // handle role as object {name} or string
  let role = r.role as unknown
  if (role && typeof role === 'object') role = (role as Record<string, unknown>).name ?? (role as Record<string, unknown>).role
  const rawRole = String(role ?? '').toUpperCase()
  const roleStr = rawRole === 'ADMIN' ? 'SYSTEM_ADMIN' : rawRole
  const allowed = new Set(['SYSTEM_ADMIN', 'BUILDING_ADMIN', 'OPERATOR', 'ACCOUNTANT', 'TECHNICIAN'])
  return {
    id: String(r.id ?? r.user_id ?? ''),
    email: r.email as string | null | undefined,
    username: String(r.username ?? ''),
    display_name: String(r.display_name ?? r.displayName ?? r.name ?? r.username ?? ''),
    role: (allowed.has(roleStr) ? roleStr : 'OPERATOR') as CurrentUser['role'],
    building_id: typeof r.building_id === 'string' ? r.building_id : null,
    active: (r.is_active as boolean) ?? (r.active as boolean) ?? true,
  }
}

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    return apiClient.post<LoginResponse>('/api/v1/auth/login', { username, password })
  },
  async me(): Promise<CurrentUser> {
    const raw = await apiClient.get<unknown>('/api/v1/auth/me')
    return mapUser(raw)
  },
}
