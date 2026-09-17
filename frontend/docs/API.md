# API Contract (Phase 1)

Nguồn: `src/api/client.ts`, `src/api/services.ts`, `dev/mock-api.mjs`. Base URL từ env `VITE_API_BASE_URL` (mặc định dev `http://localhost:8000`). Không hard-code trong component.

## Auth
- `POST /api/v1/auth/login` → `{ access_token, token_type, user }`
- `GET /api/v1/auth/me` → user hiện tại
- `POST /api/v1/auth/register` — public registration TẮT mặc định (`PUBLIC_REGISTRATION_ENABLED=false`); client không cho tự đăng ký ADMIN.

## Lanes (không có DELETE)
- `GET /api/v1/lanes`
- `GET /api/v1/lanes/{id}`
- `POST /api/v1/lanes`
- `PATCH /api/v1/lanes/{id}`

## Detections / ALPR
- `POST /api/v1/alpr/detections`
- `GET /api/v1/alpr/detections?limit&lane_id`
- `POST /api/v1/alpr/detections/{id}/confirmation`

## Users
- `GET /api/v1/users` · `GET /api/v1/users/{id}` · `POST /api/v1/users` · `PATCH /api/v1/users/{id}` (ADMIN)

## Khác
- `GET /api/v1/roles` · `GET /api/v1/audit-logs` (ADMIN)
- `GET /health/live` · `GET /health/ready`

## Error contract
```json
{ "code": "ERROR_CODE", "message": "...", "details": {}, "correlation_id": "uuid" }
```
Frontend map thành `ApiError { status, code, details, correlationId }`. 401 → xóa token + redirect login. Timeout 15s (`VITE_API_TIMEOUT_MS`). FormData không set Content-Type thủ công.
