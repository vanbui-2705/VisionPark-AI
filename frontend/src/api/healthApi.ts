import { apiClient } from './client.ts'
import type { HealthStatus } from './types.ts'

export const healthApi = {
  live(): Promise<unknown> {
    return apiClient.get('/health/live')
  },
  ready(): Promise<HealthStatus> {
    return apiClient.get<HealthStatus>('/health/ready')
  },
}
