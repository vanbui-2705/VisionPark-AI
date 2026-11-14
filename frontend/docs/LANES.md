# Lanes


- Routes: `/admin/lanes` (list), `/admin/lanes/new` (create), `/admin/lanes/:id` (detail), `/admin/lanes/:id/edit` (edit). Không có DELETE (Phase 1).
- Form: `name`, `direction` (IN/OUT), nguồn nhận diện, danh sách loại xe được phép, `camera_id`, `barrier_id`, `active`.
- Nguồn `FILE_UPLOAD` dùng ảnh/video chọn tại Station. Có thể lưu URL RTSP để chuẩn bị cấu hình nhưng runtime RTSP chưa được tích hợp; giao diện nêu rõ giới hạn này.
- `allowed_vehicle_types` là cấu hình chính; backend vẫn đọc `allowed_vehicle_type` cũ để tương thích dữ liệu legacy. Form bắt buộc ít nhất một loại xe.
- Detail hiển thị metadata + audit. List có filter/search + pagination. Guard `useUnsavedGuard` khi dirty.

Current runtime: backend API only, ALPR_PROVIDER=real with OCR enabled. Preferences, notifications and error events persist in PostgreSQL.
