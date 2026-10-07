# Architecture

- Frontend: React 19, Vite 8, React Router 7, TypeScript 6, Vitest 4, oxlint.
- API: `src/api/client.ts` (base URL từ `VITE_API_BASE_URL`, Bearer, timeout mặc định 15s; nhận diện ALPR 60s; ApiError).
- Auth: `AuthContext` + token `visionpark.access_token`.
- Permissions: `src/lib/permissions.ts` (`can()` + `PERMISSION_MATRIX`).

Current runtime: backend API only, ALPR_PROVIDER=real with OCR enabled. Preferences, notifications and error events persist in PostgreSQL.
