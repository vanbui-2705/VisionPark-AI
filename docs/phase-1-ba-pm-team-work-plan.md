# KẾ HOẠCH PHÂN CÔNG PHÁT TRIỂN VISIONPARK — PHASE 1

## 1. Thông tin tài liệu

| Thuộc tính | Nội dung |
| --- | --- |
| Tên dự án | VisionPark — Hệ thống quản lý bãi đỗ xe thông minh |
| Loại tài liệu | Kế hoạch thực hiện và phân công công việc BA/PM |
| Giai đoạn | Phase 1 — Local baseline với Mock ALPR |
| Phiên bản | 1.0.0 |
| Ngày lập | 05/09/2026 |
| Quy mô đội | 5 thành viên |
| Người phê duyệt | PM Lead / Product Owner |
| Trạng thái | Chờ team xác nhận và triển khai |

## 2. Mục tiêu Phase 1

Xây dựng một lát cắt hệ thống chạy ổn định trên local, cho phép kiểm thử luồng:

```text
Đăng nhập
    ↓
Chọn làn IN/OUT và video MP4
    ↓
Station lấy frame và gửi Backend
    ↓
Mock ALPR trả bbox, biển số và confidence
    ↓
Backend lưu ảnh và kết quả nhận diện
    ↓
Nhân viên xác nhận đúng hoặc sửa biển số
    ↓
Backend lưu kết quả cuối cùng và audit log
```

Kết quả cuối Phase 1 phải bảo đảm:

- Backend FastAPI chạy theo kiến trúc modular monolith.
- Frontend React dùng chung application cho Station và Admin.
- PostgreSQL có migration và dữ liệu seed.
- Có đăng nhập JWT, authentication và RBAC thật.
- Admin quản lý được làn `IN/OUT`.
- Station phát video MP4 và gửi frame có kiểm soát.
- API nhận ảnh và trả kết quả ALPR theo contract thống nhất.
- Kết quả nhận diện và xác nhận thủ công được lưu trong database.
- Frontend, backend và PostgreSQL chạy ổn định bằng Docker Compose.
- Chưa cần model YOLO/PaddleOCR thật; local dùng mock provider và phải hiển thị rõ trạng thái này.

## 3. Phạm vi

### 3.1. Trong phạm vi

- FastAPI application, cấu hình, logging, error handling và health check.
- PostgreSQL, SQLAlchemy, Alembic migration và seed.
- User, Role và xác thực JWT.
- Phân quyền tối thiểu `ADMIN` và `OPERATOR`.
- Lane CRUD với direction `IN/OUT` và active/inactive.
- ALPR runtime interface và mock provider.
- API nhận frame JPEG/PNG.
- Local image storage adapter.
- Lưu media metadata và ALPR detection.
- Xác nhận biển số đúng hoặc nhập lại biển số.
- Audit log cho thao tác xác nhận/sửa biển số.
- Login UI, Admin Lane UI và Station UI.
- Phát MP4, capture frame, throttle request và bbox overlay.
- Docker Compose, unit test, integration test và clean-setup documentation.

### 3.2. Ngoài phạm vi

- Train hoặc tích hợp YOLO.
- Tích hợp hoặc fine-tune PaddleOCR.
- Camera stream và barrier thật.
- Check-in/check-out nghiệp vụ.
- Phân loại vé ngày hoặc vé tháng.
- Cache Redis.
- Tính phí, VietQR và thanh toán.
- Dashboard và báo cáo nghiệp vụ hoàn chỉnh.
- Thiết kế giao diện production cuối cùng.

## 4. Nguyên tắc kiến trúc và ownership

### 4.1. Ranh giới module

- Toàn bộ backend nằm trong `backend/app`.
- Module nghiệp vụ nằm trong `backend/app/modules`.
- Toàn bộ AI nằm trong `backend/app/alpr`.
- Adapter lưu ảnh nằm trong `backend/app/integrations/storage`.
- Toàn bộ frontend nằm trong `frontend/src`.
- Station và Admin dùng chung router, authentication context và API client.
- PostgreSQL là nguồn dữ liệu chuẩn; database không lưu ảnh dạng blob.
- ALPR chỉ trả kết quả nhận diện, không quyết định loại vé, làn, phí hoặc mở cổng.

