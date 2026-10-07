export type UserRole = 'ADMIN' | 'OPERATOR' | 'ACCOUNTANT' | 'TECHNICIAN'

export interface CurrentUser {
  id: string
  username: string
  email?: string | null
  display_name: string
  role: UserRole
  active: boolean
}

export type LaneDirection = 'IN' | 'OUT'

export interface Lane {
  id: string
  name: string
  direction: LaneDirection
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
