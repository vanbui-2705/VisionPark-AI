import type { CurrentUser } from '../api/types.ts'

export type Permission =
  | 'dashboard.read'
  | 'station.use'
  | 'station.history.read'
  | 'detections.read'
  | 'detections.confirm'
  | 'lanes.read'
  | 'lanes.create'
  | 'lanes.update'
  | 'lanes.manage'
  | 'users.read'
  | 'users.manage'
  | 'roles.read'
  | 'permissions.read'
  | 'alpr.read'
  | 'alpr.test'
  | 'audit.read'
  | 'errors.read'
  | 'system.read'
  | 'profile.read'
  | 'profile.update'
  | 'settings.update'
  | 'notifications.read'
  | 'help.read'
  | 'docs.read'

const ADMIN_ALL: Permission[] = [
  'dashboard.read',
  'station.use',
  'station.history.read',
  'detections.read',
  'detections.confirm',
  'lanes.read',
  'lanes.create',
  'lanes.update',
  'lanes.manage',
  'users.read',
  'users.manage',
  'roles.read',
  'permissions.read',
  'alpr.read',
  'alpr.test',
  'audit.read',
  'errors.read',
  'system.read',
  'profile.read',
  'profile.update',
  'settings.update',
  'notifications.read',
  'help.read',
  'docs.read',
]

// OPERATOR — spec: station.use, detections.read, detections.confirm, lanes.read,
// profile.read, profile.update + trang cá nhân/cài đặt/thông báo/trợ giúp.
const OPERATOR_PERMS: Permission[] = [
  'station.use',
  'station.history.read',
  'detections.read',
  'detections.confirm',
  'lanes.read',
  'profile.read',
  'profile.update',
  'settings.update',
  'notifications.read',
  'help.read',
]

export function can(user: CurrentUser | null | undefined, perm: Permission): boolean {
  if (!user) return false
  if (user.role === 'ADMIN') return (ADMIN_ALL as string[]).includes(perm)
  return (OPERATOR_PERMS as string[]).includes(perm)
}

export const PERMISSION_MATRIX: { perm: Permission; label: string; admin: boolean; operator: boolean }[] = [
  { perm: 'dashboard.read', label: 'Dashboard', admin: true, operator: false },
  { perm: 'station.use', label: 'Quét biển số', admin: true, operator: true },
  { perm: 'station.history.read', label: 'Lịch sử station', admin: true, operator: true },
  { perm: 'detections.read', label: 'Xem detection', admin: true, operator: true },
  { perm: 'detections.confirm', label: 'Xác nhận / sửa biển số', admin: true, operator: true },
  { perm: 'lanes.read', label: 'Xem làn xe', admin: true, operator: true },
  { perm: 'lanes.create', label: 'Tạo làn xe', admin: true, operator: false },
  { perm: 'lanes.update', label: 'Cập nhật làn xe', admin: true, operator: false },
  { perm: 'users.read', label: 'Xem người dùng', admin: true, operator: false },
  { perm: 'users.manage', label: 'Quản lý người dùng', admin: true, operator: false },
  { perm: 'roles.read', label: 'Xem vai trò', admin: true, operator: false },
  { perm: 'permissions.read', label: 'Xem ma trận phân quyền', admin: true, operator: false },
  { perm: 'alpr.read', label: 'ALPR', admin: true, operator: false },
  { perm: 'alpr.test', label: 'ALPR Test Lab (dev)', admin: true, operator: false },
  { perm: 'audit.read', label: 'Audit Logs', admin: true, operator: false },
  { perm: 'errors.read', label: 'Error Center', admin: true, operator: false },
  { perm: 'system.read', label: 'System Health', admin: true, operator: false },
  { perm: 'profile.read', label: 'Hồ sơ cá nhân', admin: true, operator: true },
  { perm: 'profile.update', label: 'Cập nhật hồ sơ', admin: true, operator: true },
  { perm: 'settings.update', label: 'Cài đặt (frontend prefs)', admin: true, operator: true },
  { perm: 'notifications.read', label: 'Thông báo', admin: true, operator: true },
  { perm: 'help.read', label: 'Trợ giúp', admin: true, operator: true },
  { perm: 'docs.read', label: 'Docs Center', admin: true, operator: false },
]
