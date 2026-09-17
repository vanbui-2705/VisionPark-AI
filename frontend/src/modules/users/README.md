# Users

- `UserListPage.tsx` — table, filter, pagination (GET /api/v1/users).
- `UserDetailPage.tsx` — chi tiết + Audit.
- `UserEditPage.tsx` — display_name/email/role/active; Lock/Reset Password disabled (Backend API required); dirty guard.
- `CreateUserPage.tsx` — validation + 409 handling; dirty guard; perm preview theo role.

Service `src/api/services.ts#usersApi`. Mock fixture không fake success khi backend 404/501.
