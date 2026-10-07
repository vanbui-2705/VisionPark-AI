## Why

VisionPark đã chạy YOLO/PaddleOCR và check-in thật, nhưng cấu hình mặc định vẫn cho phép mock, một số màn hình chưa nối đầy đủ với backend và chưa có nghiệm thu bảo toàn dữ liệu Docker. Cần hoàn thiện phần đã triển khai để người dùng sử dụng dữ liệu thật, lưu được lịch sử và nâng cấp ứng dụng mà không mất dữ liệu.

## What Changes

- **BREAKING**: bỏ provider mock, fallback fixture frontend, mock API server, repository giả và ONNX placeholder khỏi mã ứng dụng; cấu hình mock cũ phải báo lỗi rõ ràng. Test doubles chỉ nằm trong thư mục test, không là chế độ chạy ứng dụng.
- Docker mặc định dùng YOLO/PaddleOCR thật; thiếu model hoặc dependency phải báo không sẵn sàng, không sinh biển số giả. Nhập thủ công vẫn hoạt động và được đánh dấu nguồn.
- Station có hai chế độ đầu vào ngang hàng: Ảnh JPEG/PNG và Video MP4 local. Hai chế độ dùng chung model, hiển thị bbox/OCR, sửa/xác nhận biển số và ghi nhận xe vào; lịch sử phân biệt ảnh tải lên với frame video.
- Bảo toàn PostgreSQL và ảnh qua restart, down/up, rebuild và recreate; kiểm kê volume hiện có trước thay đổi, backup/restore đồng bộ và migration không xóa dữ liệu.
- Lưu detection cuối, kết quả OCR, ảnh, xác nhận, giao dịch, audit, thông báo và cấu hình người dùng bằng backend/database. Preview từng frame không lưu mặc định; người dùng lưu kết quả từ trang thử ALPR được bằng thao tác rõ ràng.
- Hoàn thiện phân trang/lọc phía server, metadata làn/hướng, dashboard, hồ sơ, mật khẩu cá nhân, thu hồi phiên, ma trận quyền bốn vai trò, thông báo và Error Center.
- Nghiệm thu model bằng ảnh/video xe thật có nhãn; cập nhật runbook và tài liệu đang mô tả mock.
- Phạm vi là hoàn thiện chức năng hiện có. Xe ra, tính phí, thanh toán, vé tháng, RTSP, barrier, tracking nhiều xe, sửa quyền động, S3 và cháy/khói là các change tiếp theo.

## Capabilities

### New Capabilities
- `durable-operational-data`: lưu dữ liệu thật, bảo toàn database/ảnh trong Docker, backup và restore kiểm chứng được.
- `complete-existing-workflows`: hoàn thiện lịch sử, hồ sơ/phiên, cấu hình, thông báo, lỗi và quyền trên backend thật.
- `real-alpr-acceptance`: luồng model thật, lưu kết quả cuối và nghiệm thu bằng dữ liệu xe thật.

### Modified Capabilities
- `alpr-runtime-boundary`: loại bỏ yêu cầu cung cấp mock runtime trong ứng dụng.

## Impact

Ảnh hưởng cấu hình Compose/env/build, runtime ALPR, storage adapter, migrations, auth/users/audit/parking, frontend API và các màn hình liên quan. PostgreSQL tiếp tục là nguồn dữ liệu chuẩn; database lưu metadata/object key, ảnh lưu volume bền vững. Không thay tên hoặc tạo volume mới thay thế volume đang chứa dữ liệu mà chưa có chuyển đổi kiểm chứng.

Kế hoạch này bổ sung các gate còn mở của `phase-2-alpr-checkin`; không đánh dấu các gate cũ hoàn thành bằng kết quả giả. Các tài liệu mock trước đây giữ làm lịch sử, nhưng hướng dẫn vận hành hiện hành phải chuyển sang real-only.