### 4.2. Quy tắc owner

| Thành phần dùng chung | Owner |
| --- | --- |
| AI Core, ALPR detection API contract và mock/real provider | Người 1 |
| Backend `main.py`, core và API router registry | Người 2 |
| Lane, detection persistence, confirmation/audit và storage adapter | Người 3 |
| Station module | Người 4 |
| Frontend router, auth context và API client | Người 5 |
| Docker Compose và kiểm thử liên thông | Người 1 |

Thành viên không tự sửa file thuộc owner khác. Nếu cần thay đổi contract hoặc file dùng chung, phải tạo PR và yêu cầu owner review.

## 5. Local Gate — ưu tiên bắt buộc

Local Gate phải hoàn thành trước khi phát triển sâu các module.

### 5.1. Điều kiện đạt

- Chạy được `docker compose up --build` từ repository mới clone.
- PostgreSQL container đạt trạng thái healthy.
- Backend mở tại `http://localhost:8000`.
- Swagger mở tại `http://localhost:8000/docs`.
- Frontend mở tại `http://localhost:5173`.
- `/health/live` trả `200`.
- `/health/ready` phản ánh riêng trạng thái database và ALPR provider.
- Frontend mở được `/login` và `/station` không có console error.
- Dừng rồi khởi động lại Compose không làm lỗi migration hoặc seed.
- Local Gate được chạy thành công trên ít nhất hai máy thành viên.

### 5.2. Đóng góp của từng người

| Thành viên | Đầu ra Local Gate |
| --- | --- |
| Người 1 | `.env.example`, Compose, port/volume convention và smoke checklist |
| Người 2 | FastAPI entrypoint, health API và PostgreSQL connection |
| Người 3 | Lane router tối thiểu và cách export domain router |
| Người 4 | Station route và video placeholder |
| Người 5 | React/Vite, Login route, app router và frontend Dockerfile |

## 6. Phân công chi tiết theo thành viên

### 6.1. Người 1 — AI Core, ALPR API, Integration và QA Lead

### Phạm vi sở hữu

```text
backend/app/alpr/
backend/app/api/endpoints/alpr.py
backend/tests/unit/alpr/
backend/tests/integration/api/test_alpr.py
backend/models/
docs/api/
docs/testing/
tests/e2e/
compose.yaml
.env.example
```

### Danh sách công việc

| ID | Công việc | Đầu ra | Phụ thuộc | Tiêu chí hoàn thành |
| --- | --- | --- | --- | --- |
| `P1-AI-01` | Chốt `ALPRResult` | Contract nội bộ AI | Không | Có đầy đủ plate, bbox, confidence, latency, version và confirmation flag |
| `P1-AI-02` | Chốt bbox convention | `[x1,y1,x2,y2]` | Không | Thống nhất pixel coordinate và biên phải/dưới exclusive |
| `P1-AI-03` | Tạo runtime interface | `detect_and_read(frame)` | `P1-AI-01` | Backend gọi được mà không import YOLO/PaddleOCR |
| `P1-AI-04` | Tạo typed errors | Lỗi AI có kiểu | `P1-AI-03` | Có not-ready, validation và processing error |
| `P1-AI-05` | Viết plate normalizer | Hàm chuẩn hóa và test | Không | Viết hoa; bỏ khoảng trắng, dấu chấm và dấu gạch |
| `P1-AI-06` | Viết bbox clamp | Hàm clamp và test | `P1-AI-02` | Không cho crop vượt ảnh; bbox không hợp lệ trả null |
| `P1-AI-07` | Viết confidence policy | Policy có cấu hình | `P1-AI-01` | Confidence ngoài `0..1` bị từ chối; `< 0.85` yêu cầu xác nhận |
| `P1-AI-08` | Tạo ONNX ALPR provider | Runtime ONNX thực tế | `P1-AI-03/05/06/07` | Tải `.onnx` (YOLO/OCR) từ Colab; xử lý qua OpenCV |
| `P1-AI-09` | Tạo fixtures (fallback) | JSON contract examples | `P1-AI-08` | Dùng để Frontend dev độc lập khi model chưa train xong |
| `P1-AI-10` | Tạo model manifest | Thông tin version ONNX | `P1-AI-08` | Ghi rõ tên file `.onnx` và version đang sử dụng |
| `P1-AI-11` | Tạo schema HTTP ALPR | Request/response models | `P1-AI-01/09` | OpenAPI thể hiện đúng multipart, result và error contract |
| `P1-AI-12` | Nhận và kiểm tra frame | Multipart parser + decoder | `P1-AI-11` | Chỉ nhận JPEG/PNG hợp lệ, giới hạn size; ảnh hỏng trả `422` |
| `P1-AI-13` | Tạo ALPR application service | Luồng điều phối detection | `P1-AI-03/12` + adapter Người 3 | Kiểm tra lane, gọi ONNX runtime, lưu ảnh/kết quả qua interface |
| `P1-AI-14` | Tạo Detection API | `POST /api/v1/alpr/detections` | `P1-AI-13` | Trả đúng contract; lỗi validation/ONNX error được map đúng |
| `P1-AI-15` | Viết test ALPR API | Contract/integration tests | `P1-AI-14` | Bao phủ success, low confidence, no plate, ảnh lỗi, lane lỗi |
| `P1-AI-16` | Thả file `.onnx` và Test E2E | Run Inference thật | `P1-AI-08/14` | Bỏ file model vào folder, gửi ảnh và nhận diện thành công |
| `P1-OPS-01` | Tạo Compose baseline | Ba service chạy local | Build Người 2/5 | Backend, frontend, PostgreSQL cùng khởi động |
| `P1-QA-01` | Tạo test plan | QA checklist | Contract đã chốt | Bao phủ auth, Lane, image, ALPR và confirmation |
| `P1-QA-02` | Chạy integration/regression | Báo cáo pass/fail | Bàn giao Người 2–5 | Không còn lỗi Critical/High |

