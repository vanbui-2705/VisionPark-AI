# Auth

Nguồn: `src/modules/auth/AuthContext.tsx`, `src/api/client.ts`, `src/app/router.tsx`, `src/lib/permissions.ts`.

- Token key `visionpark.access_token`; remember key `visionpark.remember_user`.
- `AuthProvider` expose `initialized`, `isAuthenticated`, `isAdmin`, `user`, `login`, `logout`.
- `POST /api/v1/auth/login` → Bearer token. `GET /api/v1/auth/me` → user.
- `ProtectedRoute` + `AdminGuard` (`/403`) + `can(user, perm)` — không chỉ UI, backend cũng enforce.
- Root redirect: ADMIN→`/admin/dashboard`, OPERATOR→`/station/scan`, Guest→`/login`. `*`→`/404`.

Không hard-code JWT, không hard-code role, không lưu/log password hay access token.
