# Users

Nguồn: `src/modules/users/` (`UserListPage`, `CreateUserPage`, `UserDetailPage`, `UserEditPage`), `src/api/services.ts#usersApi`.

- Routes: `/admin/users`, `/admin/users/new`, `/admin/users/:id`, `/admin/users/:id/edit` (ADMIN only).
- Fields: `username` (readonly khi edit), `display_name`, `email`, `role` (ADMIN/OPERATOR), `active`.
- Edit: Save qua `PATCH /api/v1/users/:id`; Lock/Reset Password disabled "Backend API required".
- Create: validate bắt buộc + confirm password + 409 `DUPLICATE_USER`. Dirty guard `useUnsavedGuard`.
- Service boundary `call<T>(key, real)` — fixture chỉ fallback khi 404/501 và `VITE_USE_MOCK_FIXTURES=true`, và `usersCreate/usersPatch` throw 501 (không fake success).
