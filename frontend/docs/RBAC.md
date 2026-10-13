# RBAC

Nguồn: `src/lib/permissions.ts` (`PERMISSION_MATRIX` + `can()`), `src/layouts/AppShell.tsx`, `src/app/router.tsx`.

- Roles hiện hành: `SYSTEM_ADMIN`, `BUILDING_ADMIN`, `OPERATOR`, `ACCOUNTANT` (derive từ `GET /api/v1/auth/me`).
- Sidebar lọc bằng `can(user, perm)` — không `role ===` rải rác.
- `AdminGuard` render `ForbiddenPage` (403) cho OPERATOR vào route ADMIN-only.
- OPERATOR vận hành Station/check-in, đọc detection, parking, lanes và audit liên quan; không quản trị users/lanes.
- ACCOUNTANT đọc dashboard, parking và audit; không check-in hoặc xem detection.
- TECHNICIAN dùng Station/check-in, đọc và xác nhận detection, xem lanes, ALPR status và system health; không đọc parking/audit tổng quát.

Không fake role ở client; quyền thực thi ở backend.

`PERMISSION_MATRIX` trong `src/lib/permissions.ts` là cấu hình quyền của frontend; `can()` đọc trực tiếp ma trận này. `PermissionGuard` bảo vệ route theo từng quyền, kể cả dashboard/audit/ALPR/system. Backend kiểm tra role ở từng API; ma trận frontend không thay thế kiểm tra đó. Admin được quản lý users/roles/lanes. Operator chỉ đọc lane, không thêm/sửa/deactivate.

M1 thêm `BUILDING_ADMIN` với membership tòa nhà được xác thực ở backend. Vai trò này được đọc
dữ liệu tòa nhà và ghi cấu hình giá/vé, hóa đơn và thanh toán trong tòa nhà đó.
SYSTEM_ADMIN tạo tòa nhà và gán membership cho tài khoản. Thay đổi membership làm mất
hiệu lực token cũ. Callback thanh toán xác thực bằng chữ ký thay vì bearer token.
