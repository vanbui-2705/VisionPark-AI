# Deployment

## Dev
```bash
cd frontend
npm install
node dev/mock-api.mjs   # :8000
npm run dev             # Vite
```
Env: `VITE_API_BASE_URL=http://localhost:8000`, `VITE_USE_MOCK_FIXTURES=false`.

## Build
```bash
npm run build   # dist/
npm run preview
```
Checks: `npm run lint`, `npm test` (25 tests).

## Env production
- `VITE_API_BASE_URL` trỏ backend thực; không hard-code URL.
- `VITE_PUBLIC_REGISTRATION_ENABLED=false`.
- Không commit secret thực — chỉ placeholder `JWT_SECRET=<replace-me>`.
