## Purpose

Cho phép VisionPark chạy detector/OCR thật qua ALPR runtime boundary, có thể đo lường và chuyển đổi an toàn giữa mock provider và real provider.

## ADDED Requirements

### Requirement: Real provider tuân thủ ALPR runtime contract

Real provider MUST nhận frame hợp lệ qua runtime interface hiện có và trả về cùng cấu trúc kết quả ALPR như mock provider, bao gồm plate, bounding box, confidence, latency, model version và cờ yêu cầu xác nhận.

#### Scenario: Real provider đọc được biển số
- **WHEN** provider được bật và nhận frame hợp lệ có biển số
- **THEN** hệ thống trả kết quả chuẩn hóa theo ALPR contract và ghi đúng `model_version` của provider

#### Scenario: Real provider không đọc được biển số
- **WHEN** provider nhận frame hợp lệ nhưng không tìm thấy hoặc không đọc được biển số
- **THEN** hệ thống trả kết quả không có biển số với `requires_confirmation=true` và không làm crash request

### Requirement: Provider readiness phản ánh model thật

Real provider MUST báo `not_ready` khi bị tắt, thiếu model, sai manifest hoặc không load được dependency; provider chỉ được báo ready sau khi kiểm tra model và manifest thành công.

#### Scenario: Thiếu model weight
- **WHEN** real provider được cấu hình nhưng model weight không tồn tại
- **THEN** readiness là false và request inference trả lỗi typed tương ứng với HTTP `503`

#### Scenario: Model load thành công
- **WHEN** model, manifest và dependency hợp lệ
- **THEN** readiness là true và health response chứa tên/phiên bản model đang chạy

### Requirement: Model manifest và benchmark phải tái lập được

Phase 2 MUST có manifest ghi model version, loại detector/OCR, đường dẫn ngoài Git và checksum khi có; benchmark MUST dùng dataset split cố định và xuất báo cáo nhận diện cùng latency mà không yêu cầu GPU trong CI.

#### Scenario: Chạy benchmark trên dataset cố định
- **WHEN** thành viên chạy benchmark với cùng manifest và dataset split
- **THEN** báo cáo chứa số mẫu, kết quả detection/OCR, lỗi/no-plate và latency summary

#### Scenario: CI không có model weight
- **WHEN** CI chạy test trên clean checkout
- **THEN** test dùng mock provider deterministic và không tải weight thật hoặc yêu cầu GPU