### Nội dung bàn giao

- Cho Người 2: `is_ready`, provider name và model version phục vụ health check.
- Cho Người 3: contract các port `ActiveLaneChecker`, `ImageStorage`, `DetectionRecorder` mà ALPR service cần.
- Cho Người 4: OpenAPI của Detection API và năm response fixture để dựng trạng thái Station.
- Cho cả team: Compose convention, `.env.example` và QA checklist.

### Không thuộc trách nhiệm Người 1 trong vòng này

- Không train YOLO.
- Không tích hợp PaddleOCR.
- Không viết repository/ORM cụ thể cho Lane, media, detection hoặc audit.
- Không viết confirmation/history API hoặc parking business logic.
- Không dựng Station hoặc Admin UI.

### Luồng kỹ thuật do Người 1 sở hữu

```text
Station Frontend
    |
    | POST /api/v1/alpr/detections (image, lane_id)
    v
ALPR Detection Endpoint — Người 1
    |
    +--> ActiveLaneChecker port ------> adapter Người 3
    +--> ALPRRuntime -----------------> MockALPRRuntime (hiện tại)
    |                                  RealALPRRuntime: YOLO + OCR (sau train)
    +--> ImageStorage port -----------> adapter Người 3
    +--> DetectionRecorder port ------> adapter Người 3
    |
    v
ALPRResult ổn định --> Station render bbox, biển số, confidence
```

Nguyên tắc thay model: `MockALPRRuntime` và `RealALPRRuntime` cùng implement `detect_and_read(frame)`. Khi model sẵn sàng, Người 1 chỉ thêm real provider và đổi `ALPR_PROVIDER=real`; route, schema HTTP, database adapter và code Frontend không được thay đổi chỉ vì đổi model.

### 6.2. Người 2 — Backend Core, Database và Authentication

### Phạm vi sở hữu

```text
backend/app/main.py
backend/app/api/router.py
backend/app/core/
backend/app/database/
backend/app/modules/auth/
backend/app/modules/users/
backend/alembic/
backend/tests/unit/core/
backend/tests/unit/auth/
```

### Danh sách công việc

