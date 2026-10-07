## Purpose

Đảm bảo nhận diện trong ứng dụng dùng model thật, kết quả được lưu rõ ràng và chất lượng được đánh giá trên ảnh/video xe thật có nhãn.

## ADDED Requirements

### Requirement: Station supports image and video recognition
Station MUST cung cấp hai chế độ Ảnh JPEG/PNG và Video MP4 local dùng chung model thật, hiển thị bbox/biển số/confidence, cho sửa/xác nhận và ghi nhận xe vào bằng cùng luồng nghiệp vụ. Chế độ ảnh MUST xử lý ảnh được chọn; chế độ video MUST xử lý frame thủ công hoặc lấy mẫu tự động. Lỗi file MUST được báo rõ và không tạo giao dịch.

#### Scenario: Recognize and confirm an uploaded image
- **WHEN** Operator chọn làn, chọn chế độ Ảnh, tải JPEG/PNG hợp lệ và bấm Nhận diện rồi xác nhận biển số
- **THEN** hệ thống nhận diện ảnh thật, lưu đúng ảnh/kết quả cuối và tạo đúng một giao dịch cùng audit

#### Scenario: Recognize and confirm a video frame
- **WHEN** Operator chọn chế độ Video, mở MP4 local và chọn kết quả từ frame thủ công hoặc sampling
- **THEN** hệ thống dùng frame đó cho nhận diện/lưu/xác nhận, không tạo giao dịch cho mỗi frame hoặc upload toàn video để lưu mặc định

#### Scenario: Switch input while recognition is pending
- **WHEN** Operator đổi giữa Ảnh và Video hoặc chọn file khác khi nhận diện đang chờ
- **THEN** sampling/candidate cũ được dừng/reset và response cũ không thể xác nhận trong ngữ cảnh mới

### Requirement: Recognition history identifies input type
Detection cuối MUST lưu loại đầu vào ảnh tải lên hoặc frame video tách biệt với nguồn quyết định AI/sửa tay/manual; lịch sử MUST hiển thị và lọc được loại này. Dữ liệu cũ không xác định MUST giữ unknown.

#### Scenario: Filter image recognition history
- **WHEN** người dùng lọc lịch sử theo ảnh tải lên
- **THEN** backend trả các detection có loại đầu vào tương ứng, ảnh và metadata vẫn truy xuất được sau restart

### Requirement: Application uses real recognition exclusively
Ứng dụng và Docker MUST chỉ nhận diện bằng model thật, không có chế độ trả biển số cố định hay fallback dữ liệu mẫu. Cấu hình mock cũ MUST bị từ chối rõ ràng. Test doubles MUST chỉ dùng trong môi trường test riêng.

#### Scenario: Model unavailable
- **WHEN** model hoặc OCR chưa sẵn sàng
- **THEN** readiness báo lỗi và yêu cầu nhận diện trả lỗi phù hợp, không trả biển số giả; nhập thủ công được phép và ghi nguồn MANUAL_ENTRY

### Requirement: User can explicitly save recognition results
Station final capture và thao tác lưu trên trang thử ALPR MUST lưu detection/ảnh thật; confirmation MUST tạo đúng một giao dịch và audit liên quan bằng thao tác nguyên tử có idempotency. Nhận diện no-plate MUST không tự tạo check-in.

#### Scenario: Save recognition from test page
- **WHEN** người dùng có quyền chọn lưu một kết quả nhận diện ảnh với làn hợp lệ
- **THEN** hệ thống trả ID detection và lịch sử đọc được ảnh, OCR gốc, confidence, bbox và phiên bản model thực tế mà không tạo giao dịch gửi xe

#### Scenario: Repeated confirmation
- **WHEN** client gửi lại xác nhận cùng idempotency key và payload
- **THEN** backend trả cùng giao dịch đã tạo, không thêm giao dịch hoặc audit xác nhận trùng

### Requirement: Real data release evidence
Nghiệm thu ALPR MUST dùng ảnh/video xe thật có ground truth, phân tách theo xe/video; báo cáo MUST có exact match, character accuracy, no-result, false-positive, cold/warm p50/p95, phần cứng, phiên bản model và time-to-stable trên video. Kết quả giả hoặc ảnh chữ dựng MUST không được dùng để kết luận đạt chất lượng nhận diện xe thật.

#### Scenario: Missing labelled real dataset
- **WHEN** chưa có bộ ảnh/video xe thật đủ nhãn để chạy đánh giá
- **THEN** trạng thái nghiệm thu chất lượng còn mở và báo cáo ghi rõ thiếu dữ liệu, dù readiness hoặc kiểm tra API đã thành công

### Requirement: Station does not reuse stale recognition
Station MUST hủy/bỏ kết quả cũ khi đổi chế độ Ảnh/Video, đổi làn, đổi file hoặc chuyển xe; MUST giới hạn request đang xử lý và yêu cầu người vận hành xác nhận kết quả không ổn định.

#### Scenario: Lane changes while recognition is pending
- **WHEN** người dùng đổi làn hoặc video khi request trước chưa xong
- **THEN** response cũ không thể được dùng để ghi nhận xe vào cho ngữ cảnh mới
