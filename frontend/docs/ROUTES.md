# Routes

Public: `/login`, `/register` (feature-gated).
ADMIN/OPERATOR/TECHNICIAN: `/station/scan`, `/detections`, `/detections/:id`.
ADMIN/OPERATOR/ACCOUNTANT: `/parking`, `/parking/:id`.

Lanes: `/admin/lanes`, `/admin/lanes/:id` đọc cho ADMIN/OPERATOR/TECHNICIAN;
`/new`, `/:id/edit` chỉ ADMIN. Nút ghi bị ẩn với OPERATOR.
Dashboard: ADMIN/ACCOUNTANT. Audit: ADMIN/ACCOUNTANT. ALPR status và system health:
ADMIN/TECHNICIAN. Admin-only: users, roles, permissions, alpr/test, errors, docs.
Tài khoản: `/profile`, `/settings`, `/notifications`, `/help`.

`/` redirect ADMIN/ACCOUNTANT tới dashboard, OPERATOR/TECHNICIAN tới Station.
Fullscreen/Station history và legacy Admin operations URLs redirect về route
canonical. API backend luôn enforce quyền độc lập với route guard.