| ID | Công việc | Đầu ra | Phụ thuộc | Tiêu chí hoàn thành |
| --- | --- | --- | --- | --- |
| `P1-BE1-01` | Khởi tạo FastAPI project | Backend entrypoint | Không | Uvicorn chạy bằng một lệnh |
| `P1-BE1-02` | Tạo settings | Environment loader | `P1-BE1-01` | Validate biến bắt buộc, không hard-code secret |
| `P1-BE1-03` | Cấu hình CORS/API prefix | HTTP foundation | `P1-BE1-01` | Frontend local gọi được Backend |
| `P1-BE1-04` | Tạo DB engine/session | Database dependency | `P1-BE1-02` | Kết nối PostgreSQL theo request scope |
| `P1-BE1-05` | Cấu hình Alembic | Migration foundation | `P1-BE1-04` | Upgrade/downgrade chạy được |
| `P1-BE1-06` | Tạo Role/User models | ORM và migration | `P1-BE1-05` | Username/role unique và có active status |
| `P1-BE1-07` | Tạo seed | Role/user demo | `P1-BE1-06` | Seed chạy lặp không tạo trùng |
| `P1-BE1-08` | Hash password | Argon2id helper | `P1-BE1-06` | Không lưu/log mật khẩu thô |
| `P1-BE1-09` | Tạo JWT service | Token helper | `P1-BE1-08` | Có expiry và validate token |
| `P1-BE1-10` | Tạo Login API | `POST /auth/login` | `P1-BE1-09` | Đúng trả token; sai/inactive trả `401` |
| `P1-BE1-11` | Tạo Current User API | `GET /auth/me` | `P1-BE1-10` | Không trả password hash |
| `P1-BE1-12` | Tạo RBAC dependency | Role checker | `P1-BE1-11` | Backend từ chối role không phù hợp |
| `P1-BE1-13` | Tạo error handler | Error contract chung | Contract Người 1 | Có code, message, details, correlation ID |
| `P1-BE1-14` | Tạo middleware/logging | Correlation middleware | `P1-BE1-13` | Mọi request có correlation ID |
| `P1-BE1-15` | Tạo health endpoints | Live/ready | DB + AI readiness | Health phản ánh DB và provider riêng biệt |
| `P1-BE1-16` | Viết test Backend Core | Unit/integration tests | Các task trên | Migration, seed, auth, RBAC và health đạt |

### Nội dung bàn giao

- DB session và base model cho Người 3.
- Authentication và role dependency cho Người 3.
- Login contract cho Người 5.
- Router registration convention cho Người 3.

### 6.3. Người 3 — Backend Domain, Persistence và Confirmation

### Phạm vi sở hữu

```text
backend/app/modules/lanes/
backend/app/modules/alpr_detections/
backend/app/modules/audit_logs/
backend/app/integrations/storage/
backend/app/api/endpoints/lanes.py
backend/tests/unit/modules/
backend/tests/integration/api/
```

### Danh sách công việc

| ID | Công việc | Đầu ra | Phụ thuộc | Tiêu chí hoàn thành |
| --- | --- | --- | --- | --- |
| `P1-BE2-01` | Tạo Lane model/schema | ORM và DTO | DB foundation Người 2 | Có name, direction, video source và active |
| `P1-BE2-02` | Tạo Lane migration/seed | Schema + hai Lane demo | `P1-BE2-01` | Có `LANE_IN_01`, `LANE_OUT_01` |
| `P1-BE2-03` | Tạo Lane repository | Data access | `P1-BE2-01` | Không đặt SQL trong endpoint |
| `P1-BE2-04` | Tạo Lane service | Business rules | `P1-BE2-03` | Chặn trùng tên, không hard delete |
| `P1-BE2-05` | Tạo Lane API | CRUD endpoints | Auth/RBAC Người 2 | Admin mutation; user đăng nhập được list |
| `P1-BE2-06` | Tạo storage adapter | Local file storage | Config Người 2 | Lưu/xóa file và trả object metadata |
| `P1-BE2-07` | Tạo Media/Detection/Audit models | ORM và migration | DB foundation | Không lưu blob trong DB |
| `P1-BE2-08` | Cài đặt `ActiveLaneChecker` | Lane-check adapter | `P1-BE2-03/04` | Người 1 kiểm tra được lane tồn tại, active và hướng IN/OUT qua interface |
| `P1-BE2-09` | Cài đặt `ImageStorage` | Storage port implementation | `P1-BE2-06` | ALPR API lưu ảnh mà không phụ thuộc local filesystem cụ thể |
| `P1-BE2-10` | Cài đặt `DetectionRecorder` | Persistence port implementation | `P1-BE2-07/09` | Lưu media/detection trong transaction và giữ nguyên kết quả AI ban đầu |
| `P1-BE2-11` | Tạo Detection History API | Recent detections | `P1-BE2-10` | Filter lane và giới hạn số bản ghi |
| `P1-BE2-12` | Tạo Confirmation service | Xác nhận/sửa biển số | Normalizer Người 1 | Lưu AI plate và final plate riêng |
| `P1-BE2-13` | Tạo Confirmation API | Confirmation endpoint | `P1-BE2-12` | Đúng → confirmed; sửa → corrected |
| `P1-BE2-14` | Tạo audit log | Audit confirmation | `P1-BE2-13` | Có actor, before/after và timestamp |
| `P1-BE2-15` | Viết test Backend Domain | Unit/integration tests | Các task trên | Lane, adapter storage/persistence và confirmation/audit đạt |

