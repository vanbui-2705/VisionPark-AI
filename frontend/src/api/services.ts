import { apiClient } from './client.ts'
import { ApiError } from './errors.ts'
import type { CurrentUser } from './types.ts'
import type { AuditFilter, AuditLog, CheckInRequest, CheckInResponse, Detection, DetectionFilter, ManagedUser, PaginatedResponse, ParkingHistoryFilter, ParkingTransaction } from './domain.ts'

function normalizePaginated<T>(raw: PaginatedResponse<T> | T[], fallbackPage: number, fallbackPageSize: number): PaginatedResponse<T> {
  if (Array.isArray(raw)) return { items: raw, total: raw.length, page: fallbackPage, pageSize: fallbackPageSize, totalPages: Math.max(1, Math.ceil(raw.length / fallbackPageSize)) }
  return raw
}

export interface UsersApi {
  list(params?: { q?: string; role?: string; active?: boolean }): Promise<ManagedUser[]>
  get(id: string): Promise<ManagedUser>
  create(payload: { username: string; display_name: string; email?: string | null; password: string; role: 'ADMIN' | 'OPERATOR'; active?: boolean }): Promise<ManagedUser>
  patch(id: string, payload: Partial<ManagedUser & { password?: string }>): Promise<ManagedUser>
}

export interface DetectionsApi {
  list(params?: DetectionFilter): Promise<PaginatedResponse<Detection>>
  get(id: string): Promise<Detection>
  confirm(id: string, payload: { final_plate: string }): Promise<Detection>
}

export interface ParkingTransactionsApi {
  list(params?: ParkingHistoryFilter): Promise<PaginatedResponse<ParkingTransaction>>
  get(id: string): Promise<ParkingTransaction>
  checkIn(payload: CheckInRequest, idempotencyKey?: string): Promise<CheckInResponse>
}

export interface AuditApi {
  list(params?: AuditFilter): Promise<PaginatedResponse<AuditLog>>
}

export interface RolesApi {
  list(): Promise<{ name: string; display_name: string; description: string }[]>
}

function mockEnabled(): boolean {
  return import.meta.env.VITE_USE_MOCK_FIXTURES === 'true'
}

async function call<T>(key: string, real: () => Promise<T>, mockArgs?: unknown): Promise<T> {
  try {
    return await real()
  } catch (e: unknown) {
    const pending = e instanceof ApiError && (e.status === 404 || e.status === 501 || e.code === 'NOT_FOUND')
    if (pending && mockEnabled()) {
      const mod = await import('./mocks/fixtures.ts')
      const impl = (mod.mockApi as unknown as Record<string, (args?: unknown) => Promise<T>>)[key]
      if (impl) return impl(mockArgs)
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
  list: async (p) => {
    const raw = await apiClient.get<PaginatedResponse<Detection> | Detection[]>('/api/v1/alpr/detections', { params: p as Record<string, string | number | boolean | undefined | null> })
    return normalizePaginated(raw, p?.page ?? 0, p?.pageSize ?? p?.limit ?? 20)
  },
  get: (id) => apiClient.get<Detection>(`/api/v1/alpr/detections/${id}`),
  confirm: (id, b) => apiClient.post<Detection>(`/api/v1/alpr/detections/${id}/confirm`, b),
}

const realParkingTransactions: ParkingTransactionsApi = {
  list: async (p) => {
    const raw = await apiClient.get<PaginatedResponse<ParkingTransaction> | ParkingTransaction[]>('/api/v1/parking/transactions', { params: p as Record<string, string | number | boolean | undefined | null> })
    return normalizePaginated(raw, p?.page ?? 0, p?.pageSize ?? p?.limit ?? 20)
  },
  get: (id) => apiClient.get<ParkingTransaction>(`/api/v1/parking/transactions/${id}`),
  checkIn: (payload, idempotencyKey) => apiClient.post<CheckInResponse>('/api/v1/parking/check-in', payload, { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined }),
}

const realAudit: AuditApi = {
  list: async (p) => {
    const raw = await apiClient.get<PaginatedResponse<AuditLog> | AuditLog[]>('/api/v1/audit-logs', { params: p as Record<string, string | number | boolean | undefined | null> })
    return normalizePaginated(raw, p?.page ?? 0, p?.pageSize ?? p?.limit ?? 20)
  },
}

const realRoles: RolesApi = {
  list: () => apiClient.get<{ name: string; display_name: string; description: string }[]>('/api/v1/roles'),
}

export const usersApi: UsersApi = {
  list: (p) => call('usersList', () => realUsers.list(p), p),
  get: (id) => call('usersGet', () => realUsers.get(id), id),
  create: (b) => call('usersCreate', () => realUsers.create(b), b),
  patch: (id, b) => call('usersPatch', () => realUsers.patch(id, b), { id, b }),
}

export const detectionsApi: DetectionsApi = {
  list: (p) => call('detectionsList', () => realDetections.list(p), p),
  get: (id) => call('detectionsGet', () => realDetections.get(id), id),
  confirm: (id, b) => call('detectionsConfirm', () => realDetections.confirm(id, b), { id, b }),
}

export const parkingTransactionsApi: ParkingTransactionsApi = {
  list: (p) => call('parkingTransactionsList', () => realParkingTransactions.list(p), p),
  get: (id) => call('parkingTransactionsGet', () => realParkingTransactions.get(id), id),
  checkIn: (payload, idempotencyKey) => call('parkingTransactionsCheckIn', () => realParkingTransactions.checkIn(payload, idempotencyKey), { payload, idempotencyKey }),
}

export const auditApi: AuditApi = {
  list: (p) => call('auditList', () => realAudit.list(p), p),
}

export const rolesApi: RolesApi = {
  list: () => call('rolesList', () => realRoles.list()),
}

export const authRegisterApi = {
  register(payload: { username: string; display_name: string; email?: string; password: string }): Promise<CurrentUser> {
    return apiClient.post<CurrentUser>('/api/v1/auth/register', payload)
  },
}
