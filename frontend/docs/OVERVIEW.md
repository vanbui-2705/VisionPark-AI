# VisionPark — Overview

React portal cho Station và quản trị, nối FastAPI/PostgreSQL.
Chạy local qua Docker Compose; dữ liệu parking, lane, users và audit thuộc DB.

Phase 2 hiện có ảnh JPEG/PNG và video MP4, ALPR preview/final, consensus 2/3, xác nhận/sửa/nhập
biển số thủ công, check-in PARKED, duplicate/idempotency, lịch sử/audit.
Backend chỉ hỗ trợ YOLO/PaddleOCR thật; frontend không còn fixture fallback hay mock API.

ADMIN quản trị; OPERATOR vận hành và đọc lanes. ACCOUNTANT đọc dashboard,
parking và audit; TECHNICIAN dùng Station/check-in, detection và trang trạng thái.

Profile, preferences, notifications và lỗi đã lưu database. Model readiness, video demo thật và
accuracy/latency benchmark là các mức xác minh riêng. Check-out/payment/barrier,
RTSP/vé tháng nằm ngoài phạm vi hiện tại.