### Nội dung bàn giao

- Lane OpenAPI contract cho Người 5.
- Các adapter Lane/storage/persistence cho ALPR API của Người 1.
- History và confirmation contract cho Người 4.
- Health dependency state cho Người 2.
- Integration test evidence cho Người 1.

### 6.4. Người 4 — Station Frontend

### Phạm vi sở hữu

```text
frontend/src/layouts/StationLayout.tsx
frontend/src/modules/station/
frontend/tests/station/
```

### Danh sách công việc

| ID | Công việc | Đầu ra | Phụ thuộc | Tiêu chí hoàn thành |
| --- | --- | --- | --- | --- |
| `P1-FE1-01` | Tạo Station layout | Operator shell | App shell Người 5 | Gắn được vào router chung |
| `P1-FE1-02` | Tạo Lane selector | Active Lane list | Lane API + client | Chọn được làn IN/OUT đang active |
| `P1-FE1-03` | Tạo video selector | MP4 file input | Không | File lỗi có thông báo rõ |
| `P1-FE1-04` | Tạo video player | Player controls | `P1-FE1-03` | Play, pause, replay, EOF đúng |
| `P1-FE1-05` | Tạo canvas capture | JPEG frame | `P1-FE1-04` | Lấy frame theo interval cấu hình |
| `P1-FE1-06` | Tạo request controller | Throttle | `P1-FE1-05` | Tối đa một request đang xử lý |
| `P1-FE1-07` | Tạo ALPR API hook | Detection request | API client Người 5 | Gửi image và lane ID đúng multipart |
| `P1-FE1-08` | Tạo state machine | Station states | AI fixtures Người 1 | Đủ idle, processing, detected, confirm, error |
| `P1-FE1-09` | Tạo bbox overlay | Bounding box UI | `P1-FE1-07` | Bbox giữ đúng tỷ lệ khi resize |
| `P1-FE1-10` | Tạo result panel | ALPR result UI | `P1-FE1-07` | Hiển thị plate, confidence, latency, version |
| `P1-FE1-11` | Tạo confirm action | Nút biển số đúng | Confirmation API | Lưu confirmation và cập nhật UI |
| `P1-FE1-12` | Tạo correction form | Nhập lại biển số | Confirmation API | Hỗ trợ AI sai và no-plate |
| `P1-FE1-13` | Tạo recent history | Detection list | History API | Làm mới sau confirmation |
| `P1-FE1-14` | Xử lý lỗi | Error/retry UX | Error contract | Xử lý 401/403/409/422/503/timeout |
| `P1-FE1-15` | Viết Station tests | Component/integration tests | Các task trên | Video, throttle, bbox và confirm test đạt |

### Nội dung bàn giao

- Station route/component entrypoint cho Người 5.
- Evidence video và ảnh chụp luồng Station cho Người 1.
- Danh sách lỗi API/contract phát hiện trong integration.

### 6.5. Người 5 — Frontend Foundation, Login và Admin

### Phạm vi sở hữu

```text
frontend/src/app/
frontend/src/api/
frontend/src/components/
frontend/src/layouts/AuthLayout.tsx
frontend/src/layouts/AdminLayout.tsx
frontend/src/modules/auth/
frontend/src/modules/lanes/
frontend/tests/auth/
frontend/tests/lanes/
```

### Danh sách công việc

