# Decisions (ADRs)

| # | Ngày | Quyết định | Lý do |
|---|------|-----------|-------|
| 1 | 2026-09 | `can()` + `PERMISSION_MATRIX` single source RBAC | Tránh `role ===` rải rác |
| 4 | 2026-09 | Station shell Người 5, player Người 4 | Đúng ownership |
| 5 | 2026-09 | Docs `frontend/docs/*.md` + `import.meta.glob` | Source-of-truth markdown, Vite lazy chunks |
| 6 | 2026-09 | Không `DELETE /lanes` Phase 1 | Spec cấm hard delete |

| 7 | 2026-10-07 | Station dùng shared API client/backend provider | Token và contract thống nhất; không giả success bằng mock client |
| 8 | 2026-10-07 | Final capture UUID; confirm atomic/idempotent | Retry không tạo detection/transaction trùng |

Current runtime: backend API only, ALPR_PROVIDER=real with OCR enabled. Preferences, notifications and error events persist in PostgreSQL.
