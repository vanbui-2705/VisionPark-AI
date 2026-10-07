# Deployment local

Copy root env.example → .env, sinh JWT_SECRET_KEY riêng, chạy
`docker compose up --build -d`. Migration dùng cùng image backend và phải hoàn
thành trước backend. Không xóa volumes khi cập nhật bản build.

Port mặc định frontend 5173/backend 8000/DB 5433, override bằng .env.
VITE_API_BASE_URL=/ trong Compose; nginx proxy /api và /health.

Real Docker: INSTALL_REAL_ALPR=true, INSTALL_OCR=true,
ALPR_PROVIDER=real, ALPR_OCR_ENABLED=true; provision manifest/weights và OCR
cache ngoài Git. Build có thể cần tài nguyên lớn. Mock là baseline local/CI.

Current runtime: backend API only, ALPR_PROVIDER=real with OCR enabled. Preferences, notifications and error events persist in PostgreSQL.