| ID | Công việc | Đầu ra | Phụ thuộc | Tiêu chí hoàn thành |
| --- | --- | --- | --- | --- |
| `P1-FE2-01` | Khởi tạo React/Vite/TypeScript | Frontend application | Không | Dev server, test và build chạy được |
| `P1-FE2-02` | Tạo app router | Route structure | `P1-FE2-01` | Có login, station và admin/lanes |
| `P1-FE2-03` | Tạo API client | HTTP client dùng chung | Backend config | Gắn token, timeout và map error |
| `P1-FE2-04` | Tạo AuthProvider | Session state | Login contract Người 2 | Login/logout/current user hoạt động |
| `P1-FE2-05` | Tạo route guards | RBAC UI | `P1-FE2-04` | Operator bị chặn khỏi Admin route |
| `P1-FE2-06` | Tạo Login page | Login form | `P1-FE2-03/04` | Có loading, validation và error |
| `P1-FE2-07` | Tạo shared components | UI foundation | `P1-FE2-01` | Button, input, select, table, dialog, feedback |
| `P1-FE2-08` | Tạo Admin layout | Admin navigation | `P1-FE2-02/05` | Hiển thị current user và role |
| `P1-FE2-09` | Tạo Lane list | Admin Lane table | Lane API Người 3 | Có loading, empty, error và filter |
| `P1-FE2-10` | Tạo Lane form | Create/edit UI | `P1-FE2-09` | Validate name, direction và source |
| `P1-FE2-11` | Tạo inactive action | Confirm action | `P1-FE2-09` | Không hard delete; cập nhật list sau success |
| `P1-FE2-12` | Hiển thị mock banner | Provider status UI | Health API | Không gây hiểu nhầm model đã chạy thật |
| `P1-FE2-13` | Ghép Station route | Integrated frontend | Entry Người 4 | Không sửa code nội bộ Station |
| `P1-FE2-14` | Viết frontend tests | Foundation/Admin tests | Các task trên | Client, auth, role guard và Lane UI đạt |

### Nội dung bàn giao

- App shell, AuthProvider và API client cho Người 4.
- Shared UI components cho Station.
- Login/Admin build và test evidence cho Người 1.

## 7. API contract bắt buộc

### 7.1. Danh sách endpoint

```text
POST  /api/v1/auth/login
GET   /api/v1/auth/me

GET   /api/v1/lanes
GET   /api/v1/lanes/{lane_id}
POST  /api/v1/lanes
PATCH /api/v1/lanes/{lane_id}

POST  /api/v1/alpr/detections
GET   /api/v1/alpr/detections?lane_id=&limit=
POST  /api/v1/alpr/detections/{detection_id}/confirmation

GET   /health/live
GET   /health/ready
```

### 7.2. Detection request

```http
POST /api/v1/alpr/detections
Authorization: Bearer <token>
Content-Type: multipart/form-data
X-Mock-Scenario: <scenario_name> (Tùy chọn)
```

| Field | Kiểu | Bắt buộc | Mô tả |
| --- | --- | :---: | --- |
| `image` | JPEG/PNG file | Có | Frame lấy từ video (giới hạn size) |
| `lane_id` | UUID | Có | Làn đang xử lý |
| `X-Mock-Scenario` | Header | Không | Dùng ép kết quả Mock (`success`, `low_confidence`, `no_plate`, `error`) |

### 7.3. Detection response

```json
{
  "detection_id": "uuid",
  "raw_plate_number": "29A-123.45",
  "normalized_plate_number": "29A12345",
  "bbox": [120, 340, 250, 410],
  "confidence": 0.91,
  "processing_time_ms": 25,
  "model_version": "mock-alpr-0.1.0",
  "requires_confirmation": false
}
```

### 7.4. Confirmation request

Biển số đúng:

```json
{
  "accepted": true
}
```

Biển số sai hoặc AI không đọc được:

```json
{
  "accepted": false,
  "confirmed_plate_number": "29A12345"
}
```

### 7.5. Error response

```json
{
  "code": "ERROR_CODE",
  "message": "Thông báo lỗi",
  "details": {},
  "correlation_id": "uuid"
}
```

Mã lỗi tối thiểu:

