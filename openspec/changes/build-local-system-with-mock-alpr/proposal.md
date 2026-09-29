## Why

VisionPark cần một lát cắt Phase 1 chạy ổn định trên local để năm thành viên phát triển song song mà không phải chờ model YOLO/OCR. Hệ thống phải kiểm chứng được luồng đăng nhập, quản lý làn, gửi frame, nhận kết quả ALPR giả lập, lưu kết quả và xác nhận thủ công trước khi thay mock bằng model thật.

## What Changes

- Khởi tạo FastAPI modular monolith, PostgreSQL, migration và seed dữ liệu demo.
- Triển khai authentication JWT và RBAC thật cho `ADMIN` và `OPERATOR`.
- Triển khai Lane CRUD thật với hướng `IN/OUT` và inactive thay vì hard delete.
- Tích hợp `ALPRRuntime` qua provider `mock`, nhận ảnh thật nhưng trả kết quả nhận diện tất định.
- Giao Người 1 sở hữu AI Core và `POST /api/v1/alpr/detections`; Người 3 cung cấp Lane/storage/persistence adapters và sở hữu history/confirmation.
- Lưu frame qua storage adapter, lưu metadata/kết quả nhận diện/xác nhận trong PostgreSQL.
- Triển khai Station phát MP4, lấy frame có throttle, hiển thị bbox/kết quả và cho nhân viên xác nhận hoặc sửa biển số.
- Triển khai Login và Admin Lane UI dùng API thật.
- Đóng gói frontend, backend và PostgreSQL bằng Docker Compose; bổ sung kiểm thử và hướng dẫn clean setup.
- Không tích hợp OCR trong Phase 1. Model YOLO `.pt` chỉ được chạy tùy chọn ở chế độ detector-only để trả bounding box và confidence; biển số vẫn cần xác nhận thủ công. PaddleOCR được hoãn sang Phase 2.

## Capabilities

### New Capabilities

- `local-runtime`: Hệ thống frontend, backend và PostgreSQL khởi động ổn định trên local với health/readiness rõ ràng.
- `user-auth-rbac`: Đăng nhập JWT, current user và phân quyền `ADMIN`/`OPERATOR` tại backend và frontend.
- `lane-management`: Quản lý làn `IN/OUT` qua migration, seed, API và Admin UI.
- `mock-alpr-detection`: Nhận frame, gọi mock ALPR qua runtime boundary, lưu ảnh/metadata và trả response theo contract.
- `plate-confirmation`: Lưu quyết định biển số đúng hoặc biển số được nhân viên sửa cùng dấu vết người xác nhận.
- `station-video-workflow`: Station phát MP4, lấy mẫu frame có kiểm soát và hiển thị đầy đủ trạng thái ALPR.

### Modified Capabilities

- Không có.

## Impact

- Tạo mới code dưới `backend`, `frontend`, migration, test, `compose.yaml` và cấu hình local.
- Thêm public API cho auth, lane, ALPR detection, confirmation và health.
- Thêm các bảng role, user, lane, media object và ALPR detection trong PostgreSQL.
- Frontend dùng một router/auth context/API client chung cho Station và Admin.
- Change phụ thuộc contract của `scaffold-alpr-boundary` nhưng không phụ thuộc model weight.
