import type { CurrentUser } from '../api/types.ts'

export type Permission =
  | 'dashboard.read'
  | 'operations.report.read'
  | 'station.use'
  | 'station.history.read'
  | 'detections.read'
  | 'detections.confirm'
  | 'checkin.create'
  | 'checkout.create'
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

export interface PermissionEntry {
  perm: Permission
  label: string
  admin: boolean
  buildingAdmin: boolean
  operator: boolean
  accountant: boolean
}

export const PERMISSION_MATRIX: PermissionEntry[] = [
  { perm: 'dashboard.read', label: 'Dashboard', admin: true, buildingAdmin: true, operator: false, accountant: true },
  { perm: 'operations.report.read', label: 'Báo cáo vận hành tòa nhà', admin: true, buildingAdmin: true, operator: false, accountant: false },
  { perm: 'station.use', label: 'Quét biển số', admin: true, buildingAdmin: true, operator: true, accountant: false },
  { perm: 'station.history.read', label: 'Lịch sử station', admin: true, buildingAdmin: true, operator: true, accountant: false },
  { perm: 'detections.read', label: 'Xem detection', admin: true, buildingAdmin: true, operator: true, accountant: false },
  { perm: 'detections.confirm', label: 'Xác nhận / sửa biển số', admin: true, buildingAdmin: true, operator: true, accountant: false },
  { perm: 'checkin.create', label: 'Check-in / đăng ký vào bãi', admin: true, buildingAdmin: true, operator: true, accountant: false },
  { perm: 'checkout.create', label: 'Thu tiền / cho xe ra', admin: true, buildingAdmin: true, operator: true, accountant: false },
  { perm: 'transactions.read', label: 'Lịch sử đỗ xe', admin: true, buildingAdmin: true, operator: true, accountant: true },
  { perm: 'lanes.read', label: 'Xem làn xe', admin: true, buildingAdmin: true, operator: true, accountant: false },
  { perm: 'lanes.create', label: 'Tạo làn xe', admin: false, buildingAdmin: true, operator: false, accountant: false },
  { perm: 'lanes.update', label: 'Cập nhật làn xe', admin: false, buildingAdmin: true, operator: false, accountant: false },
  { perm: 'lanes.manage', label: 'Quản lý làn xe', admin: false, buildingAdmin: true, operator: false, accountant: false },
  { perm: 'users.read', label: 'Xem người dùng', admin: true, buildingAdmin: true, operator: false, accountant: false },
  { perm: 'users.manage', label: 'Quản lý người dùng', admin: true, buildingAdmin: true, operator: false, accountant: false },
  { perm: 'roles.read', label: 'Xem vai trò', admin: true, buildingAdmin: false, operator: false, accountant: false },
  { perm: 'permissions.read', label: 'Xem ma trận phân quyền', admin: true, buildingAdmin: false, operator: false, accountant: false },
  { perm: 'alpr.read', label: 'ALPR', admin: true, buildingAdmin: false, operator: false, accountant: false },
  { perm: 'alpr.test', label: 'ALPR Test Lab (dev)', admin: true, buildingAdmin: false, operator: false, accountant: false },
  { perm: 'audit.read', label: 'Audit Logs', admin: true, buildingAdmin: true, operator: false, accountant: true },
  { perm: 'errors.read', label: 'Error Center', admin: true, buildingAdmin: false, operator: false, accountant: false },
  { perm: 'system.read', label: 'System Health', admin: true, buildingAdmin: false, operator: false, accountant: false },
  { perm: 'profile.read', label: 'Hồ sơ cá nhân', admin: true, buildingAdmin: true, operator: true, accountant: true },
  { perm: 'profile.update', label: 'Cập nhật hồ sơ', admin: true, buildingAdmin: true, operator: true, accountant: true },
  { perm: 'settings.update', label: 'Cài đặt', admin: true, buildingAdmin: true, operator: true, accountant: true },
  { perm: 'notifications.read', label: 'Thông báo', admin: true, buildingAdmin: true, operator: true, accountant: true },
  { perm: 'help.read', label: 'Trợ giúp', admin: true, buildingAdmin: true, operator: true, accountant: true },
  { perm: 'docs.read', label: 'Docs Center', admin: true, buildingAdmin: false, operator: false, accountant: false },
]

const ROLE_COLUMN: Record<CurrentUser['role'], keyof Pick<PermissionEntry, 'admin' | 'buildingAdmin' | 'operator' | 'accountant'>> = {
  SYSTEM_ADMIN: 'admin',
  BUILDING_ADMIN: 'buildingAdmin',
  OPERATOR: 'operator',
  ACCOUNTANT: 'accountant',
}

export function can(user: CurrentUser | null | undefined, perm: Permission): boolean {
  if (!user) return false
  const entry = PERMISSION_MATRIX.find((candidate) => candidate.perm === perm)
  return entry?.[ROLE_COLUMN[user.role]] ?? false
}
