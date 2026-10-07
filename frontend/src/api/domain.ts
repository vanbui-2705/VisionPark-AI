export type DetectionStatus =
  | 'DETECTED'
  | 'NEEDS_CONFIRMATION'
  | 'CONFIRMED'
  | 'CORRECTED'
  | 'NO_PLATE'
  | 'ERROR'

export interface Detection {
  id: string
  lane_id: string
  lane_name?: string
  direction?: 'IN' | 'OUT'
  image_url?: string | null
  ai_plate?: string | null
  normalized_plate?: string | null
  final_plate?: string | null
  confidence?: number | null
  status: DetectionStatus
  processing_ms?: number | null
  model_version?: string | null
  operator?: string | null
  bbox?: { x: number; y: number; w: number; h: number } | null
  created_at: string
  confirmed_at?: string | null
  confirmed_by?: string | null
}

export interface AlprProviderInfo {
  provider: string
  ready: boolean
  model_version?: string
  confidence_threshold?: number
  runtime?: string
}

export type CheckInSource =
  | 'AI_ACCEPTED'
  | 'OPERATOR_CORRECTED'
  | 'MANUAL_ENTRY'
  | 'STATION_AUTO'
  | 'OPERATOR_MANUAL'

export type TransactionStatus = 'PARKED' | 'COMPLETED' | 'CANCELLED'

export interface ParkingTransaction {
  id: string
  license_plate: string
  original_ai_plate?: string | null
  normalized_plate: string
  status: TransactionStatus
  lane_id: string
  lane_name?: string
  detection_id?: string | null
  image_url?: string | null
  confidence?: number | null
  check_in_time: string
  check_in_operator_id?: string | null
  check_in_operator_name?: string | null
  source: CheckInSource
  is_manual_override: boolean
  notes?: string | null
  created_at: string
}

export interface CheckInRequest {
  lane_id: string
  license_plate?: string | null
  plate_number?: string | null
  detection_id?: string | null
  confidence?: number | null
  original_ai_plate?: string | null
  source?: CheckInSource | null
  override_reason?: string | null
  idempotency_key?: string | null
}

export interface CheckInResponse {
  transaction: ParkingTransaction
  message: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface PaginationParams {
  page?: number
  pageSize?: number
  limit?: number
  offset?: number
}

export interface ParkingHistoryFilter extends PaginationParams {
  q?: string
  lane_id?: string
  status?: TransactionStatus | 'ALL'
  from?: string
  to?: string
}

export interface AuditFilter extends PaginationParams {
  actor?: string
  action?: string
  resource?: string
  from?: string
  to?: string
  q?: string
}

export interface DetectionFilter extends PaginationParams {
  lane_id?: string
  direction?: string
  status?: string
  q?: string
  from?: string
  to?: string
}

export interface AuditLog {
  id: string
  time: string
  actor: string | null
  action: string
  resource: string
  resource_id: string
  source?: string | null
  before?: unknown | null
  after?: unknown | null
  correlation_id?: string | null
}

export interface ManagedUser {
  id: string
  username: string
  display_name: string
  email?: string | null
  role: 'ADMIN' | 'OPERATOR' | 'ACCOUNTANT' | 'TECHNICIAN'
  active: boolean
  last_login?: string | null
  created_at?: string
}
