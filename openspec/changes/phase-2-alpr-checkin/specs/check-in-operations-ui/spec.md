## Purpose

Cung cấp giao diện vận hành để nhân viên xử lý kết quả ALPR, xác nhận hoặc sửa biển số và theo dõi các lượt check-in mà không cần thao tác trực tiếp với API.

## ADDED Requirements

### Requirement: Station hiển thị và xác nhận kết quả ALPR

Station MUST cho phép Operator chọn lane `IN`, gửi frame, hiển thị biển số, confidence, bounding box, model version và trạng thái cần xác nhận trước khi tạo check-in.

#### Scenario: Kết quả confidence cao
- **WHEN** API trả kết quả ALPR hợp lệ không yêu cầu sửa
- **THEN** UI hiển thị kết quả và cho phép Operator xác nhận để tạo check-in

#### Scenario: Kết quả cần xác nhận
- **WHEN** API trả no-plate hoặc confidence thấp
- **THEN** UI yêu cầu Operator nhập/sửa biển số trước khi cho phép xác nhận check-in

### Requirement: UI xử lý lỗi và trạng thái request

UI MUST hiển thị rõ trạng thái đang xử lý, thành công, duplicate, unauthorized, provider not ready và lỗi mạng; lỗi một request không được làm mất lane hoặc phiên đăng nhập hiện tại.

#### Scenario: ALPR provider chưa sẵn sàng
- **WHEN** API trả HTTP `503` với lỗi provider not ready
- **THEN** UI hiển thị hướng dẫn chuyển sang manual fallback hoặc thử lại sau

#### Scenario: Check-in bị trùng
- **WHEN** API trả lỗi biển số đang `PARKED`
- **THEN** UI hiển thị cảnh báo giao dịch trùng và không báo thành công giả

### Requirement: Operations xem được lịch sử check-in

Operations UI MUST hiển thị danh sách check-in với biển số, lane, thời điểm, trạng thái, nguồn xác nhận và người thực hiện; danh sách MUST hỗ trợ tối thiểu lọc theo biển số, lane và khoảng thời gian.

#### Scenario: Xem lịch sử theo lane
- **WHEN** Operator hoặc Admin chọn một lane và khoảng thời gian
- **THEN** UI chỉ hiển thị các check-in phù hợp và giữ thông tin trạng thái xác nhận
