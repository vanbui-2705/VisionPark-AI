# Architecture

- Frontend: React 19, Vite 8, React Router 7, TypeScript 6, Vitest 4, oxlint.
- API: `src/api/client.ts` (base URL từ `VITE_API_BASE_URL`, Bearer, timeout mặc định 15s; nhận diện ALPR 60s; ApiError).
- Auth: `AuthContext` + token `visionpark.access_token`.
- Permissions: `src/lib/permissions.ts` (`can()` + `PERMISSION_MATRIX`).

Current runtime: backend API only, ALPR_PROVIDER=real with OCR enabled. Preferences, notifications and error events persist in PostgreSQL.

M4: membership đã xác thực trong M1 và làn xe xác định `building_id`. M4 đăng ký
bộ kiểm tra phiên bản giá hiệu lực cho điều kiện sẵn sàng của bãi. Check-in chọn quy tắc giá hiện hành
và lưu snapshot bất biến vào transaction. Preview và hóa đơn dùng cùng hàm tính
phí thuần; hóa đơn đọc snapshot thay vì bảng giá mới. Đăng ký vé ngày/tháng được
chụp hạn hiệu lực lúc check-in để chỉ tính phần vượt hạn. Thanh toán mock lưu
provider reference và idempotency key; callback xác thực HMAC rồi đối soát với
hóa đơn. Job đối soát đọc các chênh lệch theo tòa nhà.

Phase 4: Station OUT dùng CheckOutService hiện có (modules/checkout), tái sử dụng
API client/Bearer, DetectionImage, VideoPlayer và final candidate. Preview trả thời
điểm server, duration và fee. Checkout CASH một chạm hoàn tất phiên, giảm counter
và ghi barrier event mô phỏng. expected_fee optional chặn phí thay đổi sau preview
trước khi thu tiền; client yêu cầu xem lại phí. Phím tắt kích hoạt các nút đang được
phép thao tác, dùng chung khóa chống submit lặp và idempotency key.
