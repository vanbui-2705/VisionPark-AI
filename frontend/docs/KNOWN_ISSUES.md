# Known Issues

| # | Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|--------|-----------|-------------|
| 1 | `GET /api/v1/detections` chỉ hỗ trợ `lane_id` + `limit` | Filter date/confidence client-side | Backend bổ sung query params |
| 2 | `POST /api/v1/users` fixture throw 501 khi mock | Không fake success; UI "API pending" | Backend triển khai users API |
| 3 | Warnings `set-state-in-effect` | Không chặn build; pattern fetch-on-mount | Giữ nguyên |
| 4 | Windows case-insensitive FS | Alias uppercase là file riêng | Đã tạo alias |

Không tạo số giả — chỉ ghi metadata thực.
