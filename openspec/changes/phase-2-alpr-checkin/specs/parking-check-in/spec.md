## Purpose

Cung cấp luồng ghi nhận xe vào bãi có xác nhận của người vận hành, chống giao dịch trùng và lưu được lịch sử/audit để làm nền cho check-out và tính phí về sau.

## ADDED Requirements

### Requirement: Tạo giao dịch check-in hợp lệ

Hệ thống MUST cho phép người dùng đã xác thực tạo check-in cho một lane `IN` đang active bằng biển số đã chuẩn hóa và kết quả ALPR hoặc xác nhận thủ công. Giao dịch thành công MUST có trạng thái `PARKED`, lane, biển số, thời điểm và liên kết tới detection nếu có.

#### Scenario: Check-in bằng kết quả ALPR đã xác nhận
- **WHEN** Operator gửi kết quả ALPR hợp lệ cho lane `IN` active và xác nhận biển số
- **THEN** hệ thống tạo một parking transaction trạng thái `PARKED` và trả transaction identifier

#### Scenario: Check-in bằng biển số nhập tay
- **WHEN** ALPR không có kết quả hoặc confidence thấp và Operator nhập biển số hợp lệ rồi xác nhận
- **THEN** hệ thống tạo giao dịch `PARKED`, đánh dấu nguồn xác nhận thủ công và lưu giá trị ALPR ban đầu nếu có

### Requirement: Từ chối check-in không hợp lệ

Hệ thống MUST từ chối request nếu người dùng chưa xác thực, lane không phải `IN`, lane inactive, biển số sau chuẩn hóa rỗng hoặc biển số đang có giao dịch `PARKED`.

#### Scenario: Lane không hoạt động
- **WHEN** Operator gửi check-in vào lane inactive
- **THEN** API trả lỗi validation/conflict phù hợp và không tạo transaction

#### Scenario: Biển số đang ở trong bãi
- **WHEN** Operator gửi check-in cho biển số đã có transaction `PARKED`
- **THEN** API trả lỗi duplicate/conflict và giữ nguyên transaction hiện có

### Requirement: Check-in có idempotency

Hệ thống MUST hỗ trợ `Idempotency-Key` cho request check-in. Cùng key và cùng payload MUST trả lại kết quả đã tạo; cùng key nhưng payload khác MUST bị từ chối và không tạo thêm giao dịch.

#### Scenario: Retry cùng request
- **WHEN** client gửi lại cùng payload với cùng `Idempotency-Key`
- **THEN** hệ thống trả cùng transaction identifier và không tạo bản ghi thứ hai

#### Scenario: Key dùng cho payload khác
- **WHEN** client dùng lại một key với biển số hoặc lane khác
- **THEN** API trả lỗi conflict và không thay đổi dữ liệu check-in

### Requirement: Lưu audit cho quyết định check-in

Hệ thống MUST lưu người thực hiện, thời điểm, lane, biển số AI, biển số cuối cùng, nguồn xác nhận và kết quả của mỗi thao tác check-in hoặc sửa/xác nhận biển số.

#### Scenario: Operator sửa biển số trước khi check-in
- **WHEN** Operator thay đổi biển số ALPR rồi xác nhận check-in
- **THEN** transaction lưu biển số cuối cùng và audit lưu cả biển số AI, người sửa và thời điểm sửa
