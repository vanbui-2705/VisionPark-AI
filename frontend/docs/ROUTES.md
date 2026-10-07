# Routes

Public: `/login`, `/register` (feature-gated).
ADMIN/OPERATOR: `/station/scan`, `/detections`, `/detections/:id`, `/parking`,
`/parking/:id`. Role khác nhận 403 tại các route nghiệp vụ.

Lanes: `/admin/lanes`, `/admin/lanes/:id` đọc cho ADMIN/OPERATOR;
`/new`, `/:id/edit` chỉ ADMIN. Nút ghi bị ẩn với OPERATOR.
Admin-only: dashboard, users, roles, permissions, alpr/test, audit, system, docs.
Tài khoản: `/profile`, `/settings`, `/notifications`, `/help`.

`/` redirect ADMIN tới dashboard, OPERATOR tới Station, role khác tới Profile.
Fullscreen/Station history và legacy Admin operations URLs redirect về route
canonical. API backend luôn enforce quyền độc lập với route guard.
