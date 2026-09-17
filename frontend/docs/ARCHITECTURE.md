# Architecture

- Frontend: React 19, Vite 8, React Router 7, TypeScript 6, Vitest 4, oxlint.
- API: `src/api/client.ts` (base URL từ `VITE_API_BASE_URL`, Bearer, 15s timeout, ApiError).
- Auth: `AuthContext` + token `visionpark.access_token`.
- Permissions: `src/lib/permissions.ts` (`can()` + `PERMISSION_MATRIX`).
- Mock server: `dev/mock-api.mjs` (Node http, chỉ dev).
- Service boundary: `call<T>(key, real)` fallback sang `mocks/fixtures.ts` chỉ khi 404/501 và `VITE_USE_MOCK_FIXTURES=true`.
