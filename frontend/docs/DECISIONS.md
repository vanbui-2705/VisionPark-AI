# Decisions (ADRs)

| # | Ngày | Quyết định | Lý do |
|---|------|-----------|-------|
| 1 | 2026-09 | `can()` + `PERMISSION_MATRIX` single source RBAC | Tránh `role ===` rải rác |
| 2 | 2026-09 | `call<T>(key, real)` boundary | Mocks chỉ khi 404/501 + `VITE_USE_MOCK_FIXTURES=true` |
| 3 | 2026-09 | `dev/mock-api.mjs` Node http | Chạy mọi nơi, không phụ thuộc ServiceWorker |
| 4 | 2026-09 | Station shell Người 5, player Người 4 | Đúng ownership |
| 5 | 2026-09 | Docs `frontend/docs/*.md` + `import.meta.glob` | Source-of-truth markdown, Vite lazy chunks |
| 6 | 2026-09 | Không `DELETE /lanes` Phase 1 | Spec cấm hard delete |
