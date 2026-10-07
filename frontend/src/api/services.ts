import { apiClient } from './client.ts'
import { mapUser } from './authApi.ts'
import { getApiBaseUrl } from './client.ts'
import type { CurrentUser } from './types.ts'
import type { AuditLog, CheckInRequest, CheckInResponse, Detection, ManagedUser, ParkingHistoryFilter, ParkingTransaction } from './domain.ts'

export interface UsersApi {
  list(params?: { q?: string; role?: string; active?: boolean }): Promise<ManagedUser[]>
  get(id: string): Promise<ManagedUser>
  create(payload: {
    username: string
    display_name: string
    email?: string | null
    password: string
    role: ManagedUser['role']
    active?: boolean
  }): Promise<ManagedUser>
  patch(id: string, payload: Partial<ManagedUser & { password?: string }>): Promise<ManagedUser>
}

export interface DetectionsApi {
  list(params?: { lane_id?: string; direction?: string; status?: string; q?: string; limit?: number; from?: string; to?: string }): Promise<Detection[]>
  get(id: string): Promise<Detection>
  confirm(id: string, payload: { final_plate: string }): Promise<Detection>
}

export interface ParkingTransactionsApi {
  summary(): Promise<{ total: number; parked: number; manual: number }>
  list(params?: ParkingHistoryFilter): Promise<ParkingTransaction[]>
  get(id: string): Promise<ParkingTransaction>
  checkIn(payload: CheckInRequest, idempotencyKey?: string): Promise<CheckInResponse>
}

export interface AuditApi {
  list(params?: { actor?: string; actor_id?: string; resource_id?: string; offset?: number; action?: string; from?: string; to?: string; limit?: number }): Promise<AuditLog[]>
}

export interface RolesApi {
  list(): Promise<{ name: string; display_name: string; description: string }[]>
}

type ManagedUserResponse = Omit<ManagedUser, 'active' | 'last_login'> & { is_active: boolean; last_login_at: string | null }
function mapManagedUser(raw: ManagedUserResponse): ManagedUser {
  return { ...raw, ...mapUser(raw), last_login: raw.last_login_at ?? undefined }
}
const realUsers: UsersApi = {
  list: async (p) => (await apiClient.get<ManagedUserResponse[]>('/api/v1/users', { params: p })).map(mapManagedUser),
  get: async (id) => mapManagedUser(await apiClient.get<ManagedUserResponse>(`/api/v1/users/${id}`)),
  create: async (b) => mapManagedUser(await apiClient.post<ManagedUserResponse>('/api/v1/users', b)),
  patch: async (id, b) => mapManagedUser(await apiClient.patch<ManagedUserResponse>(`/api/v1/users/${id}`, b)),
}

const realDetections: DetectionsApi = {
  list: async (p) => (await apiClient.get<DetectionResponse[]>('/api/v1/alpr/detections', { params: p })).map(mapDetection),
  get: async (id) => mapDetection(await apiClient.get<DetectionResponse>(`/api/v1/alpr/detections/${id}`)),
  confirm: async (id, b) => mapDetection(await apiClient.post<DetectionResponse>(`/api/v1/alpr/detections/${id}/confirm`, { confirmed_plate: b.final_plate })),
}

export interface DetectionResponse {
  input_kind?: string | null; lane_name?: string | null; direction?: "IN" | "OUT";
  id: string; lane_id: string; image_key: string; raw_plate: string | null;
  normalized_plate: string | null; confidence: number | null;
  requires_confirmation: boolean; is_confirmed: boolean; confirmed_plate: string | null;
  created_at: string; confirmed_at: string | null; confirmed_by_id: string | null;
  processing_time_ms: number | null; model_version: string | null;
  bbox_x1: number | null; bbox_y1: number | null; bbox_x2: number | null; bbox_y2: number | null;
}
export function mapDetection(raw: DetectionResponse): Detection {
  return {
    ...raw, lane_name: raw.lane_name ?? undefined, ai_plate: raw.raw_plate, final_plate: raw.confirmed_plate,
    status: raw.is_confirmed ? (raw.confirmed_plate === raw.normalized_plate ? 'CONFIRMED' : 'CORRECTED')
      : !raw.normalized_plate ? 'NO_PLATE' : raw.requires_confirmation ? 'NEEDS_CONFIRMATION' : 'DETECTED',
    image_url: `${getApiBaseUrl()}/api/v1/alpr/media/${encodeURIComponent(raw.image_key)}`,
    processing_ms: raw.processing_time_ms, confirmed_by: raw.confirmed_by_id,
    bbox: raw.bbox_x1 != null && raw.bbox_y1 != null && raw.bbox_x2 != null && raw.bbox_y2 != null
      ? { x: raw.bbox_x1, y: raw.bbox_y1, w: raw.bbox_x2 - raw.bbox_x1, h: raw.bbox_y2 - raw.bbox_y1 } : null,
  }
}

const realParkingTransactions: ParkingTransactionsApi = {
  summary: () => apiClient.get('/api/v1/parking/summary'),
  list: (p) => apiClient.get<ParkingTransaction[]>('/api/v1/parking/transactions', { params: p }),
  get: (id) => apiClient.get<ParkingTransaction>(`/api/v1/parking/transactions/${id}`),
  checkIn: (payload, idempotencyKey) => apiClient.post<CheckInResponse>('/api/v1/parking/check-in', payload, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
  }),
}

const realAudit: AuditApi = {
  list: (p) => apiClient.get<AuditLog[]>('/api/v1/audit-logs', { params: p }),
}

const realRoles: RolesApi = {
  list: () => apiClient.get<{ name: string; display_name: string; description: string }[]>('/api/v1/roles'),
}

export const usersApi = realUsers
export const detectionsApi = realDetections
export const parkingTransactionsApi = realParkingTransactions
export const auditApi = realAudit
export const rolesApi = realRoles

export const authRegisterApi = {
  register(payload: { username: string; display_name: string; email?: string; password: string }): Promise<CurrentUser> {
    // public register không gửi role; backend phải set OPERATOR/PENDING. Client không bao giờ chọn ADMIN.
    return apiClient.post<CurrentUser>('/api/v1/auth/register', payload)
  },
}
