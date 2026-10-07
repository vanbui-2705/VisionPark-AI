import type { CurrentUser } from '../api/types.ts'

export type Permission =
  | 'dashboard.read'
  | 'station.use'
  | 'station.history.read'
  | 'detections.read'
  | 'detections.confirm'
  | 'checkin.create'
  | 'transactions.read'
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

export const PERMISSION_MATRIX: { perm: Permission; label: string; admin: boolean; operator: boolean; accountant: boolean; technician: boolean }[] = [
  { perm: 'dashboard.read', label: 'Dashboard', admin: true, operator: false, accountant: true, technician: false },
  { perm: 'station.use', label: 'Quét biển số', admin: true, operator: true, accountant: false, technician: true },
  { perm: 'station.history.read', label: 'Lịch sử station', admin: true, operator: true, accountant: false, technician: true },
  { perm: 'detections.read', label: 'Xem detection', admin: true, operator: true, accountant: false, technician: true },
  { perm: 'detections.confirm', label: 'Xác nhận / sửa biển số', admin: true, operator: true, accountant: false, technician: true },
  { perm: 'checkin.create', label: 'Check-in / đăng ký vào bãi', admin: true, operator: true, accountant: false, technician: true },
  { perm: 'transactions.read', label: 'Lịch sử đỗ xe', admin: true, operator: true, accountant: true, technician: false },
  { perm: 'lanes.read', label: 'Xem làn xe', admin: true, operator: true, accountant: false, technician: true },
  { perm: 'lanes.create', label: 'Tạo làn xe', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'lanes.update', label: 'Cập nhật làn xe', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'lanes.manage', label: 'Quản lý làn xe', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'users.read', label: 'Xem người dùng', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'users.manage', label: 'Quản lý người dùng', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'roles.read', label: 'Xem vai trò', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'permissions.read', label: 'Xem ma trận phân quyền', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'alpr.read', label: 'ALPR', admin: true, operator: false, accountant: false, technician: true },
  { perm: 'alpr.test', label: 'ALPR Test Lab (dev)', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'audit.read', label: 'Audit Logs', admin: true, operator: false, accountant: true, technician: false },
  { perm: 'errors.read', label: 'Error Center', admin: true, operator: false, accountant: false, technician: false },
  { perm: 'system.read', label: 'System Health', admin: true, operator: false, accountant: false, technician: true },
  { perm: 'profile.read', label: 'Hồ sơ cá nhân', admin: true, operator: true, accountant: true, technician: true },
  { perm: 'profile.update', label: 'Cập nhật hồ sơ', admin: true, operator: true, accountant: true, technician: true },
  { perm: 'settings.update', label: 'Cài đặt (frontend prefs)', admin: true, operator: true, accountant: true, technician: true },
  { perm: 'notifications.read', label: 'Thông báo', admin: true, operator: true, accountant: true, technician: true },
  { perm: 'help.read', label: 'Trợ giúp', admin: true, operator: true, accountant: true, technician: true },
  { perm: 'docs.read', label: 'Docs Center', admin: true, operator: false, accountant: false, technician: false },
]

const ROLE_COLUMN: Record<CurrentUser['role'], 'admin' | 'operator' | 'accountant' | 'technician'> = {
  ADMIN: 'admin',
  OPERATOR: 'operator',
  ACCOUNTANT: 'accountant',
  TECHNICIAN: 'technician',
}

export function can(user: CurrentUser | null | undefined, perm: Permission): boolean {
  if (!user) return false
  const column = ROLE_COLUMN[user.role]
  return column ? (PERMISSION_MATRIX.find((entry) => entry.perm === perm)?.[column] ?? false) : false
}