| HTTP | Code | Trường hợp |
| ---: | --- | --- |
| 401 | `UNAUTHENTICATED` | Token thiếu, sai hoặc hết hạn |
| 403 | `FORBIDDEN` | Role không có quyền |
| 404 | `LANE_NOT_FOUND` | Không tìm thấy Lane |
| 409 | `DUPLICATE_LANE_NAME` | Tên Lane đã tồn tại |
| 409 | `DETECTION_ALREADY_CONFIRMED` | Operator xác nhận detection lần hai |
| 422 | `INVALID_IMAGE` | File không decode được |
| 422 | `INVALID_PLATE_NUMBER` | Biển số nhập tay không hợp lệ |
| 503 | `ALPR_NOT_READY` | Provider AI không sẵn sàng |
| 503 | `ALPR_PROCESSING_ERROR` | Provider AI xử lý lỗi |

## 8. Mô hình dữ liệu Phase 1

| Bảng | Nội dung chính |
| --- | --- |
| `roles` | Tên role duy nhất |
| `users` | Username, display name, password hash, role, active |
| `lanes` | Name, direction, video source, active |
| `media_objects` | Object key, MIME, size, checksum |
| `alpr_detections` | Lane, media, AI/final plate, bbox, confidence, version, status, confirmer |
| `audit_logs` | Actor, action, resource, before/after, timestamp, correlation ID |

Ràng buộc:

- Username và Lane name là duy nhất.
- Lane direction chỉ nhận `IN` hoặc `OUT`.
- Confidence nằm trong `0.0..1.0`.
- Ảnh không lưu trực tiếp trong PostgreSQL.
- Detection đã confirmed/corrected không bị Operator ghi đè.
- Biển số AI ban đầu phải được giữ lại khi nhân viên sửa.

## 9. Lịch thực hiện và bàn giao

### Ngày 1 — Local Gate và contract

- Người 1 chốt ALPR/error/env contract và Compose.
- Người 2 khởi tạo Backend, DB connection và health.
- Người 3 tạo Lane module/router tối thiểu.
- Người 4 tạo Station route/video placeholder.
- Người 5 khởi tạo Frontend, router và Login placeholder.
- Cuối ngày chạy Local Gate trên ít nhất hai máy.

### Ngày 2 — Nền tảng chạy thật

- Người 1 hoàn thiện ALPR utilities và mock runtime.
- Người 2 hoàn thiện migration, seed, authentication và RBAC.
- Người 3 hoàn thiện Lane CRUD.
- Người 4 hoàn thiện video player và capture.
- Người 5 hoàn thiện Login, AuthProvider và Admin shell.

### Ngày 3 — Detection và giao diện

- Người 1 hoàn thiện `POST /alpr/detections`, fixtures và ALPR API tests.
- Người 2 hoàn thiện health/error/core tests.
- Người 3 hoàn thiện storage, Lane checker và detection persistence adapters.
- Người 4 hoàn thiện throttle, bbox và result states.
- Người 5 hoàn thiện Lane Admin UI và shared components.

### Ngày 4 — Confirmation và integration

- Người 3 hoàn thiện confirmation/audit API.
- Người 4 hoàn thiện xác nhận/sửa biển số và recent history.
- Người 5 ghép Station vào app router.
- Người 1 chạy luồng end-to-end và giao lỗi về đúng owner.

### Ngày 5 — Regression và nghiệm thu

- Chạy clean setup trên máy mới.
- Chạy migration/seed lặp.
- Chạy backend/frontend test, lint và build.
- Kiểm tra đầy đủ auth, RBAC, Lane, video, detection và confirmation.
- Sửa toàn bộ lỗi Critical/High.
- Hoàn thiện README và test evidence.

### Bảng bàn giao

| Bên giao | Bên nhận | Nội dung | Hạn |
| --- | --- | --- | --- |
| Người 1 | Người 2/3/4 | ALPR Detection API, error và readiness contract | Trưa ngày 1 |
| Người 2 | Người 3 | DB session, auth dependency, router convention | Cuối ngày 1 |
| Người 2 | Người 5 | Login/current-user contract | Cuối ngày 2 |
| Người 3 | Người 5 | Lane OpenAPI contract | Trưa ngày 2 |
| Người 3 | Người 1 | `ActiveLaneChecker`, `ImageStorage`, `DetectionRecorder` adapters | Cuối ngày 3 |
| Người 3 | Người 4 | History/confirmation contract | Cuối ngày 3 |
| Người 5 | Người 4 | App shell, API client, AuthProvider, shared UI | Cuối ngày 2 |
| Người 4 | Người 5 | Station route entrypoint | Trưa ngày 4 |
| Người 2–5 | Người 1 | Test/build evidence | Trưa ngày 5 |

