import { apiClient } from '../api/client'
export interface ClientError { id: string; time: string; code: string; status: number; message: string; source: string; correlationId?: string }
let list: ClientError[] = []
const subs = new Set<() => void>()
let timer: ReturnType<typeof setInterval> | undefined
export async function refreshErrorLog() {
  const result = await apiClient.get<{ items: ClientError[] }>('/api/v1/errors')
  list = result.items; subs.forEach(fn => fn())
}
export function getErrorLog() { return list }
export function subscribeErrorLog(fn: () => void): () => void {
  subs.add(fn)
  if (subs.size === 1) { void refreshErrorLog().catch(() => undefined); timer = setInterval(() => void refreshErrorLog().catch(() => undefined), 30000) }
  return () => { subs.delete(fn); if (!subs.size) { clearInterval(timer); list = [] } }
}
export function clearErrorLog() { void refreshErrorLog().catch(() => undefined) }
