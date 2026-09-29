## Context

Repository đang ở trạng thái triển khai dở dang; ALPR boundary đã được đề xuất trong change `scaffold-alpr-boundary`, backend/frontend/database đã có các phần nền tảng nhưng còn lỗi migration, fixture và integration. Kiến trúc chuẩn là FastAPI modular monolith, một React application và PostgreSQL làm source of truth. Phase 1 lấy provider mock làm acceptance gate; model YOLO `.pt` chỉ là đường chạy detector-only tùy chọn.

## Goals / Non-Goals

**Goals:**

- Năm thành viên làm song song theo thư mục owner và contract ổn định.
- Chạy được end-to-end: login → chọn Lane/video → gửi frame → mock ALPR → lưu → xác nhận.
- Có migration, seed, authorization, storage và error handling đủ để thay mock bằng model thật sau này.
- Ưu tiên Local Gate trước khi phát triển module sâu.

**Non-Goals:**

- OCR/PaddleOCR và việc suy luận chuỗi biển số.
- Check-in/check-out, phân loại vé, cache, tính phí hoặc điều khiển barrier.
- Camera stream thật; nguồn video Phase 1 là MP4 local.
- Giao diện final hoặc dashboard nghiệp vụ đầy đủ.

## Decisions

### 1. Chia năm workstream theo ownership

- Người 1 — AI Core/ALPR API/Integration/QA: `backend/app/alpr`, `POST /api/v1/alpr/detections`, ALPR contract/fixtures, Compose và E2E.
- Người 2 — Backend Core: `main.py`, core, database, auth/users và Alembic foundation.
- Người 3 — Backend Domain/Persistence: lanes, detection persistence, confirmation/audit, storage adapter và health dependency wiring.
- Người 4 — Station Frontend: Station layout, video/canvas, request controller, bbox và confirmation UI.
- Người 5 — Frontend Foundation/Admin: app/router/auth/API client, Login, Admin layout và Lane UI.

Shared files có owner: Người 2 sở hữu backend app/router; Người 5 sở hữu frontend app/router/API client; Người 1 sở hữu contract và Compose. Thành viên khác export entrypoint thay vì sửa file shared trực tiếp.

ALPR detection endpoint thuộc Người 1 vì đây là public boundary của AI Core. Endpoint nhận/decode frame, gọi `ALPRRuntime`, map lỗi và trả `ALPRResult`. Để không kéo ORM và nghiệp vụ bãi xe vào AI Core, application service của Người 1 chỉ phụ thuộc các port `ActiveLaneChecker`, `ImageStorage` và `DetectionRecorder`; Người 3 cài đặt và inject các adapter này. Detection history và confirmation API vẫn thuộc Người 3.

### 2. Công nghệ local baseline

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL driver, PyJWT và Argon2id.
- Frontend: React, TypeScript, Vite, React Router và test runner của project.
- Runtime: Docker Compose gồm `postgres`, `backend`, `frontend`; local image storage dùng named volume/mount qua adapter.
- Redis, MediaMTX, Nginx và object storage service chưa cần cho lát cắt này.

### 3. Data model tối thiểu

- `roles`: ID, name duy nhất.
- `users`: ID, username duy nhất, display name, password hash, role, active, timestamps.
- `lanes`: UUID, name duy nhất, direction `IN/OUT`, video source, active, timestamps.
- `media_objects`: UUID, object key, MIME, size, checksum, timestamps.
- `alpr_detections`: UUID, lane, media, raw/normalized/final plate, bbox JSON, confidence, model version, processing time, requires confirmation, status, confirmed by/at, timestamps.
- `audit_logs`: UUID, actor, action, resource, before/after JSON, timestamp, correlation ID.

Không tạo `parking_transactions`, tickets, pricing hoặc payments trong change này.

### 4. API contract

```text
POST  /api/v1/auth/login
GET   /api/v1/auth/me
GET   /api/v1/lanes
GET   /api/v1/lanes/{id}
POST  /api/v1/lanes
PATCH /api/v1/lanes/{id}
POST  /api/v1/alpr/detections
GET   /api/v1/alpr/detections?lane_id=&limit=
POST  /api/v1/alpr/detections/{id}/confirmation
GET   /health/live
GET   /health/ready
```

