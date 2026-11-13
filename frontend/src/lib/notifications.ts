import { apiClient } from '../api/client'
import { getToken } from '../api/token'
export interface NotificationItem { id: string; time: string; title: string; message: string; read: boolean; to?: string }
let list: NotificationItem[] = []
const subs = new Set<() => void>()
let timer: ReturnType<typeof setTimeout> | undefined
let generation = 0
let delay = 15000
let lastError = ''
export async function refreshNotifications(): Promise<void> {
  const current = generation
  if (!getToken()) { list = []; return }
  const result = await apiClient.get<{ items: NotificationItem[] }>('/api/v1/notifications')
  if (!Array.isArray(result.items)) throw new Error('Invalid notifications response')
  if (current !== generation) return
  list = result.items; lastError = ''; subs.forEach(fn => fn())
}
async function poll() {
  try { await refreshNotifications(); delay = 15000 }
  catch (error) {
    lastError = error instanceof Error ? error.message : 'Không tải được thông báo.'
    subs.forEach(fn => fn())
    delay = Math.min(delay * 2, 120000)
  }
  if (subs.size) timer = setTimeout(() => void poll(), delay)
}
export function getNotifications() { return list }
export function getUnreadCount() { return list.filter(n => !n.read).length }
export function getNotificationsError() { return lastError }
export function markNotificationRead(id: string) { return apiClient.post(`/api/v1/notifications/${id}/read`).then(refreshNotifications) }
export function markAllRead() { return apiClient.post('/api/v1/notifications/read-all').then(refreshNotifications) }
export function subscribeNotifications(fn: () => void): () => void {
  subs.add(fn)
  if (subs.size === 1) void poll()
  return () => { subs.delete(fn); if (!subs.size) { clearTimeout(timer); generation += 1; list = []; lastError = '' } }
}
