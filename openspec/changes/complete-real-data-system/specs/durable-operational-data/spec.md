## Purpose

Bảo đảm dữ liệu nghiệp vụ thật và ảnh liên quan tồn tại bền vững, truy xuất được sau khi cập nhật hoặc khởi động lại hệ thống Docker.

## ADDED Requirements

### Requirement: Operational records are durable
Hệ thống MUST lưu tài khoản, làn, detection cuối, xác nhận, giao dịch, audit, cấu hình và thông báo nghiệp vụ đã ghi nhận trong database bền vững. Ảnh MUST được lưu bền vững với object key trong database. Preview MUST không tự tạo giao dịch hoặc lưu mọi frame.

#### Scenario: Saved detection survives application restart
- **WHEN** người dùng lưu detection hoặc xác nhận check-in rồi khởi động lại backend/frontend
- **THEN** bản ghi, ảnh, biển số gốc/cuối, nguồn, người thực hiện và liên kết giao dịch vẫn truy xuất được

#### Scenario: Preview is transient
- **WHEN** Station gửi nhiều frame preview mà chưa lưu hoặc xác nhận
- **THEN** hệ thống không tạo giao dịch hoặc lịch sử detection cho mỗi frame

### Requirement: Docker lifecycle preserves existing data
Hệ thống MUST giữ database và ảnh qua restart, down/up không xóa volume, rebuild và recreate. Nâng cấp MUST nhận diện và tiếp tục dùng volume hiện có hoặc chuyển đổi có kiểm chứng; MUST không âm thầm kết nối database rỗng thay thế.

#### Scenario: Rebuild and recreate preserve identifiers
- **WHEN** vận hành rebuild và recreate các container trên cùng bộ dữ liệu
- **THEN** ID và nội dung các bản ghi đã tồn tại cùng checksum ảnh vẫn giữ nguyên

### Requirement: Upgrade and bootstrap do not overwrite user data
Migration MUST bảo toàn bản ghi nghiệp vụ; bootstrap MUST không tạo dữ liệu nghiệp vụ giả, đổi mật khẩu hoặc ghi đè cấu hình người dùng đã tồn tại. Test và cleanup MUST dùng database/storage riêng.

#### Scenario: Existing account is not reset
- **WHEN** ứng dụng chạy bootstrap sau một lần nâng cấp
- **THEN** mật khẩu, vai trò và thông tin tài khoản đã chỉnh sửa vẫn giữ nguyên

### Requirement: Recoverable database and media backup
Vận hành MUST có quy trình backup nhất quán database và ảnh, lưu phiên bản schema và kiểm tra khả năng restore trên môi trường riêng trước thay đổi lưu trữ hoặc migration rủi ro. Không tự động xóa dữ liệu/ảnh trong đợt hoàn thiện này.

#### Scenario: Restore into isolated environment
- **WHEN** phục hồi một bộ backup vào database và storage riêng
- **THEN** các bản ghi tham chiếu ảnh đều đọc được và kết quả kiểm tra ID, số lượng cùng checksum ảnh khớp thời điểm backup
