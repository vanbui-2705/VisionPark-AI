# Backend (tóm tắt cho frontend)

- Base: `VITE_API_BASE_URL`
- Auth: `POST /api/v1/auth/login`, `POST /api/v1/auth/register` (gate `PUBLIC_REGISTRATION_ENABLED`), `GET /api/v1/auth/me`
- Lanes: `GET/POST /api/v1/lanes`, `GET/PATCH /api/v1/lanes/:id` (không có DELETE)
- Users: `GET/POST /api/v1/users`, `GET/PATCH /api/v1/users/:id` (ADMIN only)
- Detections: `GET /api/v1/detections`, `GET /api/v1/detections/:id`, `POST /api/v1/detections/:id/confirm`
- Audit: `GET /api/v1/audit-logs` (ADMIN)
- Roles/Health: `GET /api/v1/roles`, `/health/ready`, `/health/live`
