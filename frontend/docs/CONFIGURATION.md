# Configuration

VITE_API_BASE_URL: origin backend, không chứa /api/v1; / cho Compose.
VITE_API_TIMEOUT_MS: 15000 mặc định.
PUBLIC_REGISTRATION_ENABLED và VITE_PUBLIC_REGISTRATION_ENABLED: false mặc định;
phải bật cả backend và build frontend nếu cho phép đăng ký OPERATOR.

INSTALL_REAL_ALPR và INSTALL_OCR chọn optional dependency ở Docker build.

Secret chỉ lưu trong .env bị gitignore. Không copy credential/token vào docs.

RBAC frontend cấu hình tĩnh trong `src/lib/permissions.ts` qua `PERMISSION_MATRIX`; `can()` dùng cùng ma trận. Không có biến môi trường để nới quyền. Backend vẫn kiểm tra role cho từng API.

ALPR_PROVIDER=real; ALPR_OCR_ENABLED=true. Station supports IMAGE_UPLOAD and VIDEO_FRAME; preview is temporary and final captures persist.

Current runtime: backend API only, ALPR_PROVIDER=real with OCR enabled. Preferences, notifications and error events persist in PostgreSQL.
