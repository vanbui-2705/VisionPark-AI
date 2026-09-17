export type UserRole = 'ADMIN' | 'OPERATOR'

export interface CurrentUser {
  id: string
  username: string
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
  database?: { ready: boolean }
  alpr?: { ready: boolean; provider?: string; model_version?: string }
  // allow extra fields
  [k: string]: unknown
}
