# VisionPark — Tài liệu review kiến trúc và luồng hệ thống

> **Mục đích:** tài liệu chuẩn bị cho buổi review với giảng viên hướng dẫn. Nội dung được tổng hợp từ code, cấu hình, migration, test và tài liệu thiết kế đang có trong repository.
>
> **Ngày đối chiếu:** 01/10/2026
>
> **Cách đọc:** phần “Đã có” mô tả code đang triển khai; phần “Thiết kế mục tiêu” mô tả hướng mở rộng đã được thống nhất nhưng chưa nên trình bày như chức năng đã hoàn thiện.

---

## 1. Tóm tắt dự án

VisionPark là hệ thống quản lý bãi đỗ xe thông minh, dùng **ALPR (Automatic License Plate Recognition)** để hỗ trợ nhận diện biển số tại các làn vào/ra.

Mục tiêu nghiệp vụ tổng thể:

1. Quản lý người dùng và quyền truy cập.
2. Quản lý làn xe, hướng vào/ra và nguồn video/camera.
3. Nhận ảnh từ Station, phát hiện vùng biển số và đọc biển số.
4. Cho nhân viên vận hành xem kết quả, xác nhận hoặc sửa biển số.
5. Lưu detection, ảnh gốc, metadata AI và lịch sử thao tác.
6. Mở rộng thành quy trình check-in, check-out, tính phí, vé tháng, thanh toán và điều khiển barrier.

### Trạng thái hiện tại

| Nhóm chức năng | Trạng thái thực tế |
|---|---|
| FastAPI application, cấu hình, middleware, error contract | Đã có |
| PostgreSQL/SQLite-compatible SQLAlchemy, Alembic, seed | Đã có nền tảng |
| JWT authentication, Argon2id password hashing, RBAC | Đã có |
| Lane management | Đã có backend và frontend admin |
| ALPR runtime boundary | Đã có |
| Mock ALPR deterministic provider | Đã có, là đường chạy mặc định local/CI |
| Real detector provider bằng Ultralytics và tùy chọn OCR PaddleOCR | Đã có adapter/readiness; cần kiểm chứng model/runtime thực tế |
| Lưu ảnh local và lưu metadata detection | Đã có |
| Detection history và operator confirmation | Đã có ở backend ở mức detection |
| Station UI capture/video/bounding box | Đã có một phần; một số màn hình còn là shell/demo |
| Parking transaction PARKED, check-in end-to-end | Chưa hoàn thiện |
| Check-out, fee calculation, monthly ticket, payment/VietQR | Chưa triển khai |
| Barrier và camera RTSP thật | Chưa triển khai, mới có integration boundary/thiết kế |
| Production deployment, monitoring, retention/backup đầy đủ | Chưa hoàn thiện |

Điểm cần nhấn mạnh khi review: **ALPR detection không đồng nghĩa với nghiệp vụ gửi xe**. Module ALPR chỉ trả kết quả nhận diện; domain parking mới quyết định xe được check-in, trạng thái xe, phí và barrier.

---

## 2. Phạm vi và giả định kiến trúc

### 2.1 Phạm vi MVP hiện tại

- Một bãi xe.
- Nhiều lane vào/ra.
- Một React application dùng chung cho Station và Admin.
- Một FastAPI modular monolith xử lý API, domain logic và ALPR orchestration.
- PostgreSQL là nguồn dữ liệu chuẩn.
- Ảnh không lưu trực tiếp trong database; database chỉ lưu image key và metadata.
- Mock provider dùng cho local/CI/demo ổn định.
- Real provider được bật bằng cấu hình khi có model manifest, weights và dependency phù hợp.

### 2.2 Các giả định chưa phải quyết định production

- Camera thật sẽ đi qua adapter hoặc video gateway; frontend hiện chủ yếu thao tác với video file/demo.
- Barrier sẽ được tích hợp qua adapter, không gọi trực tiếp từ ALPR runtime.
- Payment/VietQR cần cơ chế xác nhận thanh toán riêng; tạo QR không được coi là đã thanh toán.
- Khi chưa có model thật hoặc model không sẵn sàng, hệ thống phải hiển thị trạng thái rõ ràng và cho phép fallback thủ công.

---

## 3. Kiến trúc tổng thể

### 3.1 Kiểu kiến trúc

VisionPark hiện dùng **modular monolith**:

~~~text
┌──────────────────────────────────────────────────────────────┐
│ Browser                                                      │
│ React + TypeScript + Vite                                   │
│ - Auth / route guards                                       │
│ - Station UI                                                │
│ - Admin UI                                                  │
│ - Shared API client                                         │
└───────────────────────────────┬──────────────────────────────┘
                                │ HTTP/JSON + multipart image
                                ▼
