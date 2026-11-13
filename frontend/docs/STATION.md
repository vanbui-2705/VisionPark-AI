# Station

Route canonical: `/station/scan`; fullscreen cũ redirect về đây.

- Chọn một lane IN hoặc OUT active từ backend; chọn JPEG/PNG hoặc MP4 local.
- Ảnh `.jpg/.jpeg/.png` vẫn được nhận khi trình duyệt không cung cấp MIME type; frontend chuẩn hóa MIME trước khi gửi backend. MP4 được phát local, mỗi frame capture được gửi dưới dạng JPEG với `VIDEO_FRAME` và timestamp.
- Giám sát cháy chạy song song với ALPR: khi video đang phát, Station tự lấy một JPEG tối đa 640 px mỗi 2,5 giây; ảnh tĩnh được kiểm tra cháy cùng lúc người dùng bấm nhận diện. Request dùng `camera_id` cấu hình trên lane (fallback về lane ID), `building_id` của lane và `demo_mode=true`.
- Khi backend trả về `FIRE` hoặc `SMOKE`, Station hiển thị `alertdialog` toàn màn hình và giữ nguyên cho đến khi Operator bấm **ĐÃ NHẬN CẢNH BÁO – TẮT**. Backdrop, Escape và phím tắt Station không tắt cảnh báo. Một sự cố được latch để không bật lại liên tục; monitor chỉ tái kích hoạt sau một frame không còn tín hiệu cháy/khói hoặc khi đổi lane/nguồn ảnh.
- Lỗi riêng của fire runtime không chặn luồng xe và không tạo error-report theo từng frame nền. Demo hiện chỉ cảnh báo tại màn hình, chưa lưu incident, phát âm thanh hay điều khiển thiết bị PCCC.
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
- Nhập tay hỗ trợ CAR/MOTORBIKE bằng biển số và BICYCLE bằng mã vé. Luồng OUT có thể
  tra theo mã vé, đánh dấu mất vé và gửi loại xe thực tế để backend kiểm tra mismatch.

## Phase 4 — VAN-119 đến VAN-123

- IN giữ nguyên check-in. OUT tra phiên bằng biển số, không chọn lại biểu phí.
  Quyền checkout.create dành cho OPERATOR/SYSTEM_ADMIN/BUILDING_ADMIN.
- ALPR OUT lưu đúng final candidate, xác nhận metadata (check_in=false), rồi truyền
  URL ảnh đã lưu sang preview/checkout. Nhập tay tra xe độc lập với ALPR.
- Loại xe từ ALPR (`vehicle_type`, `vehicle_confidence`) được hiển thị và tự điền cho cả IN/OUT; Operator vẫn có thể sửa trước khi xác nhận.
- Khi loại xe vào/ra lệch nhau, Station yêu cầu lý do xác nhận tối thiểu 10 ký tự và gửi `override_reason` để backend lưu audit; không còn dead-end khóa vĩnh viễn checkout.
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
- Preview lại phí giữ nguyên cờ mất vé và loại xe thực tế; phí mất vé được hiển thị rõ
  trong phần tóm tắt trước khi xác nhận checkout.
- F2 chụp/nhận diện; F4 xác nhận biển số hoặc bản sửa; F9 xe tiếp theo sau thành công.
  Phím tắt dùng cùng nút và điều kiện khóa như click; bỏ qua nhập liệu/dialog/IME,
  phím lặp và tổ hợp bổ trợ. Không đổi làn/nguồn ảnh trong lúc gửi xác nhận/checkout.
- Chỉ báo thành công khi backend trả đúng phiên/làn/phí, trạng thái hoàn tất và
  barrier_opened=true. Lỗi mạng giữ cùng phiên để retry, không giả thành công.

Barrier hiện được backend mô phỏng bằng sự kiện DB; UI nêu rõ giới hạn này.
Chưa có điều khiển barrier vật lý hoặc camera RTSP trong luồng Station.
