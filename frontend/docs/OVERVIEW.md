# VisionPark — Overview

React portal cho Station và quản trị, nối FastAPI/PostgreSQL.
Chạy local qua Docker Compose; dữ liệu parking, lane, users và audit thuộc DB.

Phase 2 hiện có ảnh JPEG/PNG và video MP4, ALPR preview/final, consensus 2/3, xác nhận/sửa/nhập
biển số thủ công, check-in PARKED, duplicate/idempotency, lịch sử/audit.
Backend chỉ hỗ trợ YOLO/PaddleOCR thật; frontend không còn fixture fallback hay mock API.

Các role hiện hành là SYSTEM_ADMIN, BUILDING_ADMIN, OPERATOR và ACCOUNTANT.
SYSTEM_ADMIN quản trị toàn hệ thống; BUILDING_ADMIN quản trị dữ liệu/cấu hình trong tòa nhà;
OPERATOR vận hành Station; ACCOUNTANT đọc dashboard, parking và audit tài chính.

Profile, preferences, notifications và lỗi đã lưu database. Model readiness, video demo thật và
accuracy/latency benchmark là các mức xác minh riêng.

Phase 4 Station hỗ trợ IN/OUT, đối chiếu ảnh vào/ra, thời gian gửi và phí từ snapshot,
xác nhận CASH, checkout và phím tắt. Barrier được backend mô phỏng bằng sự kiện;
chưa điều khiển thiết bị vật lý. Vé tháng có danh mục khu vực, hạng khách hàng và quy tắc
cho phép/từ chối xe theo từng tòa nhà. Chi tiết trong `STATION.md`. RTSP chưa được hỗ trợ.
