import { apiClient } from './client.ts'
import type { Lane, LaneDirection } from './types.ts'

export interface LanePayload {
  name: string
  direction: LaneDirection
  video_source?: string | null
  active?: boolean
}

export const lanesApi = {
  getLanes(): Promise<Lane[]> {
    return apiClient.get<Lane[]>('/api/v1/lanes')
  },
  getLane(id: string): Promise<Lane> {
    return apiClient.get<Lane>(`/api/v1/lanes/${id}`)
  },
  createLane(payload: LanePayload): Promise<Lane> {
    return apiClient.post<Lane>('/api/v1/lanes', payload)
  },
  updateLane(id: string, payload: Partial<LanePayload>): Promise<Lane> {
    return apiClient.patch<Lane>(`/api/v1/lanes/${id}`, payload)
  },
  setLaneInactive(id: string): Promise<Lane> {
    return apiClient.patch<Lane>(`/api/v1/lanes/${id}`, { active: false })
  },
}
