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

## Docker Compose

Từ thư mục gốc repository:

```bash
copy env.example .env
docker compose up --build
```

Frontend được phục vụ bằng Nginx tại `http://localhost:5173`. Nginx chuyển
tiếp `/api/*` và `/health/*` sang FastAPI, vì vậy `VITE_API_BASE_URL=/` cần được
nhúng ở build time. Swagger vẫn có thể truy cập trực tiếp tại
`http://localhost:8000/docs`.

Compose khởi động PostgreSQL, chạy Alembic migration một lần, sau đó mới
khởi động backend và frontend. Dữ liệu PostgreSQL và ảnh upload được giữ
trong named volumes `postgres_data` và `media_data`.

Không dùng các giá trị development trong `env.example` khi triển khai production;
hãy thay database password, JWT secret và mật khẩu tài khoản seed.

## Env production
- `VITE_API_BASE_URL` trỏ backend thực; không hard-code URL.
- `VITE_PUBLIC_REGISTRATION_ENABLED=false`.
- Không commit secret thực — chỉ placeholder `JWT_SECRET=<replace-me>`.
