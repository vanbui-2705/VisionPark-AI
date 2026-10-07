// ponytail: dev/test fixtures only. Không phải production API. Integration pending khi backend implement.
import type { AuditFilter, AuditLog, CheckInResponse, Detection, DetectionFilter, ManagedUser, PaginatedResponse, ParkingHistoryFilter, ParkingTransaction } from '../domain.ts'
import { ApiError } from '../errors.ts'

const users: ManagedUser[] = [
  { id: 'u-admin', username: 'admin', display_name: 'Quản trị', email: 'admin@visionpark.local', role: 'ADMIN', active: true, created_at: new Date().toISOString() },
  { id: 'u-op1', username: 'operator01', display_name: 'Nguyễn Văn A', email: 'operator01@visionpark.local', role: 'OPERATOR', active: true, created_at: new Date().toISOString() },
  { id: 'u-op2', username: 'operator02', display_name: 'Trần Văn B', role: 'OPERATOR', active: false, created_at: new Date().toISOString() },
]

const detections: Detection[] = [
  { id: 'd-1', lane_id: '1', lane_name: 'LANE_IN_01', direction: 'IN', ai_plate: '29A-123.45', normalized_plate: '29A12345', final_plate: '29A12345', confidence: 0.91, status: 'CONFIRMED', processing_ms: 35, model_version: 'mock-alpr-0.1.0', created_at: new Date().toISOString(), confirmed_at: new Date().toISOString(), confirmed_by: 'admin' },
  { id: 'd-2', lane_id: '1', lane_name: 'LANE_IN_01', direction: 'IN', ai_plate: '30F-888.88', normalized_plate: '30F88888', confidence: 0.64, status: 'NEEDS_CONFIRMATION', created_at: new Date().toISOString() },
]

const parkingTransactions: ParkingTransaction[] = [
  { id: 'pt-1', license_plate: '29A12345', original_ai_plate: '29A-123.45', normalized_plate: '29A12345', status: 'PARKED', lane_id: '1', lane_name: 'LANE_IN_01', detection_id: 'd-1', confidence: 0.91, check_in_time: new Date().toISOString(), check_in_operator_id: 'u-admin', check_in_operator_name: 'Duy Anh', source: 'STATION_AUTO', is_manual_override: false, created_at: new Date().toISOString() },
  { id: 'pt-2', license_plate: '30F88888', original_ai_plate: '30F-888.88', normalized_plate: '30F88888', status: 'PARKED', lane_id: '1', lane_name: 'LANE_IN_01', detection_id: 'd-2', confidence: 0.64, check_in_time: new Date().toISOString(), check_in_operator_id: 'u-admin', check_in_operator_name: 'Duy Anh', source: 'OPERATOR_MANUAL', is_manual_override: true, notes: 'Low-confidence plate corrected by operator.', created_at: new Date().toISOString() },
]

const audit: AuditLog[] = [
  { id: 'a-1', time: new Date().toISOString(), actor: 'Duy Anh', action: 'LANE_CREATE', resource: 'Lane', resource_id: '1', after: { name: 'LANE_IN_01' }, correlation_id: 'mock-cid-1' },
  { id: 'a-2', time: new Date().toISOString(), actor: 'Duy Anh', action: 'CHECK_IN', resource: 'ParkingTransaction', resource_id: 'pt-1', source: 'STATION_AUTO', after: { ai_plate: '29A-123.45', final_plate: '29A12345', lane_id: '1', status: 'PARKED' }, correlation_id: 'mock-cid-2' },
]

function paginate<T>(all: T[], page: number, pageSize: number): PaginatedResponse<T> {
  if (!Number.isInteger(page) || page < 0) throw new ApiError('Invalid page', { status: 422, code: 'VALIDATION_ERROR' })
  if (!Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) throw new ApiError('Invalid pageSize', { status: 422, code: 'VALIDATION_ERROR' })
  const total = all.length
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const start = page * pageSize
  const items = all.slice(start, start + pageSize)
  return { items, total, page, pageSize, totalPages }
}

function toPage(p?: Record<string, unknown>): { page: number; pageSize: number } {
  const page = p?.page != null ? Number(p.page) : 0
  const pageSize = p?.pageSize != null ? Number(p.pageSize) : p?.limit != null ? Number(p.limit) : 20
  return { page: Number.isFinite(page) ? page : 0, pageSize: Number.isFinite(pageSize) ? pageSize : 20 }
}

