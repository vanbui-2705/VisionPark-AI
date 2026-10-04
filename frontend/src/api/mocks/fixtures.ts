// ponytail: dev/test fixtures only. Không phải production API. Integration pending khi backend implement.
import type { AuditLog, CheckInResponse, Detection, ManagedUser, ParkingTransaction } from '../domain.ts'

const users: ManagedUser[] = [
  { id: 'u-admin', username: 'admin', display_name: 'Quản trị', email: 'admin@visionpark.local', role: 'ADMIN', active: true, created_at: new Date().toISOString() },
  { id: 'u-op1', username: 'operator01', display_name: 'Nguyễn Văn A', email: 'operator01@visionpark.local', role: 'OPERATOR', active: true, created_at: new Date().toISOString() },
  { id: 'u-op2', username: 'operator02', display_name: 'Trần Văn B', role: 'OPERATOR', active: false, created_at: new Date().toISOString() },
]

const detections: Detection[] = [
  {
    id: 'd-1',
    lane_id: '1',
    lane_name: 'LANE_IN_01',
    direction: 'IN',
    ai_plate: '29A-123.45',
    normalized_plate: '29A12345',
    final_plate: '29A12345',
    confidence: 0.91,
    status: 'CONFIRMED',
    processing_ms: 35,
    model_version: 'mock-alpr-0.1.0',
    created_at: new Date().toISOString(),
    confirmed_at: new Date().toISOString(),
    confirmed_by: 'admin',
  },
  {
    id: 'd-2',
    lane_id: '1',
    lane_name: 'LANE_IN_01',
    direction: 'IN',
    ai_plate: '30F-888.88',
    normalized_plate: '30F88888',
    confidence: 0.64,
    status: 'NEEDS_CONFIRMATION',
    created_at: new Date().toISOString(),
  },
]

const parkingTransactions: ParkingTransaction[] = [
  {
    id: 'pt-1',
    license_plate: '29A12345',
    original_ai_plate: '29A-123.45',
    normalized_plate: '29A12345',
    status: 'PARKED',
    lane_id: '1',
    lane_name: 'LANE_IN_01',
    detection_id: 'd-1',
    confidence: 0.91,
    check_in_time: new Date().toISOString(),
    check_in_operator_id: 'u-admin',
    check_in_operator_name: 'Duy Anh',
    source: 'STATION_AUTO',
    is_manual_override: false,
    created_at: new Date().toISOString(),
  },
  {
    id: 'pt-2',
    license_plate: '30F88888',
    original_ai_plate: '30F-888.88',
    normalized_plate: '30F88888',
    status: 'PARKED',
    lane_id: '1',
    lane_name: 'LANE_IN_01',
    detection_id: 'd-2',
    confidence: 0.64,
    check_in_time: new Date().toISOString(),
    check_in_operator_id: 'u-admin',
    check_in_operator_name: 'Duy Anh',
    source: 'OPERATOR_MANUAL',
    is_manual_override: true,
    notes: 'Low-confidence plate corrected by operator.',
    created_at: new Date().toISOString(),
  },
]

const audit: AuditLog[] = [
  {
    id: 'a-1',
    time: new Date().toISOString(),
    actor: 'Duy Anh',
    action: 'LANE_CREATE',
    resource: 'Lane',
    resource_id: '1',
    after: { name: 'LANE_IN_01' },
    correlation_id: 'mock-cid-1',
  },
  {
    id: 'a-2',
    time: new Date().toISOString(),
    actor: 'Duy Anh',
    action: 'CHECK_IN',
    resource: 'ParkingTransaction',
    resource_id: 'pt-1',
    source: 'STATION_AUTO',
    after: { ai_plate: '29A-123.45', final_plate: '29A12345', lane_id: '1', status: 'PARKED' },
    correlation_id: 'mock-cid-2',
  },
]

export const mockApi = {
  usersList: async (): Promise<ManagedUser[]> => [...users],
  usersGet: async (): Promise<ManagedUser> => users[0],
  usersCreate: async (): Promise<ManagedUser> => {
    throw Object.assign(new Error('Not implemented on backend — integration pending (P1-FE-USER-API).'), { code: 501 })
  },
  usersPatch: async (): Promise<ManagedUser> => {
    throw Object.assign(new Error('Not implemented on backend — integration pending.'), { code: 501 })
  },
  detectionsList: async (): Promise<Detection[]> => [...detections],
  detectionsGet: async (): Promise<Detection> => detections[0],
  detectionsConfirm: async (): Promise<Detection> => detections[1],
  parkingTransactionsList: async (): Promise<ParkingTransaction[]> => [...parkingTransactions],
  parkingTransactionsGet: async (): Promise<ParkingTransaction> => parkingTransactions[0],
  parkingTransactionsCheckIn: async (): Promise<CheckInResponse> => ({
    transaction: parkingTransactions[0],
    message: 'Mock check-in created by Duy Anh',
  }),
  auditList: async (): Promise<AuditLog[]> => [...audit],
  rolesList: async (): Promise<{ name: string; display_name: string; description: string }[]> => [
    { name: 'ADMIN', display_name: 'ADMIN', description: 'Toàn quyền quản trị' },
    { name: 'OPERATOR', display_name: 'OPERATOR', description: 'Nhân viên vận hành' },
  ],
}