┌──────────────────────────────────────────────────────────────┐
│ Nginx / frontend runtime                                    │
│ - Serve static React build                                  │
│ - Proxy /api/* and /health/* to backend                    │
└───────────────────────────────┬──────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI backend                                             │
│ API layer → Application/domain service → Ports/adapters     │
│ Auth | Lanes | ALPR | Audit | Parking (planned)             │
└──────────────┬───────────────────────────┬───────────────────┘
               │                           │
               ▼                           ▼
┌────────────────────────┐       ┌────────────────────────────┐
│ PostgreSQL              │       │ Local media storage         │
│ users, roles, lanes,   │       │ original frames/images      │
│ detections, audit_logs  │       │ grouped by lane             │
└────────────────────────┘       └────────────────────────────┘

Optional ALPR runtime inside backend:
  mock provider | real Ultralytics detector | optional PaddleOCR
~~~

### 3.2 Các nguyên tắc chính

1. **HTTP endpoint chỉ làm nhiệm vụ transport.** Validation nghiệp vụ và orchestration nằm trong service/domain layer.
2. **Repository/adapter che giấu persistence hoặc dependency bên ngoài.** Service không nên phụ thuộc trực tiếp vào implementation cụ thể nếu có thể dùng port.
3. **ALPR là module nội bộ, không phải microservice riêng trong MVP.** Nhờ interface ALPRRuntime, provider có thể đổi mà caller không đổi.
4. **ALPR không tạo parking transaction.** ALPR chỉ nhận ảnh và trả ALPRResult.
5. **Database là source of truth.** Local storage chỉ lưu binary image; metadata và trạng thái nghiệp vụ nằm ở database.
6. **Barrier chỉ được mở sau khi nghiệp vụ tương ứng commit thành công.**
7. **Mock phải deterministic.** CI và demo không phụ thuộc GPU, model weight hay dataset nhạy cảm.

### 3.3 Sơ đồ có sẵn trong repository

- [Component diagram](./VisionPark_Component_Diagram.svg)
- [Deployment diagram](./VisionPark_Deployment_Diagram.svg)
- [Package diagram](./VisionPark_Package_Diagram.svg)
- [Activity overview](./VisionPark_Activity_Overview.svg)
- [Activity check-in](./VisionPark_Activity_CheckIn.png)
- [Activity check-out](./VisionPark_Activity_CheckOut.png)
- [ERD khái niệm](./VisionPark-ERD-khai-niem.png)

---

## 4. Cấu trúc repository và trách nhiệm module

~~~text
VisionPark/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI router và endpoint
│   │   ├── core/                   # config, security, error, logging, health
│   │   ├── database/               # engine/session/base/seed/bootstrap
│   │   ├── modules/
│   │   │   ├── auth/               # login, current user, role dependency
│   │   │   ├── users/              # User, Role, repository, DTO
│   │   │   ├── lanes/              # Lane CRUD và lane rules
│   │   │   ├── alpr/               # Detection model/response/confirmation
│   │   │   └── audit_logs/          # Audit model và log service
│   │   ├── alpr/                   # runtime interface, providers, ALPR service
│   │   └── integrations/
│   │       ├── persistence/        # database adapters
│   │       └── storage/            # local image storage adapter
│   ├── alembic/                    # migration lịch sử database
│   ├── models/                     # manifest/model metadata
│   └── tests/                      # unit/integration tests backend
├── frontend/
│   ├── src/
│   │   ├── api/                    # client, token, typed services
│   │   ├── layouts/                # shell theo Station/Admin
│   │   ├── modules/                # auth, station, lanes, detections, admin...
│   │   ├── components/             # reusable UI và error boundary
│   │   └── app/                    # router
│   └── tests/                      # Vitest/Testing Library
├── docs/                           # architecture, diagrams, plans, review docs
├── openspec/                       # proposal/design/spec/task của các change
├── docker-compose.yml              # local stack và CI services
└── .github/workflows/ci.yml        # Docker CI pipeline
~~~

### Backend layering

~~~text
HTTP request
  ↓
FastAPI endpoint/router
  ↓
Auth dependency + Pydantic schema + input validation
  ↓
Application service / domain service
  ↓
Repository hoặc port
  ↓
SQLAlchemy / local storage / ALPR runtime / external adapter
~~~

### Frontend layering

~~~text
Route
  ↓
Page module
  ↓
Feature hook/state
  ↓
Typed API service
  ↓
Shared apiClient
  ↓
fetch + JWT + timeout + typed ApiError
~~~

---

## 5. Luồng khởi động và triển khai local

### 5.1 Docker Compose flow

~~~text
docker compose up
       │
       ├── db
       │     └── PostgreSQL 17, healthcheck pg_isready
       │
       ├── migrate
       │     └── alembic upgrade head
       │
       ├── backend
       │     ├── chờ db healthy
       │     ├── chờ migrate completed successfully
       │     ├── FastAPI/Uvicorn :8000
       │     └── healthcheck /health/live
       │
       └── frontend
             ├── build React/Vite
             ├── Nginx :80 trong container
             ├── proxy /api/ → backend:8000
             └── proxy /health/ → backend:8000
~~~

Compose hiện public mặc định:

| Service | Container port | Host port mặc định | Vai trò |
|---|---:|---:|---|
| PostgreSQL | 5432 | 5433 | Database |
| Backend | 8000 | 8000 | API |
| Frontend/Nginx | 80 | 5173 | Web UI |

### 5.2 FastAPI lifespan

Khi app.main:create_app() chạy:

1. Đọc Settings từ environment/.env.
2. Cấu hình logging.
3. Khi lifespan bắt đầu, cấu hình SQLAlchemy database engine.
4. Nếu AUTO_SEED=true, tạo role, demo users và demo lanes theo kiểu idempotent.
5. Tạo ALPR runtime thông qua create_runtime(...).
6. Gắn runtime vào app.state.alpr_runtime.
7. Gắn readiness probe vào app.state.alpr_readiness_probe.
8. Đăng ký CORS, correlation ID middleware, exception handlers và routers.
9. Khi shutdown, dispose database engine.

### 5.3 Database migration và seed

Migration hiện đi theo chuỗi chính:

~~~text
identity tables
   ↓
lane tables
   ↓
detection tables
   ↓
detection metadata + audit_logs
~~~

Seed mặc định tạo:

- Roles: ADMIN, OPERATOR, ACCOUNTANT, TECHNICIAN.
- User demo theo biến môi trường khi có password.
- LANE_IN_01 với direction IN.
- LANE_OUT_01 với direction OUT.

Password không lưu dạng plaintext; seed dùng Argon2id để tạo password_hash.

---

## 6. Luồng authentication và authorization

### 6.1 Login end-to-end

~~~text
User nhập username/password
        ↓
React LoginPage
        ↓
authApi.login()
        ↓
POST /api/v1/auth/login
        ↓
AuthService.login()
        ├── UserRepository tìm user
        ├── verify_password bằng Argon2id
        ├── reject nếu không tồn tại, sai password hoặc inactive
        ├── cập nhật last_login_at
        └── create_access_token() bằng JWT HS256
        ↓
Frontend lưu access_token
        ↓
Gọi GET /api/v1/auth/me
        ↓
AuthContext lưu current user
        ↓
RootRedirect:
  ADMIN     → /admin/dashboard
  role khác → /station/scan
~~~

### 6.2 JWT

JWT hiện chứa các claim chính:

- sub: UUID user.
- type: access.
- iat: thời điểm phát hành.
- exp: thời điểm hết hạn.
- jti: UUID token.

Frontend gắn token vào header:

~~~http
Authorization: Bearer <access_token>
~~~

Backend giải mã token, tìm lại user trong database và kiểm tra is_active. Vì vậy token hợp lệ về chữ ký nhưng user đã bị disable vẫn bị từ chối.

### 6.3 Role guard

| Vai trò | Quyền đang thể hiện trong code |
|---|---|
| ADMIN | Toàn bộ admin UI, quản lý lane, xem detection, thao tác quản trị |
| OPERATOR | Station/ALPR operation, xem detection và xác nhận biển số |
| ACCOUNTANT | Có trong domain role/seed; frontend/backend nghiệp vụ riêng chưa hoàn thiện |
| TECHNICIAN | Có trong domain role/seed; nghiệp vụ riêng chưa hoàn thiện |

Authorization có hai lớp:

1. Frontend ProtectedRoute/AdminGuard để điều hướng và ẩn khu vực UI.
2. Backend get_current_user() và require_roles(...) để bảo vệ thực sự API.

Frontend guard chỉ là UX; không được coi là lớp bảo mật cuối cùng.

### 6.4 Khi token hết hạn

apiClient xử lý HTTP 401:

1. Xóa token local.
2. Gọi onUnauthorized do AuthProvider đăng ký.
3. Chuyển về /login?returnUrl=....
4. Các lỗi network/5xx không tự động xóa token để tránh mất phiên do lỗi tạm thời.

---

## 7. Luồng quản lý lane

### 7.1 Admin tạo/cập nhật lane

~~~text
Admin mở /admin/lanes
        ↓
LaneListPage + useLanes
        ↓
lanesApi → apiClient
        ↓
POST/PATCH /api/v1/lanes
        ↓
require_roles(ADMIN)
        ↓
lanes.service
        ├── kiểm tra lane name trùng
        ├── repository thao tác SQLAlchemy
        ├── commit transaction
        └── log_action(CREATE_LANE/UPDATE_LANE)
        ↓
LaneResponse trả về UI
~~~

### 7.2 Soft deactivation

Lane không bị xóa vật lý từ UI. Thao tác ngưng lane chuyển is_active=false, sau đó lane không còn hợp lệ cho ALPR processing.

Điều này bảo toàn lịch sử detection và tránh làm mất foreign key liên quan.

### 7.3 API lane hiện có

| Method | Endpoint | Role | Mục đích |
|---|---|---|---|
| POST | /api/v1/lanes/ | ADMIN | Tạo lane |
| GET | /api/v1/lanes/ | ADMIN | Liệt kê lane |
| GET | /api/v1/lanes/active | ADMIN | Liệt kê lane active |
| GET | /api/v1/lanes/{lane_id} | ADMIN | Xem lane |
| PATCH | /api/v1/lanes/{lane_id} | ADMIN | Cập nhật lane |
| POST | /api/v1/lanes/{lane_id}/deactivate | ADMIN | Soft deactivate |

---

## 8. Luồng ALPR hiện tại

### 8.1 ALPR boundary

Interface ALPRRuntime quy định hai hành vi:

~~~python
is_ready() -> tuple[bool, str]
detect_and_read(image_bytes: bytes) -> ALPRResult
~~~

Provider hiện có:

| Provider | Mục đích | Đặc điểm |
|---|---|---|
| mock | local/CI/demo | Deterministic, không cần model thật |
| real | chạy detector thật | Ultralytics weights, manifest/checksum; OCR tùy chọn |
| ONNX runtime class | baseline/compatibility | Có lớp ONNX nhưng output detector/OCR hiện còn placeholder cần hoàn thiện theo model contract |
| unavailable | fallback khi cấu hình sai | Readiness false và trả lỗi dependency |

### 8.2 Luồng upload detection

~~~text
Station chọn lane + frame ảnh
        ↓
POST /api/v1/alpr/detections
multipart/form-data:
  lane_id
  image (JPEG/PNG)
        ↓
Auth: OPERATOR hoặc ADMIN
        ↓
Kiểm tra content type
        ↓
Đọc bytes; giới hạn tối đa 5 MB
        ↓
OpenCV decode để loại ảnh hỏng
        ↓
resolve_alpr_service()
        ├── runtime = app.state.alpr_runtime
        ├── lane_checker = DatabaseLaneChecker
        ├── image_storage = LocalStorageAdapter
        └── detection_recorder = DatabaseDetectionRecorder
        ↓
ALPRApplicationService.process_detection()
        ├── kiểm tra lane tồn tại và active
        ├── runtime.detect_and_read(image_bytes)
        ├── lưu ảnh gốc vào local storage
        ├── lưu detection metadata vào database
        └── nếu ghi DB lỗi: xóa ảnh vừa lưu
        ↓
Map ALPRResult → ALPRHTTPResponse
        ↓
Frontend hiển thị biển số, bbox, confidence, latency, model version
~~~

### 8.3 Xử lý ảnh và kết quả

ALPRResult gồm:

- plate_number: biển số raw hoặc null.
- bbox: x1, y1, x2, y2 hoặc null.
- confidence: 0–1.
- processing_time_ms.
- requires_confirmation.
- model_version.
- detection_id sau khi persistence thành công.

Plate được normalize bằng cách uppercase và bỏ ký tự không phải A-Z/0-9. Ví dụ:

~~~text
29A-123.45 → 29A12345
~~~

BBox được clamp theo kích thước ảnh trước khi crop hoặc trả về UI, tránh tọa độ vượt biên.

### 8.4 Mock scenarios

Mock provider hỗ trợ các scenario để test/demo:

- success: trả một biển số mẫu với confidence cao.
- low-confidence: trả biển số nhưng bắt buộc confirmation.
- no-plate: không có biển số/bbox, bắt buộc nhập tay.
- processing-error: mô phỏng lỗi inference.
- unavailable: mô phỏng runtime chưa sẵn sàng.

### 8.5 Real provider flow

Khi ALPR_PROVIDER=real:

1. Đọc model manifest.
2. Kiểm tra model_version.
3. Resolve weights_path.
4. Kiểm tra file weights và checksum SHA-256 nếu manifest cung cấp.
5. Lazy-load Ultralytics.
6. Nếu bật OCR, lazy-load PaddleOCR.
7. Detector tìm class plate có confidence cao nhất.
8. Clamp bbox và crop plate với margin.
9. OCR đọc text, normalize text.
10. Kết hợp detector/OCR confidence; so sánh với threshold.
11. Trả kết quả cùng latency và model version.

Heavy dependency được lazy-load để mock mode và CI không cần PyTorch/Ultralytics/PaddleOCR/model weight.

### 8.6 Persistence của detection

Bảng detections hiện lưu:

- id, lane_id.
- image_key, image_content_type, image_size_bytes.
- raw_plate, normalized_plate.
- Bốn tọa độ bbox.
- confidence, processing_time_ms.
- requires_confirmation.
- is_confirmed, confirmed_plate, confirmed_by_id.
- created_at, updated_at.

Ảnh được lưu theo cấu trúc tương tự:

~~~text
<LOCAL_STORAGE_PATH>/
└── <lane_id>/
    └── <lane_id>_<uuid>.jpg|png
~~~

Nếu database recorder lỗi sau khi ảnh đã lưu, application service gọi delete_image() để tránh file mồ côi.

---

## 9. Luồng Station và trạng thái UI

Có hai lớp Station đang tồn tại trong codebase:

1. StationPage và các component ALPR capture chi tiết: lane selector, video player, result, confirmation, recent history.
2. ScanPage: shell vận hành theo state demo, dùng cho tích hợp màn hình/UX rộng hơn.

### 9.1 Station capture flow

~~~text
Mở Station
  ↓
Load active lanes
  ↓
Operator chọn lane
  ↓
Chọn video file hoặc nguồn camera seam
  ↓
VideoPlayer capture frame
  ↓
Throttle chống gửi nhiều request đồng thời
  ↓
POST detection
  ↓
PROCESSING
  ├── success có biển số
  ├── low confidence / requires confirmation
  ├── no plate
  ├── timeout/network error
  └── provider unavailable
  ↓
Hiển thị bbox overlay và metadata
  ↓
Operator:
  ├── xác nhận biển số đúng
  ├── sửa/nhập biển số thủ công
  └── quét lại
  ↓
Gọi confirmation API và refresh history
~~~

### 9.2 Các state được thiết kế ở Scan UI

NO_VIDEO, READY, PLAYING, PROCESSING, DETECTED, LOW_CONFIDENCE, NO_PLATE, WAITING_CONFIRMATION, CONFIRMED, CORRECTED, ERROR, OFFLINE.

Ý nghĩa nghiệp vụ:

- PROCESSING: đang gửi frame tới ALPR.
- DETECTED: có kết quả, có thể cần thao tác tiếp.
- LOW_CONFIDENCE: không tự động coi là đúng.
- NO_PLATE: cho phép nhập tay hoặc quét lại.
- CONFIRMED/CORRECTED: operator đã chốt giá trị cuối.
- OFFLINE/ERROR: không được giả lập thành thành công; hiển thị retry/fallback.

### 9.3 Mock mode frontend

Khi VITE_USE_MOCK_ALPR khác false, frontend/src/modules/station/api.ts trả dữ liệu mock tại frontend, gồm biển số mẫu, bbox, confidence và lịch sử trong memory.

Cần phân biệt:

- **Frontend mock:** request chưa đi backend.
- **Backend mock:** request đi qua API, service, storage và database nhưng runtime AI trả kết quả deterministic.

---

## 10. Luồng xác nhận biển số và audit

### 10.1 Confirmation hiện tại

Backend có endpoint:

~~~http
POST /api/v1/alpr/detections/{detection_id}/confirm
Authorization: Bearer <token>
Content-Type: application/json

{
  "confirmed_plate": "29A12345"
}
~~~

Flow:

1. Require OPERATOR hoặc ADMIN.
2. Tìm Detection theo UUID.
3. Set is_confirmed=true.
4. Set confirmed_plate.
5. Set confirmed_by_id=current_user.id.
6. Ghi AuditLog action CONFIRM_PLATE.
7. Commit và trả detection.

### 10.2 Audit log

audit_logs lưu:

- actor user_id.
- action.
- entity_type và entity_id.
- old_value JSON.
- new_value JSON.
- timestamps.

Lane create/update/deactivate và detection confirmation đã có các điểm gọi log_action.

### 10.3 Nguyên tắc nghiệp vụ

AI chỉ là đề xuất. Giá trị được dùng cho nghiệp vụ sau này phải là **final/confirmed plate**, không lấy mù quáng từ raw_plate.

---

## 11. Thiết kế mục tiêu cho parking check-in

Đây là vertical slice Phase 2 được mô tả trong OpenSpec; code hiện tại chưa hoàn thiện đầy đủ transaction/domain/API này.

### 11.1 Luồng mục tiêu

~~~text
Frame
  ↓
ALPR detection
  ↓
Operator confirm hoặc nhập tay
  ↓
Parking Check-in Service
  ├── xác thực lane IN và active
  ├── normalize final plate
  ├── kiểm tra plate đang PARKED
  ├── kiểm tra Idempotency-Key
  ├── tạo parking transaction PARKED
  ├── liên kết detection
  ├── ghi actor/source/audit
  └── commit transaction
  ↓
Sau commit thành công mới gọi barrier adapter
  ↓
Trả kết quả check-in và refresh history
~~~

### 11.2 Vì sao confirm-before-create

- Confidence cao vẫn có thể sai do góc, ánh sáng hoặc biển bị che.
- Không tạo giao dịch gửi xe từ kết quả AI chưa được operator kiểm chứng.
- Cho phép no-plate/low-confidence chuyển sang manual fallback.
- Tách trách nhiệm: ALPR đọc, parking quyết định trạng thái.

### 11.3 Duplicate và idempotency

Thiết kế mục tiêu:

- Idempotency-Key cho retry cùng request.
- Lưu fingerprint payload.
- Cùng key + cùng payload → trả lại kết quả cũ.
- Cùng key + payload khác → conflict.
- Unique rule/transaction lock cho một plate đang PARKED.

Đây là lớp bảo vệ chống double check-in do double click, retry mạng hoặc request đồng thời.

### 11.4 Không nên gọi check-in là đã hoàn thành

Hiện database chưa có model parking transaction hoàn chỉnh; chưa có đầy đủ idempotency persistence, duplicate race handling, check-in service và barrier adapter thật. Nên mô tả đây là **thiết kế next milestone**, còn detection/confirmation là baseline đang chạy.

---

## 12. Luồng mục tiêu cho check-out, tính phí và payment

Đây là phạm vi sau check-in, chưa hoàn thiện trong code hiện tại.

~~~text
Xe tại lane OUT
  ↓
Capture frame → ALPR → final plate
  ↓
Tìm active parking transaction
  ↓
Đối chiếu biển vào và biển ra
  ├── match
  ├── mismatch → operator review
  └── không tìm thấy → xử lý lost ticket/exception
  ↓
Xác định loại vé:
  ├── visitor
  └── monthly ticket còn hạn
  ↓
Tính phí theo pricing rule
  ↓
Tạo payment intent/QR nếu cần
  ↓
Xác nhận payment thật từ provider/callback hoặc operator policy
  ↓
Commit checkout/payment state
  ↓
Gọi barrier adapter mở barrier
  ↓
Ghi audit và hoàn tất transaction
~~~

Các trạng thái cần tách rõ:

~~~text
PARKED → FEE_CALCULATED → PAYMENT_PENDING → PAID → EXITED
                    └──────── exception/review ────────┘
~~~

Không nên coi việc sinh VietQR là PAID; phải có trạng thái payment và nguồn xác nhận riêng.

---

## 13. API hiện có và các contract cần review

### 13.1 Health

| Method | Endpoint | Ý nghĩa |
|---|---|---|
| GET | /health/live | Process FastAPI còn sống |
| GET | /health/ready | Kiểm tra database và ALPR runtime |
| GET | /api/v1/alpr/health/live | ALPR route liveness |
| GET | /api/v1/alpr/health/ready | Readiness database + runtime |

Readiness có thể trả 503 nếu process vẫn chạy nhưng database hoặc ALPR provider chưa sẵn sàng. Đây là phân biệt đúng giữa liveness và readiness.

### 13.2 Auth

| Method | Endpoint | Role |
|---|---|---|
| POST | /api/v1/auth/login | Public |
| GET | /api/v1/auth/me | Authenticated |

### 13.3 ALPR/detection backend

| Method | Endpoint | Role | Mục đích |
|---|---|---|---|
| POST | /api/v1/alpr/detections | OPERATOR/ADMIN | Upload ảnh và tạo detection |
| GET | /api/v1/alpr/detections | OPERATOR/ADMIN | Detection history, filter lane/pagination cơ bản |
| POST | /api/v1/alpr/detections/{id}/confirm | OPERATOR/ADMIN | Confirm/correct detection |
| GET | /api/v1/alpr/media/{image_key} | Chưa nên coi là public | Serve ảnh detection |

### 13.4 Contract mismatch cần xử lý trước demo end-to-end

Codebase hiện có hai hướng API client/contract song song:

1. Backend thực tế đăng ký ALPR dưới /api/v1/alpr/....
2. Một số frontend service gọi /api/v1/detections, /api/v1/detections/{id}/confirm.
3. frontend/src/modules/station/api.ts dùng /alpr/detections/{id}/confirmation và payload accepted/confirmed_plate_number, trong khi backend dùng /alpr/detections/{id}/confirm và payload confirmed_plate.
4. Backend lane trả field is_active; một số frontend type/UI dùng active.
5. Backend get active lanes hiện được bảo vệ bởi role ADMIN, trong khi Station flow có nhu cầu cho OPERATOR đọc lane active.

Đây là các điểm hợp đồng cần thống nhất, không phải lỗi kiến trúc nền tảng. Khi review, nên trình bày rõ:

~~~text
API contract chuẩn cần chọn một phiên bản duy nhất
  ↓
OpenAPI/schema fixture
  ↓
backend endpoint
  ↓
shared frontend apiClient/service
  ↓
Station/Admin UI tests
~~~

---

## 14. Database và dữ liệu

### 14.1 Quan hệ chính hiện có

~~~text
roles ────────< users
                  │
                  ├────< audit_logs
                  └────< detections >──── lanes
~~~

#### roles

- id, name, timestamps.
- Unique role name.

#### users

- username unique.
- display name.
- Argon2id password hash.
- role foreign key.
- active flag.
- last login timestamp.

#### lanes

- name unique.
- direction IN/OUT.
- video source.
- active flag.
- timestamps.

#### detections

- Detection output, bbox, confidence, latency.
- Image storage key/metadata.
- Confirmation information.
- Foreign key đến lane và confirmed user.

#### audit_logs

- actor/action/entity/before/after.
- Foreign key user với SET NULL khi user bị xóa theo policy.

### 14.2 Transaction boundary hiện tại

- Lane service commit các thay đổi lane và audit.
- Detection recorder commit detection sau khi image được lưu.
- Nếu detection commit thất bại, image được xóa bù.
- Confirmation cập nhật detection và audit trong cùng request transaction.

### 14.3 Transaction boundary cần bổ sung cho parking

Parking check-in/check-out cần một transaction atomic bao phủ:

~~~text
validate → duplicate/idempotency check → create/update transaction
         → link detection → audit → commit
~~~

Barrier call nên nằm sau commit hoặc qua outbox/command pattern khi cần reliability cao hơn; không để thiết bị mở nhưng database rollback.

---

## 15. Error handling, observability và resilience

### 15.1 Error contract

Backend có AppError và global exception handlers. Error response hướng tới các field:

- HTTP status.
- code ổn định cho frontend.
- message hiển thị.
- details nếu cần.
- correlation_id để truy vết.

Các lỗi ALPR được phân loại:

| Error | HTTP dự kiến | Ý nghĩa |
|---|---:|---|
| Invalid format / corrupted image | 422 | Input không hợp lệ |
| Lane không tồn tại/inactive | 404/validation error | Không thể xử lý lane |
| ALPR not ready | 503 | Model/dependency chưa sẵn sàng |
| ALPR processing error | 503 | Inference thất bại |
| Unauthenticated | 401 | Thiếu/sai/hết token |
| Forbidden | 403 | Không đủ role |
| Conflict | 409 | Duplicate hoặc state conflict |

### 15.2 Correlation ID

CorrelationIdMiddleware tạo hoặc giữ correlation ID cho request, trả qua header X-Correlation-ID và đưa vào error response/log context. Khi debug một lần scan, có thể dùng ID này nối frontend error với backend log.

### 15.3 Frontend resilience

apiClient có:

- timeout cấu hình bằng VITE_API_TIMEOUT_MS.
- abort request khi timeout.
- phân loại TIMEOUT và NETWORK_ERROR.
- parse lỗi typed thành ApiError.
- tự xử lý 401.
- giữ FormData không tự set Content-Type để browser tự thêm boundary.

Station có retry/error panel; lịch sử là secondary data nên lỗi history không làm mất toàn bộ màn hình scan.

---

## 16. Security design

### Đã có

- JWT HS256.
- Argon2id password hashing.
- Secret đọc từ environment.
- Production từ chối development JWT secret.
- CORS cấu hình được.
- RBAC backend.
- Upload giới hạn JPEG/PNG và 5 MB.
- OpenCV decode để chặn file hỏng.
- Không commit .env, secret, dataset nhạy cảm và model weight production.
- Audit các thao tác quan trọng.

### Cần bổ sung/kiểm chứng trước production

- Rate limit login và upload.
- HTTPS/TLS và secure deployment secret.
- Kiểm soát path traversal khi serve media bằng image key.
- Authorization riêng cho endpoint xem ảnh.
- Retention/lifecycle cho ảnh biển số.
- Backup/restore và phân quyền database.
- CORS allowlist production.
- Token revocation/session policy nếu yêu cầu đăng xuất cưỡng chế.
- Audit truy cập ảnh và thao tác payment/barrier.

---

## 17. Testing và CI/CD

### 17.1 Backend tests

Nhóm test hiện có:

- config/security.
- create users và seed.
- migration.
- health/readiness.
- error handlers.
- auth integration.
- lane API.
- ALPR schema, utility, service, runtime adapter, provider và API.

Lệnh chính:

~~~powershell
cd backend
pytest
ruff check .
ruff format --check .
~~~

### 17.2 Frontend tests

Các nhóm test chính:

- api client, Authorization header, FormData, timeout, 401.
- AuthProvider và login.
- route guard cho guest/operator/admin.
- lane list/filter/duplicate/inactive/không DELETE.
- station video controls, throttle, bbox overlay, confirmation.

Lệnh chính:

~~~powershell
cd frontend
npm run lint -- src tests
npm test -- --run
npm run build
~~~

### 17.3 Docker CI flow

Workflow .github/workflows/ci.yml:

~~~text
Checkout
  ↓
docker compose config
  ↓
Build backend-ci/frontend-ci/migrate/backend/frontend
  ↓
Run backend pytest + Ruff trong container
  ↓
Run frontend lint + Vitest + build trong container
  ↓
Start backend/frontend runtime stack
  ↓
Verify backend /health/ready
Verify frontend /health/live
  ↓
Cleanup compose stack
~~~

CI mặc định chạy mock mode, không cần GPU/model weight thật.

### 17.4 Acceptance checklist cho vertical slice

Trước khi tuyên bố check-in hoàn thành nên có test/evidence cho:

- success detection.
- no plate.
- low confidence.
- manual correction.
- inactive lane.
- unauthorized/forbidden.
- duplicate active plate.
- retry cùng idempotency key.
- conflict khi payload đổi.
- race/concurrent request.
- audit đầy đủ actor, AI plate, final plate, lane, timestamp.
- clean database setup.

---

## 18. Các điểm đang hoàn thiện và rủi ro kỹ thuật

### 18.1 Rủi ro contract frontend/backend

Đây là rủi ro gần nhất với demo: nhiều client/API shape song song có thể khiến UI hiển thị được nhưng không gọi đúng backend.

**Đề xuất:** chốt một contract cho detection/confirmation/check-in, cập nhật OpenAPI/schema fixture, sửa một shared service, sau đó thêm integration test từ Station tới API thật.

### 18.2 Real ALPR chưa đồng nghĩa production accuracy

Provider thật đã có cơ chế manifest/loading/readiness, nhưng accuracy cần benchmark theo dataset đại diện: ánh sáng, góc camera, xe máy/ô tô, biển mờ, biển bị che và nhiều biển trong frame.

Không nên trình bày confidence detector như accuracy hệ thống. Cần báo cáo riêng:

- detection precision/recall.
- OCR exact match/character accuracy.
- end-to-end plate accuracy.
- p50/p95 latency.
- tỷ lệ phải manual confirmation.

### 18.3 ONNX class còn placeholder

OnnxALPRRuntime có skeleton cho detector/OCR nhưng phần decode output trong code hiện còn mock output minh họa. Nếu review hỏi “model ONNX đã đọc thật chưa?”, câu trả lời chính xác là: **boundary và pipeline đã có, output parser theo model cụ thể cần hoàn thiện/kiểm chứng**.

### 18.4 Parking domain chưa tách thành module hoàn chỉnh

ALPR detection và confirmation đang chạy, nhưng parking transaction, check-in, check-out và payment chưa có đầy đủ model/service/router. Đây là cơ hội để chứng minh kiến trúc đang giữ đúng boundary, không phải thiếu sót bị che giấu.

### 18.5 Media authorization

Endpoint serve image cần review kỹ path safety và quyền truy cập. Ảnh biển số là dữ liệu nhạy cảm; không nên chỉ dựa trên việc biết image_key.

---

## 19. Kế hoạch phát triển đề xuất

### Phase 1 — Baseline đang có

- FastAPI foundation.
- Database/migration/seed.
- JWT/RBAC.
- Lane management.
- ALPR boundary/mock provider.
- Detection persistence và confirmation.
- Station/Admin shell.
- Docker/CI.

### Phase 2 — ALPR + check-in vertical slice

1. Chốt contract detection/confirmation/check-in.
2. Hoàn thiện real provider và benchmark.
3. Thêm parking transaction model/migration.
4. Implement confirm-before-create check-in.
5. Thêm duplicate protection và idempotency.
6. Thêm history/audit cho check-in.
7. Ghép Station flow với API chuẩn.
8. Thêm E2E mock flow.

### Phase 3 — Check-out và thương mại

1. Parking active transaction lookup.
2. Check-out và đối chiếu biển vào/ra.
3. Pricing rule và fee calculation.
4. Monthly ticket.
5. Payment/VietQR callback/reconciliation.
6. Barrier adapter.
7. Accountant/reporting/dashboard.

### Phase 4 — Production hardening

- Camera RTSP/video gateway.
- Device integration testing.
- Object storage/lifecycle.
- Monitoring/alerting.
- Backup/restore.
- Security hardening.
- Load/performance test.
- Model evaluation and retraining loop.

---

## 20. Kịch bản demo đề xuất cho giảng viên

### Demo A — Authentication/RBAC

1. Đăng nhập bằng ADMIN.
2. Hiển thị admin dashboard/lane management.
3. Logout/login bằng OPERATOR.
4. Truy cập Station thành công.
5. Truy cập /admin/lanes bị chặn ở frontend/backend.

### Demo B — Lane management

1. Admin tạo lane IN.
2. Tạo lane trùng tên để nhận 409.
3. Sửa video source.
4. Deactivate lane.
5. Kiểm tra audit log.

### Demo C — Detection với backend mock

1. Bật ALPR_PROVIDER=mock.
2. Kiểm tra /health/ready.
3. Operator chọn lane và upload frame.
4. Backend validate file/lane.
5. Mock runtime trả plate/bbox/confidence.
6. Ảnh và detection được lưu.
7. UI hiển thị kết quả.

### Demo D — Manual confirmation

1. Chạy scenario low-confidence hoặc no-plate.
2. Hiển thị cảnh báo.
3. Nhập/sửa biển số.
4. Confirm.
5. Kiểm tra is_confirmed, confirmed_plate, confirmed_by_id.
6. Kiểm tra CONFIRM_PLATE trong audit log.

### Demo E — Readiness/failure handling

1. Chuyển mock scenario unavailable.
2. /health/live vẫn alive.
3. /health/ready trả 503 not_ready.
4. Station hiển thị lỗi provider/retry, không giả lập thành transaction thành công.

### Demo F — Nói rõ phần chưa hoàn thiện

~~~text
Detection + confirmation = baseline đã có.
Parking check-in transaction = vertical slice tiếp theo.
Check-out/fee/payment/barrier = phase mở rộng sau check-in.
~~~

---

## 21. Câu hỏi giảng viên có thể hỏi và câu trả lời ngắn

### Vì sao chọn modular monolith thay vì microservices?

Vì MVP có một team và một domain liên kết chặt. Modular monolith giữ boundary rõ giữa auth, lane, ALPR, parking nhưng giảm overhead deploy/network/debug. Khi một module thật sự cần scale hoặc deploy độc lập mới tách service.

### Vì sao ALPR không tự mở barrier?

Vì ALPR chỉ là computer vision capability. Quyền mở barrier phụ thuộc trạng thái transaction, payment, policy và audit; để trong parking/device integration giúp dễ test và tránh side effect ngoài ý muốn.

### Vì sao lưu ảnh ngoài database?

Binary image làm database phình và backup nặng. Database lưu metadata/storage key; adapter có thể đổi local storage sang object storage mà không đổi domain service.

### Vì sao phải confirmation khi confidence cao?

Confidence là tín hiệu của model, không phải bảo đảm nghiệp vụ. Một lỗi biển số có thể tạo duplicate hoặc thu phí sai; confirmation là human-in-the-loop cho MVP.

### Readiness khác liveness thế nào?

Liveness trả lời process còn sống. Readiness trả lời hệ thống có đủ dependency để phục vụ request hay chưa. Backend có thể alive nhưng not ready khi database/model chưa sẵn sàng.

### Làm sao chống tạo giao dịch trùng?

Dùng nhiều lớp: disable double-submit ở UI, idempotency key ở API/application boundary, unique constraint/transaction lock ở database và audit để truy vết.

### Nếu model thật lỗi thì sao?

Readiness báo not ready, request trả dependency error, hệ thống có thể rollback cấu hình về mock cho demo/CI. Không commit model weight/dataset nhạy cảm vào repository.

### Hiện dự án đã có check-in chưa?

Hiện đã có detection và operator confirmation ở mức ALPR. Parking check-in transaction PARKED cùng duplicate/idempotency/audit đầy đủ là hạng mục Phase 2 đang triển khai, chưa nên gọi là hoàn thiện.

---

## 22. Danh sách việc cần chốt trước buổi review

- [ ] Chốt URL và payload chính thức cho detection history/confirmation.
- [ ] Đồng nhất active và is_active giữa backend/frontend.
- [ ] Quyết định Station operator có được gọi active-lane API hay không; hiện role backend cần review.
- [ ] Xác nhận demo dùng frontend mock hay backend mock.
- [ ] Chuẩn bị một ảnh/video demo hợp lệ và một case no-plate/low-confidence.
- [ ] Chuẩn bị screenshot /health/ready, detection record và audit log.
- [ ] Trình bày rõ real ALPR adapter khác với ONNX placeholder.
- [ ] Nêu rõ check-in/check-out/payment/barrier là roadmap, không claim đã hoàn thiện.
- [ ] Chốt acceptance criteria cho parking check-in.
- [ ] Sau review, cập nhật API contract trước khi tiếp tục mở rộng UI.

---

## 23. File code/tài liệu tham chiếu chính

### Backend

- backend/app/main.py
- backend/app/api/v1/router.py
- backend/app/api/v1/endpoints/alpr.py
- backend/app/api/v1/endpoints/lanes.py
- backend/app/alpr/interface.py
- backend/app/alpr/runtime_adapter.py
- backend/app/alpr/pt_provider.py
- backend/app/alpr/onnx_provider.py
- backend/app/alpr/service.py
- backend/app/modules/alpr/models.py
- backend/app/modules/lanes/models.py
- backend/app/modules/auth/dependencies.py
- backend/app/integrations/persistence/detection_recorder_impl.py
- backend/app/integrations/storage/local_storage.py

### Frontend

- frontend/src/App.tsx
- frontend/src/app/router.tsx
- frontend/src/api/client.ts
- frontend/src/modules/auth/AuthContext.tsx
- frontend/src/modules/station/StationPage.tsx
- frontend/src/modules/station/ScanPage.tsx
- frontend/src/modules/station/api.ts
- frontend/src/modules/lanes/LaneListPage.tsx

### Deployment/quality

- docker-compose.yml
- backend/Dockerfile
- frontend/Dockerfile
- frontend/nginx.conf
- .github/workflows/ci.yml
- openspec/changes/phase-2-alpr-checkin/design.md
- openspec/changes/phase-2-alpr-checkin/tasks.md

---

## Kết luận

VisionPark hiện có nền tảng tốt cho một hệ thống bãi xe thông minh: kiến trúc modular monolith, authentication/RBAC, quản lý lane, ALPR runtime boundary, mock/real provider, lưu detection, confirmation, audit, frontend shell và Docker CI.

Giá trị kiến trúc quan trọng nhất là đã tách **khả năng nhận diện** khỏi **quyết định nghiệp vụ gửi xe**. Bước review tiếp theo nên tập trung vào việc chốt contract và hoàn thiện vertical slice:

~~~text
Station frame
  → ALPR
  → operator confirmation
  → parking check-in PARKED
  → duplicate/idempotency protection
  → history/audit
~~~

Sau khi slice này ổn định mới mở rộng sang check-out, pricing, payment và barrier.

