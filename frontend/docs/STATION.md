# Station

Route canonical: `/station/scan`; fullscreen cũ redirect về đây.

- Chọn một lane IN hoặc OUT active từ backend; chọn JPEG/PNG hoặc MP4 local.
- Sampling mặc định 1000ms, không queue nhiều inference cùng lúc.
- Preview gửi `persist=false`; giữ tối đa 8 frame ở bộ nhớ phục vụ consensus 2/3.
- Chưa đủ consensus thì cần xác nhận; chuyển làn/video/xe sẽ reset candidate.
- Xác nhận lưu đúng frame candidate ở mode final với capture_id ổn định,
  sau đó POST `/api/v1/alpr/detections/{id}/confirm` với confirmed_plate,
  check_in=true và khóa idempotency ổn định. Retry tái sử dụng detection/key.
- Confirm thành công mới hiện transaction ID và lịch sử DB. Khóa double-click,
  ngừng sampling trong khi confirm và sau success; “Xe tiếp theo” reset phiên.
- Nhập tay độc lập với ALPR gọi `/api/v1/parking/check-in`, source MANUAL_ENTRY.
  Không cần provider ready để tạo manual check-in.

## Phase 4 — VAN-119 đến VAN-123

- IN giữ nguyên check-in. OUT tra phiên bằng biển số, không chọn lại biểu phí.
  Quyền checkout.create dành cho OPERATOR/SYSTEM_ADMIN/BUILDING_ADMIN.
- ALPR OUT lưu đúng final candidate, xác nhận metadata (check_in=false), rồi truyền
  URL ảnh đã lưu sang preview/checkout. Nhập tay tra xe độc lập với ALPR.
- Ảnh vào và ảnh ra hiển thị cạnh nhau, màn hình nhỏ xếp dọc. Ảnh tải bằng Bearer qua
  DetectionImage; thiếu ảnh có thông báo rõ ràng, không dùng ảnh giả.
- Thời điểm vào, ra dự kiến lấy từ server, thời gian gửi theo ngày/giờ/phút và phí VND
  từ preview. Sau checkout hiển thị thời điểm ra thật từ transaction.
- F8 / Xác nhận thu tiền và mở cổng gửi checkout CASH với expected_fee. Backend xử lý
  một chạm, giảm bộ đếm và ghi sự kiện barrier. Retry dùng cùng khóa theo session.
  Không gọi payment API riêng. Phí đã đổi thì cập nhật preview và xác nhận lại.
- Preview xe ra dùng trạng thái `PREVIEW_READY`, chưa phải thành công. UI chỉ chuyển sang
  thành công sau khi backend trả đúng phiên/làn/phí và `barrier_opened=true`. F8/F10 mở
  hộp thoại xác nhận cuối; request checkout chỉ gửi sau khi Operator xác nhận trong dialog.
- Checkout bắt buộc có ảnh xe ra. Tra biển số thủ công vẫn được dùng để tìm phiên nhưng
  nút checkout bị khóa cho đến khi Operator quay lại chụp hoặc chọn ảnh xe ra.
- Xe phí 0 hoặc đã PAID dùng F10 / Mở cổng, không gửi thêm CASH.
- F2 chụp/nhận diện; F4 xác nhận biển số hoặc bản sửa; F9 xe tiếp theo sau thành công.
  Phím tắt dùng cùng nút và điều kiện khóa như click; bỏ qua nhập liệu/dialog/IME,
  phím lặp và tổ hợp bổ trợ. Không đổi làn/nguồn ảnh trong lúc gửi xác nhận/checkout.
- Chỉ báo thành công khi backend trả đúng phiên/làn/phí, trạng thái hoàn tất và
  barrier_opened=true. Lỗi mạng giữ cùng phiên để retry, không giả thành công.

Barrier hiện được backend mô phỏng bằng sự kiện DB; UI nêu rõ giới hạn này.
Chưa có điều khiển barrier vật lý hoặc camera RTSP trong luồng Station.
