# Users

- `UserListPage.tsx` — table, filter, pagination (GET /api/v1/users).
- `UserDetailPage.tsx` — chi tiết + Audit.
- `UserEditPage.tsx` — display_name/email/role/active; active checkbox và mật khẩu mới lưu qua Admin PATCH API; dirty guard.
- `CreateUserPage.tsx` — validation + 409 handling; dirty guard; perm preview theo role.

Service `src/api/services.ts#usersApi` gọi backend thật. Force Logout thu hồi token qua API; profile và đổi mật khẩu dùng API tài khoản cá nhân.