Detection request dùng multipart `image` và `lane_id`. Confirmation request dùng `{accepted: boolean, confirmed_plate_number?: string}`. Tất cả lỗi dùng `{code,message,details,correlation_id}`.

### 5. Mock provider là runtime thật của local

`ALPR_PROVIDER=mock` là mặc định local. Mock implement cùng `ALPRRuntime` và trả kết quả tất định với `model_version=mock-alpr-0.1.0`. Health báo ready nhưng công bố provider mock; UI luôn hiện nhãn demo. `ALPR_PROVIDER=unavailable` dùng để test `503`. CI không tải weight hoặc dependency AI nặng.

### 5a. Detector-only là đường tích hợp tùy chọn

`ALPR_PROVIDER=real` được phép chạy model `.pt` đã có trong repository nhưng không được khởi tạo OCR khi `ALPR_OCR_ENABLED=false`. Runtime chỉ trả bounding box, confidence và `plate_number=null`; kết quả luôn đặt `requires_confirmation=true`. Mock provider vẫn là gate bắt buộc của Phase 1 để CI không phụ thuộc weight hoặc dependency AI nặng. Khi Phase 2 bật OCR, chỉ thay implementation phía provider và giữ nguyên HTTP/database/UI contract.

### 6. Transaction và storage consistency

API validate/decode ảnh và Lane trước, lưu file qua storage adapter, sau đó lưu media/detection trong database transaction. Nếu DB fail sau khi đã ghi file, adapter thực hiện cleanup best-effort. Database không lưu blob và API không trả filesystem path.

### 7. Authentication/RBAC

JWT access token đủ cho local Phase 1, thời hạn cấu hình; chưa có refresh token. Password dùng Argon2id. Health/login public; detection/confirmation cần `OPERATOR` hoặc `ADMIN`; Lane mutation chỉ `ADMIN`; Lane list cho user đã đăng nhập.

### 8. Station concurrency

Station lấy frame bằng canvas theo interval mặc định 200 ms nhưng chỉ gửi nếu không có request pending. Pause, EOF, route unmount hoặc đổi video sẽ hủy timer. Response gắn với request hiện tại để tránh kết quả cũ ghi đè video/lane mới.

## Risks / Trade-offs

- [Mock có thể bị nhầm là model thật] → Health, response và UI công bố rõ provider/version mock.
- [Hai nhánh cùng sửa bootstrap] → Quy định owner cho shared router và merge entrypoint qua handoff.
- [Lưu file xong nhưng DB lỗi] → Cleanup best-effort và test failure path; production object storage để change sau.
- [Frontend gửi quá nhiều frame] → Một request pending tối đa và bỏ frame khi bận.
- [JWT local đơn giản hơn production] → Thời hạn cấu hình, không refresh; thiết kế session production để change riêng.

## Migration Plan

1. Đạt Local Gate: ba container boot, migration/seed, health và hai route UI hoạt động.
2. Triển khai auth/RBAC và Lane theo chiều dọc DB → API → UI.
3. Người 1 triển khai ALPR boundary/mock và Detection API; Người 3 cung cấp Lane/storage/persistence adapters.
4. Ghép Station video, request controller và confirmation.
5. Chạy integration/regression trên clean environment.
6. Khi cần kiểm thử model, chuyển `ALPR_PROVIDER=real` và `ALPR_OCR_ENABLED=false`; rollback về mock không đổi API/database/UI. OCR/PaddleOCR chỉ được thêm trong Phase 2 sau khi có bộ ảnh biển số và benchmark riêng.

## Phase 1 Exit Gate

Phase 1 chỉ được đóng khi backend pytest, frontend lint/test/build, migration check và Docker Compose clean boot đều pass; luồng login → lane → upload frame → mock/detector-only result → manual confirmation → history/audit chạy được. Không yêu cầu OCR, nhưng UI và API phải công bố rõ khi plate chưa được đọc và cần xác nhận thủ công.
