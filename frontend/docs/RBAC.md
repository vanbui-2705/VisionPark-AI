# RBAC

Nguồn: `src/lib/permissions.ts` (`PERMISSION_MATRIX` + `can()`), `src/layouts/AppShell.tsx`, `src/app/router.tsx`.

- Roles: `ADMIN`, `OPERATOR`, `ACCOUNTANT`, `TECHNICIAN` (derive từ `GET /api/v1/auth/me`).
- Sidebar lọc bằng `can(user, perm)` — không `role ===` rải rác.
- `AdminGuard` render `ForbiddenPage` (403) cho OPERATOR vào route ADMIN-only.
- OPERATOR được: `station.use`, `station.history.read`, `detections.read`, `detections.confirm`, `lanes.read`, `profile.read`, `profile.update`, `settings.update`, `notifications.read`, `help.read`.

Không fake role ở client; quyền thực thi ở backend.

`PermissionGuard` bảo vệ các route vận hành. Accountant/Technician vào `/profile`, không được ép thành Operator. Admin được quản lý users/roles/lanes và xem audit. Operator chỉ đọc lane, không thêm/sửa/deactivate.
