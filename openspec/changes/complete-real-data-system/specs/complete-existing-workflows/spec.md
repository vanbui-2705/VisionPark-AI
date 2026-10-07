## Purpose

Hoàn thiện các màn hình nghiệp vụ đã tồn tại bằng API và dữ liệu bền vững, loại bỏ thao tác chỉ có giao diện hoặc bị giới hạn bởi dữ liệu mẫu.

## ADDED Requirements

### Requirement: History filtering and pagination use complete server data
Lịch sử nhận diện/gửi xe và audit theo người dùng/tài nguyên MUST lọc và phân trang trên server, trả tổng số phù hợp, metadata làn/hướng và actor khi có quyền. Dashboard MUST dùng tổng số database và có cách làm mới rõ ràng.

#### Scenario: Matching record is beyond first two hundred records
- **WHEN** người dùng tìm một bản ghi nằm ngoài 200 bản ghi đầu
- **THEN** bản ghi vẫn xuất hiện khi khớp bộ lọc, tổng số và phân trang phản ánh toàn bộ tập dữ liệu phù hợp

### Requirement: Personal profile and session management work
Người dùng MUST sửa thông tin cá nhân và đổi mật khẩu bằng API có xác thực, kiểm tra mật khẩu hiện tại. Admin có quyền MUST thu hồi phiên của tài khoản; token đã thu hồi MUST không gọi được API bảo vệ. Thao tác MUST có audit không chứa mật khẩu/token.

#### Scenario: Administrator revokes a user session
- **WHEN** admin thu hồi phiên tài khoản khác
- **THEN** token cũ bị từ chối ở request bảo vệ tiếp theo và giao diện chuyển về đăng nhập

### Requirement: User preferences are persistent and applied
Theme/ngôn ngữ được hỗ trợ MUST áp dụng toàn ứng dụng và lưu theo tài khoản ở backend; frontend MUST phản ánh preference sau đăng nhập hoặc reload. Tên hiển thị MUST cập nhật hồ sơ thật.

#### Scenario: Preferences survive browser storage clear
- **WHEN** người dùng lưu theme/ngôn ngữ, xóa localStorage rồi đăng nhập lại
- **THEN** ứng dụng đọc preference đã lưu và áp dụng lựa chọn tương ứng

### Requirement: Operational notifications are persistent and authorized
Thông báo MUST được tạo từ sự kiện nghiệp vụ/lỗi thật, lưu người nhận và trạng thái đọc, chỉ hiển thị cho tài khoản có quyền. Polling là cơ chế cập nhật của đợt này.

#### Scenario: Notification read state persists
- **WHEN** người dùng đánh dấu thông báo đã đọc rồi reload hoặc đăng nhập trên trình duyệt khác
- **THEN** trạng thái đã đọc giữ nguyên và tài khoản khác không đọc được thông báo riêng này

### Requirement: Error center uses real sanitized errors
Error Center MUST đọc lỗi thật đã lưu, có thời gian, correlation ID, loại lỗi và quyền truy cập. Tiếp nhận lỗi frontend MUST giới hạn tần suất/kích thước và loại bỏ token, mật khẩu, ảnh hoặc payload nhạy cảm; MUST không dùng cơ chế báo lỗi để gây vòng lặp lỗi.

#### Scenario: Client error survives reload without secrets
- **WHEN** client ghi nhận lỗi API và reload trang
- **THEN** tài khoản có quyền vẫn tra được lỗi đã lưu và bản ghi không chứa thông tin xác thực

### Requirement: Four roles have consistent visible permissions
API và giao diện MUST thống nhất quyền của ADMIN, OPERATOR, ACCOUNTANT, TECHNICIAN; ma trận MUST thể hiện đủ bốn vai trò và các màn hình hiện có được phép truy cập. Chưa bổ sung chỉnh quyền động hoặc nghiệp vụ kế toán/kỹ thuật mới.

#### Scenario: Unauthorized mutation
- **WHEN** tài khoản chỉ có quyền đọc gọi API thay đổi dữ liệu
- **THEN** backend từ chối dù client tự gửi request bỏ qua giao diện

### Requirement: Lane source capabilities are represented honestly
Làn MUST lưu nguồn video đúng định dạng được hỗ trợ và giao diện MUST phân biệt video MP4 local đang xử lý với địa chỉ camera chưa tích hợp. Không tuyên bố camera connected dựa trên một chuỗi video_source đã lưu.

#### Scenario: Camera address configured without streaming integration
- **WHEN** làn có địa chỉ RTSP nhưng hệ thống chưa hỗ trợ streaming
- **THEN** giao diện hiển thị trạng thái chưa hỗ trợ, không báo camera đang kết nối
