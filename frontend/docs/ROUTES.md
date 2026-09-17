# Routes

Nguồn: `src/app/router.tsx`.

- Public: `/login`, `/register`
- Station: `/station/scan`, `/station/scan/fullscreen`
- Detections: `/detections`, `/detections/:id`
- Admin: `/admin/dashboard`, `/admin/lanes` (+ `/new`, `/:id`, `/:id/edit`), `/admin/users` (+ tương tự), `/admin/roles`, `/admin/permissions`, `/admin/alpr` (+ `/test`), `/admin/audit-logs`, `/admin/errors`, `/admin/system`
- Account: `/profile`, `/settings`, `/notifications`, `/help`
- Docs: `/docs` (index) + `/docs/:slug` (ADMIN only, OPERATOR→403)
- Dev: `/dev/ui-kit`
- Errors: `/403`, `/404`; `*`→`/404`; `/` redirect theo role.
- Aliases: `/station/history`→`/detections`, `/admin/detections`→`/detections`, `/admin/profile`→`/profile`.