## 10. Quy trình quản lý công việc

### 10.1. Trạng thái task

```text
TODO → IN PROGRESS → CODE REVIEW → QA → DONE
```

Task bị chặn dùng trạng thái `BLOCKED`, kèm:

- Nguyên nhân.
- Task hoặc người đang chặn.
- Ảnh hưởng đến deadline.
- Hành động cần thực hiện.
- Thời điểm cần giải quyết.

### 10.2. Quy tắc Git/PR

- Branch: `<type>/<task-id>-<short-name>`.
- Một PR chỉ giải quyết một task hoặc nhóm task liên quan chặt chẽ.
- PR phải ghi task ID, thay đổi, cách test và evidence.
- Tối thiểu một thành viên khác review.
- Thay đổi ALPR/API contract cần Người 1 phê duyệt.
- Không merge khi lint, test hoặc build lỗi.
- Không commit `.env`, secret, video lớn hoặc model weight.
- Không sửa file ngoài ownership nếu chưa có owner review.

### 10.3. Daily 15 phút

Mỗi thành viên báo cáo:

1. Task đã hoàn thành và evidence.
2. Task sẽ chuyển sang Code Review/QA trong ngày.
3. Blocker, người cần hỗ trợ và deadline bị ảnh hưởng.

## 11. Definition of Done

Một task chỉ được xem là hoàn thành khi:

- Code nằm đúng module/owner.
- Không đặt business logic trong endpoint hoặc React component.
- Có migration nếu thay đổi database.
- Có test cho happy path và lỗi chính.
- Authorization và error handling được áp dụng khi cần.
- Không làm thay đổi contract ngoài phê duyệt.
- Lint, test và build đạt.
- PR được review.
- Có log, screenshot hoặc video làm evidence.
- Tài liệu được cập nhật nếu thay đổi interface.
- Không chứa secret, dữ liệu thật, video/model lớn.

## 12. Tiêu chí nghiệm thu Phase 1

- [ ] `docker compose up --build` khởi động thành công.
- [ ] PostgreSQL healthy; migration và seed chạy được từ database rỗng.
- [ ] Admin và Operator đăng nhập được.
- [ ] Đăng nhập sai trả `401`.
- [ ] Operator không gọi được Lane mutation hoặc truy cập Admin page.
- [ ] Admin tạo, xem, sửa và inactive được Lane.
- [ ] Station chọn được Lane đang active.
- [ ] Station chọn và phát được video MP4.
- [ ] Station lấy frame và không tạo nhiều request đồng thời.
- [ ] Backend nhận JPEG/PNG và từ chối file hỏng.
- [ ] Mock ALPR trả response đúng contract.
- [ ] UI hiển thị bbox, biển số, confidence, latency và model version.
- [ ] UI hiển thị rõ `mock-alpr`, không gây hiểu nhầm model thật.
- [ ] Nhân viên xác nhận được biển số đúng.
- [ ] Nhân viên sửa/nhập được biển số khi AI sai hoặc no-plate.
- [ ] Database giữ cả AI plate và final plate.
- [ ] Confirmation lưu người, thời gian và audit log.
- [ ] Timeout, `503` và lỗi video không làm hệ thống crash.
- [ ] `/health/live` và `/health/ready` phản ánh đúng trạng thái.
- [ ] Backend test/lint và frontend test/lint/build đều đạt.
- [ ] Clean setup chạy thành công trên ít nhất hai máy.
- [ ] Không còn lỗi Critical/High.

## 13. Đầu ra bàn giao cuối Phase 1

- Source code backend và frontend.
- Alembic migrations và seed.
- Dockerfile, Compose và `.env.example`.
- ALPR runtime contract và mock provider.
- OpenAPI contract.
- Local image storage adapter.
- Bộ unit/integration/E2E tests.
- Báo cáo QA và evidence.
- README cài đặt, chạy local và tài khoản demo.
- Backlog giai đoạn tiếp theo: dataset, YOLO training, OCR integration và runtime thật.
