import { apiClient } from './client.ts'
import type { Lane, LaneDirection } from './types.ts'

export interface LanePayload {
  name: string
  direction: LaneDirection
  video_source?: string | null
  active?: boolean
}

interface LaneResponse extends Omit<Lane, 'active'> { is_active: boolean }
function mapLane(raw: LaneResponse): Lane { return { ...raw, active: raw.is_active } }
function toPayload(payload: Partial<LanePayload>) {
  const { active, ...rest } = payload
  return { ...rest, ...(active === undefined ? {} : { is_active: active }) }
}

export const lanesApi = {
  async getLanes(): Promise<Lane[]> {
    return (await apiClient.get<LaneResponse[]>('/api/v1/lanes/')).map(mapLane)
  },
  async getActiveLanes(): Promise<Lane[]> {
    return (await apiClient.get<LaneResponse[]>('/api/v1/lanes/active')).map(mapLane)
  },
  async getLane(id: string): Promise<Lane> {
    return mapLane(await apiClient.get<LaneResponse>(`/api/v1/lanes/${id}`))
  },
  async createLane(payload: LanePayload): Promise<Lane> {
    return mapLane(await apiClient.post<LaneResponse>('/api/v1/lanes/', toPayload(payload)))
  },
  async updateLane(id: string, payload: Partial<LanePayload>): Promise<Lane> {
    return mapLane(await apiClient.patch<LaneResponse>(`/api/v1/lanes/${id}`, toPayload(payload)))
  },
  async setLaneInactive(id: string): Promise<Lane> {
    return mapLane(await apiClient.post<LaneResponse>(`/api/v1/lanes/${id}/deactivate`))
  },
}
