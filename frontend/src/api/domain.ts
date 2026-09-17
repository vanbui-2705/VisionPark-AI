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

export interface AuditLog {
  id: string
  time: string
  actor: string
  action: string
  resource: string
  resource_id: string
  before?: unknown
  after?: unknown
  correlation_id?: string
}

export interface ManagedUser {
  id: string
  username: string
  display_name: string
  email?: string | null
  role: 'ADMIN' | 'OPERATOR'
  active: boolean
  last_login?: string | null
  created_at?: string
}
