// Thông báo nội bộ frontend (không fake notification server).
// Chỉ ghi sự kiện thật xảy ra phía client: xác nhận detection, lỗi bắt được, thao tác CRUD.
export interface NotificationItem {
  id: number
  time: string
  title: string
  message: string
  read: boolean
  to?: string
}

let list: NotificationItem[] = []
let nextId = 1
const subs = new Set<() => void>()

export function pushNotification(n: { title: string; message: string; to?: string }): void {
  list = [{ id: nextId++, time: new Date().toISOString(), read: false, ...n }, ...list].slice(0, 100)
  subs.forEach((fn) => fn())
}

export function getNotifications(): NotificationItem[] {
  return list
}

export function getUnreadCount(): number {
  return list.filter((n) => !n.read).length
}

export function markNotificationRead(id: number): void {
  list = list.map((n) => (n.id === id ? { ...n, read: true } : n))
  subs.forEach((fn) => fn())
}

export function markAllRead(): void {
  list = list.map((n) => ({ ...n, read: true }))
  subs.forEach((fn) => fn())
}

export function subscribeNotifications(fn: () => void): () => void {
  subs.add(fn)
  return () => subs.delete(fn)
}
