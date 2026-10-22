export type UserRole = 'SYSTEM_ADMIN' | 'BUILDING_ADMIN' | 'OPERATOR' | 'ACCOUNTANT' | 'TECHNICIAN'

export interface CurrentUser {
  id: string
  username: string
  email?: string | null
  display_name: string
  role: UserRole
  building_id?: string | null
  active: boolean
}

export type LaneDirection = 'IN' | 'OUT'

export interface Lane {
  id: string
  name: string
  direction: LaneDirection
  building_id?: string | null
  video_source?: string | null
  active: boolean
  created_at?: string
  updated_at?: string
}

export interface HealthStatus {
  status: string
  database?: { ready: boolean; status?: string }
  alpr?: { ready: boolean; status?: string; provider?: string; version?: string; model_version?: string; ocr_enabled?: boolean }
  // allow extra fields
  [k: string]: unknown
}
