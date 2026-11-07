# API Contract — Phase 2

Nguồn: `src/api/client.ts`, `src/api/services.ts`, OpenAPI backend tại `/docs`.
Base URL là origin backend (`VITE_API_BASE_URL`), không chứa `/api/v1`.
Trong Compose dùng `/` để đi qua reverse proxy cùng origin.

- Auth: POST `/api/v1/auth/login`, GET `/api/v1/auth/me`.
- Register: POST `/api/v1/auth/register`, mặc định tắt trên backend; nếu bật chỉ nhận username/display_name/email/password, server gán OPERATOR.
- Lanes: GET/POST `/api/v1/lanes/`, GET `/api/v1/lanes/active`, GET/PATCH `/api/v1/lanes/{id}`, POST `/api/v1/lanes/{id}/deactivate`. Không DELETE.
- Users (ADMIN): GET/POST `/api/v1/users`, GET/PATCH `/api/v1/users/{id}`, GET `/api/v1/roles`.
- ALPR: POST `/api/v1/alpr/detections` multipart JPEG/PNG, lane_id, mode, persist. Preview không lưu; final có capture_id UUID để retry cùng frame không tạo detection mới.
- Detection history: GET `/api/v1/alpr/detections` với q/lane_id/direction/status/from/to/skip/limit; GET `/api/v1/alpr/detections/{id}`. ADMIN/OPERATOR/TECHNICIAN được đọc và xác nhận detection.
- Confirm: POST `/api/v1/alpr/detections/{id}/confirm` với `confirmed_plate`; thêm `check_in=true` và `Idempotency-Key` để tạo transaction cùng audit. Reply khi check-in là `{transaction,message}`; metadata-only trả DetectionResponse.
- Parking: POST `/api/v1/parking/check-in` cho ADMIN/OPERATOR/TECHNICIAN; GET `/api/v1/parking/transactions`, GET `/api/v1/parking/transactions/{id}` và GET `/api/v1/parking/summary` cho ADMIN/OPERATOR/ACCOUNTANT. Summary trả `{total,parked,manual}` từ DB. Danh sách transactions trả array mặc định; khi `paginated=true` hoặc có `page`/`pageSize`, trả object có `items`, `data`, `total`, `page`, `pageSize`, `totalPages`, `limit`, `offset`.
- Audit: GET `/api/v1/audit-logs/` cho ADMIN/OPERATOR/ACCOUNTANT; menu audit hiển thị cho ADMIN/ACCOUNTANT. Danh sách audit trả array mặc định; khi `paginated=true` hoặc có `page`/`pageSize`, trả cùng cấu trúc phân trang như transactions.
- Health: GET `/health/live`, `/health/ready`; readiness trả status ready/not_ready, provider/version/ocr_enabled.

Service adapter chuyển `is_active` → `active`, raw_plate → ai_plate,
confirmed_plate → final_plate và flags → status. Bbox history dùng pixel,
hiển thị được scale theo natural image dimensions. Auth giữ đủ bốn role;
ACCOUNTANT/TECHNICIAN không được suy ra thành OPERATOR.

Errors: `{code,message,details,correlation_id}`; 401 xóa token, 403 giữ phiên,
503 cho phép retry/manual. FormData không tự đặt Content-Type. Tất cả Station
requests dùng client và token `visionpark.access_token` chung.

# Phase 3 building isolation (VAN-60)

Authenticated requests resolve the building from the signed token and current server membership.
Client-supplied building IDs cannot widen access. Detection images under `/api/v1/alpr/media/`
now require Bearer authentication; `DetectionImage` loads them with `apiClient.getBlob`, displays
a temporary object URL, and revokes it on cleanup. Local Station previews remain local blob URLs.

## Phase 3 M4

- `POST/GET /api/v1/buildings`: SYSTEM_ADMIN tạo; BUILDING_ADMIN thao tác trong membership của mình.
- `/api/v1/pricing/customer-classes`, `/ticket-products`, `/versions`: GET theo tòa nhà; BUILDING_ADMIN tạo và cập nhật class/product. Phiên bản giá chỉ thêm mới.
- Check-in và xác nhận ALPR trên làn đã gán tòa nhà gửi thêm `vehicle_type`, `ticket_kind`, `customer_class_id` và `zone_id` khi cần chọn gói; backend chụp snapshot giá và hạn vé đăng ký đang hiệu lực. Station chọn thông tin này trước khi tạo giao dịch.
- Check-in thủ công cho xe đạp có thể gửi `ticket_code` thay cho `license_plate`; hệ thống tra đăng ký theo mã vé.
- `POST /api/v1/pricing/preview`: tính phí từ quy tắc hiện hành; `GET /active` lấy snapshot đang áp dụng.
- `/api/v1/tickets/vehicles`, `/quotas`, `/subscriptions`, `/guest-invites`, `/access`: quản lý vé và tra quyết định ALLOW/DENY/REVIEW. `POST /vehicles/import` nhận CSV tối đa 1 MB/1000 dòng.
- `/api/v1/m5/cash-shifts`: tổng hợp lượt vào, lượt ra và tiền mặt đã thanh toán trong khoảng `start`/`end` có timezone; `/api/v1/lifecycle/sessions/export-csv` xuất danh sách lượt xe theo bộ lọc thời gian.
- `/api/v1/settings/lot` GET/PUT: đọc và cập nhật sức chứa an toàn theo loại xe, với kiểm soát revision.
- `POST/GET /api/v1/invoices`: tạo hóa đơn từ snapshot lúc check-in; phụ thu là dòng riêng.
- `POST /api/v1/payments` cần `Idempotency-Key`; `GET /payments/{id}` để polling; `GET /payments/reconcile` cho BUILDING_ADMIN. Callback mock `POST /payments/callback` cần HMAC-SHA256 trên raw body trong header `X-Mock-Signature`, dùng `MOCK_VIETQR_CALLBACK_SECRET`.
- Job đối soát chạy một lần: `python scripts/reconcile_m4_payments.py --building-id <UUID>` từ thư mục `backend`; mã thoát 1 khi có chênh lệch.

## Phase 4 Station OUT

- POST /api/v1/parking/check-out/preview nhận license_plate (hoặc session_id), exit_lane_id,
  exit_image_url optional. Trả biển số, ảnh vào/ra, check_in_time và exit_time có múi giờ,
  duration_minutes, fee, fee_breakdown, status. Preview không đóng phiên.
- OUT final detection dùng confirm với check_in=false. URL ảnh đã lưu được truyền vào
  preview và checkout; không tạo check-in trên làn OUT.
- POST /api/v1/parking/check-out nhận session_id, exit_lane_id, exit_image_url optional,
  payment_method=CASH và expected_fee. Khóa ổn định: station-exit-<session_id>.
  CASH một chạm ghi nhận thanh toán, hoàn tất phiên và mở barrier mô phỏng. Xe phí 0
  hoặc trạng thái PAID không gửi CASH. Không gọi thêm /payments để tránh ghi nhận hai lần.
- expected_fee optional không ảnh hưởng caller cũ. Phí khác số đã hiển thị trả 409
  FEE_CHANGED trước khi thu tiền; phải cập nhật preview và xác nhận lại phí mới.
- Thành công trả transaction, fee, status, barrier_opened, message. Frontend chỉ báo
  hoàn tất khi đúng phiên/làn/phí, trạng thái COMPLETED/EXITED và barrier_opened=true.
- Quyền backend: OPERATOR/SYSTEM_ADMIN/BUILDING_ADMIN; frontend dùng checkout.create.
  Barrier chỉ ghi sự kiện mô phỏng, chưa điều khiển thiết bị vật lý.
