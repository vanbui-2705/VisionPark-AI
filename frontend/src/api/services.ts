import { apiClient } from './client.ts'
import { ApiError } from './errors.ts'
import type { CurrentUser } from './types.ts'
import type { AuditLog, Detection, ManagedUser } from './domain.ts'

// ponytail: Phase 1 backend chưa có các endpoint dưới; interface đặt sẵn để Person 2/3 implement.
// Mock fixtures (src/api/mocks/fixtures.ts) chỉ dùng khi VITE_USE_MOCK_FIXTURES=true (dev/test).
// Blocker: P1-FE-USER-API blocked by Backend User Management API.
export interface UsersApi {
  list(params?: { q?: string; role?: string; active?: boolean }): Promise<ManagedUser[]>
  get(id: string): Promise<ManagedUser>
  create(payload: {
    username: string
    display_name: string
    email?: string | null
    password: string
    role: 'ADMIN' | 'OPERATOR'
    active?: boolean
  }): Promise<ManagedUser>
  patch(id: string, payload: Partial<ManagedUser & { password?: string }>): Promise<ManagedUser>
}

export interface DetectionsApi {
  list(params?: { lane_id?: string; direction?: string; status?: string; q?: string; limit?: number; from?: string; to?: string }): Promise<Detection[]>
  get(id: string): Promise<Detection>
  confirm(id: string, payload: { final_plate: string }): Promise<Detection>
}

export interface AuditApi {
  list(params?: { actor?: string; action?: string; from?: string; to?: string; limit?: number }): Promise<AuditLog[]>
}

export interface RolesApi {
  list(): Promise<{ name: string; display_name: string; description: string }[]>
}

function mockEnabled(): boolean {
  return import.meta.env.VITE_USE_MOCK_FIXTURES === 'true'
}

// Gọi API thật; nếu backend chưa có endpoint (404/501) và đang bật fixture mode -> trả mock + gắn cờ pending.
async function call<T>(key: string, real: () => Promise<T>): Promise<T> {
  try {
    return await real()
  } catch (e: unknown) {
    const pending = e instanceof ApiError && (e.status === 404 || e.status === 501 || e.code === 'NOT_FOUND')
    if (pending && mockEnabled()) {
      const mod = await import('./mocks/fixtures.ts')
      const impl = (mod.mockApi as unknown as Record<string, () => Promise<T>>)[key]
      if (impl) return impl()
    }
    throw e
  }
}

const realUsers: UsersApi = {
  list: (p) => apiClient.get<ManagedUser[]>('/api/v1/users', { params: p }),
  get: (id) => apiClient.get<ManagedUser>(`/api/v1/users/${id}`),
  create: (b) => apiClient.post<ManagedUser>('/api/v1/users', b),
  patch: (id, b) => apiClient.patch<ManagedUser>(`/api/v1/users/${id}`, b),
}

const realDetections: DetectionsApi = {
  list: (p) => apiClient.get<Detection[]>('/api/v1/detections', { params: p }),
  get: (id) => apiClient.get<Detection>(`/api/v1/detections/${id}`),
  confirm: (id, b) => apiClient.post<Detection>(`/api/v1/detections/${id}/confirm`, b),
}

const realAudit: AuditApi = {
  list: (p) => apiClient.get<AuditLog[]>('/api/v1/audit-logs', { params: p }),
}

const realRoles: RolesApi = {
  list: () => apiClient.get<{ name: string; display_name: string; description: string }[]>('/api/v1/roles'),
}

export const usersApi: UsersApi = {
  list: (p) => call('usersList', () => realUsers.list(p)),
  get: (id) => call('usersGet', () => realUsers.get(id)),
  create: (b) => call('usersCreate', () => realUsers.create(b)),
  patch: (id, b) => call('usersPatch', () => realUsers.patch(id, b)),
}

export const detectionsApi: DetectionsApi = {
  list: (p) => call('detectionsList', () => realDetections.list(p)),
  get: (id) => call('detectionsGet', () => realDetections.get(id)),
  confirm: (id, b) => call('detectionsConfirm', () => realDetections.confirm(id, b)),
}

export const auditApi: AuditApi = {
  list: (p) => call('auditList', () => realAudit.list(p)),
}

export const rolesApi: RolesApi = {
  list: () => call('rolesList', () => realRoles.list()),
}

export const authRegisterApi = {
  register(payload: { username: string; display_name: string; email?: string; password: string }): Promise<CurrentUser> {
    // public register không gửi role; backend phải set OPERATOR/PENDING. Client không bao giờ chọn ADMIN.
    return apiClient.post<CurrentUser>('/api/v1/auth/register', payload)
  },
}
