# Station

Route canonical: `/station/scan`; fullscreen cũ redirect về đây.

- Chọn một lane IN active từ backend; chọn MP4 local, play/pause/replay/capture.
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

Không có camera RTSP hoặc điều khiển barrier thật trong phạm vi này.

ALPR_PROVIDER=real; ALPR_OCR_ENABLED=true. Station supports IMAGE_UPLOAD and VIDEO_FRAME; preview is temporary and final captures persist.
