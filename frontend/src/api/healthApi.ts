import { apiClient } from './client.ts'
import type { HealthStatus } from './types.ts'

export const healthApi = {
  live(): Promise<unknown> {
    return apiClient.get('/health/live')
  },
  async ready(): Promise<HealthStatus> {
    const raw = await apiClient.get<HealthStatus>('/health/ready')
    return { ...raw,
      database: raw.database ? { ...raw.database, ready: raw.database.status === 'ready' } : undefined,
      alpr: raw.alpr ? { ...raw.alpr, ready: raw.alpr.status === 'ready', model_version: raw.alpr.version } : undefined,
    }
  },
}