export const mockApi = {
  usersList: async (): Promise<ManagedUser[]> => [...users],
  usersGet: async (): Promise<ManagedUser> => users[0],
  usersCreate: async (): Promise<ManagedUser> => { throw Object.assign(new Error('Not implemented on backend — integration pending (P1-FE-USER-API).'), { code: 501 }) },
  usersPatch: async (): Promise<ManagedUser> => { throw Object.assign(new Error('Not implemented on backend — integration pending.'), { code: 501 }) },

  detectionsList: async (params?: DetectionFilter): Promise<PaginatedResponse<Detection>> => {
    const p = params as Record<string, unknown> | undefined
    let filtered = [...detections]
    if (p?.q) { const q = String(p.q).toLowerCase(); filtered = filtered.filter((d) => (d.final_plate ?? d.normalized_plate ?? d.ai_plate ?? '').toLowerCase().includes(q)) }
    if (p?.lane_id) filtered = filtered.filter((d) => d.lane_id === p.lane_id)
    if (p?.status && p.status !== 'ALL') filtered = filtered.filter((d) => d.status === p.status)
    if (p?.direction && p.direction !== 'ALL') filtered = filtered.filter((d) => d.direction === p.direction)
    if (p?.from) filtered = filtered.filter((d) => new Date(d.created_at) >= new Date(String(p.from)))
    if (p?.to) filtered = filtered.filter((d) => new Date(d.created_at) <= new Date(String(p.to) + 'T23:59:59'))
    const { page, pageSize } = toPage(p)
    return paginate(filtered, page, pageSize)
  },
  detectionsGet: async (): Promise<Detection> => detections[0],
  detectionsConfirm: async (): Promise<Detection> => detections[1],

  parkingTransactionsList: async (params?: ParkingHistoryFilter): Promise<PaginatedResponse<ParkingTransaction>> => {
    const p = params as Record<string, unknown> | undefined
    let filtered = [...parkingTransactions]
    if (p?.q) { const q = String(p.q).toLowerCase(); filtered = filtered.filter((t) => (t.license_plate ?? t.normalized_plate ?? '').toLowerCase().includes(q)) }
    if (p?.lane_id) filtered = filtered.filter((t) => t.lane_id === p.lane_id)
    if (p?.status && p.status !== 'ALL') filtered = filtered.filter((t) => t.status === p.status)
    if (p?.from) filtered = filtered.filter((t) => new Date(t.check_in_time) >= new Date(String(p.from)))
    if (p?.to) filtered = filtered.filter((t) => new Date(t.check_in_time) <= new Date(String(p.to) + 'T23:59:59'))
    const { page, pageSize } = toPage(p)
    return paginate(filtered, page, pageSize)
  },
  parkingTransactionsGet: async (): Promise<ParkingTransaction> => parkingTransactions[0],
  parkingTransactionsCheckIn: async (): Promise<CheckInResponse> => ({ transaction: parkingTransactions[0], message: 'Mock check-in created by Duy Anh' }),

  auditList: async (params?: AuditFilter): Promise<PaginatedResponse<AuditLog>> => {
    const p = params as Record<string, unknown> | undefined
    let filtered = [...audit]
    if (p?.actor) filtered = filtered.filter((a) => a.actor.toLowerCase().includes(String(p.actor).toLowerCase()))
    if (p?.action) filtered = filtered.filter((a) => a.action === p.action)
    if (p?.resource) filtered = filtered.filter((a) => a.resource === p.resource)
    if (p?.q) { const q = String(p.q).toLowerCase(); filtered = filtered.filter((a) => `${a.actor} ${a.action} ${a.resource} ${a.resource_id}`.toLowerCase().includes(q)) }
    if (p?.from) filtered = filtered.filter((a) => new Date(a.time) >= new Date(String(p.from)))
    if (p?.to) filtered = filtered.filter((a) => new Date(a.time) <= new Date(String(p.to) + 'T23:59:59'))
    const { page, pageSize } = toPage(p)
    return paginate(filtered, page, pageSize)
  },
  rolesList: async (): Promise<{ name: string; display_name: string; description: string }[]> => [
    { name: 'ADMIN', display_name: 'ADMIN', description: 'Toàn quyền quản trị' },
    { name: 'OPERATOR', display_name: 'OPERATOR', description: 'Nhân viên vận hành' },
  ],
}
