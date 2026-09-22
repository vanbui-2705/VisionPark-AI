# VisionPark Phase 1 — Backlog 5 thành viên, ưu tiên local-first

## 1. Mục tiêu

Chia hệ thống thành năm workstream có thể phát triển song song và có khối lượng tương đương:

| Thành viên | Role chính | Phạm vi |
| --- | --- | --- |
| Người 1 | AI Lead, Integration, QA | ALPR contract/mock, Compose, kiểm thử liên thông |
| Người 2 | Backend Core | FastAPI core, config, DB connection, auth/users scaffold |
| Người 3 | Backend Domain | Lane và các domain router/API placeholder |
| Người 4 | Frontend Station/Operations | Station, video, ALPR UI, transaction/payment mock |
| Người 5 | Frontend Foundation/Admin | App shell, mock auth/service, các trang quản trị |

Mỗi người có **20 effort point**. Point dùng để cân bằng tương đối, không phải số giờ cam kết.

Ưu tiên cao nhất là hệ thống chạy ổn định trên local trước khi phát triển sâu:

```text
docker compose up --build
├── frontend: http://localhost:5173
├── backend:  http://localhost:8000
├── swagger:  http://localhost:8000/docs
└── postgres: localhost:5432
```

## 2. Quy tắc làm việc chung

- Ngày đầu tiên chỉ tập trung đạt Local Gate; chưa dựng hàng loạt page hoặc module.
- Mỗi thư mục có một owner chính; người khác không sửa nếu chưa trao đổi với owner.
- Frontend chỉ phụ thuộc service interface, không gọi trực tiếp `localStorage`.
- Backend domain chỉ export router; không tự sửa `main.py` hoặc backend core.
- Mọi endpoint chưa triển khai trả cùng error contract `501 NOT_IMPLEMENTED`.
- ALPR chưa có model chỉ trả trạng thái `NOT_READY`; không giả vờ đã nhận diện thật.
- Model weight, video lớn, secret và dữ liệu thật không được commit.
- Mỗi task chỉ chuyển `DONE` khi có test hoặc bằng chứng chạy tương ứng.

## 3. Local Gate — cả đội hoàn thành trước

### Điều kiện đạt

- Clone repository mới và làm theo README không cần sửa source.
- `.env.example` chứa đủ biến cấu hình nhưng không có secret thật.
- Backend chạy trực tiếp bằng Uvicorn và qua Docker.
- Frontend chạy trực tiếp bằng Vite và qua Docker.
- PostgreSQL container healthy; backend kiểm tra được kết nối.
- `/health/live` trả `200`.
- `/health/ready` phân biệt rõ `database=ready` và `alpr=not_ready`.
- Frontend mở được `/login` và `/station` mà không có console error.
- Backend/frontend tự reload được trong local development.
- `docker compose down` rồi `up` lại không làm hỏng môi trường.

### Đóng góp của từng người cho Local Gate

| Người | Việc bắt buộc trước Local Gate |
| --- | --- |
| Người 1 | `.env.example`, Compose, quy ước port/volume và smoke checklist |
| Người 2 | FastAPI entrypoint, health API, PostgreSQL connectivity |
| Người 3 | Một router mẫu `/api/v1/lanes` trả `501` để kiểm tra module registration |
| Người 4 | Station route và video placeholder render được |
| Người 5 | React/Vite, router, Login route và frontend Dockerfile |

Không bắt đầu tích hợp module xuyên hệ thống nếu Local Gate chưa đạt.

## 4. Người 1 — AI Lead, Integration và QA

Phạm vi sở hữu:

```text
backend/app/alpr/
deployment/
tests/e2e/
.github/workflows/
compose.yaml
.env.example
docs/api/
docs/testing/
```

| ID | Subtask | Point | Phụ thuộc | Definition of Done |
| --- | --- | ---: | --- | --- |
| `AI-01` | Chốt kiểu `ALPRResult` | 2 | Không | Có schema cho detected, no-plate và not-ready |
| `AI-02` | Chốt error/state của AI runtime | 2 | `AI-01` | Có `READY`, `NOT_READY`, `PROCESSING_ERROR` |
| `AI-03` | Tạo runtime interface | 2 | `AI-01` | Có `detect_and_read(frame)` nhưng chưa chứa model |
| `AI-04` | Tạo mock result fixtures | 2 | `AI-01` | Frontend/backend test dùng chung được |
| `AI-05` | Viết normalization và test | 2 | Không | Chuẩn hóa chữ hoa, khoảng trắng, dấu chấm/gạch |
| `AI-06` | Viết bbox clamp và test | 2 | Không | Bbox không vượt khỏi ảnh, bbox lỗi được từ chối |
| `OPS-01` | Tạo `.env.example` và Compose | 2 | Backend/Frontend bootstrap | Ba service khởi động được |
| `QA-01` | Viết smoke/integration checklist | 3 | Contract đã chốt | Bao phủ health, route, role, video và ALPR state |
| `QA-02` | Chạy regression và tổng hợp evidence | 3 | Bàn giao Người 2–5 | Có báo cáo pass/fail và không còn lỗi High |
|  | **Tổng** | **20** |  |  |

Đầu ra bàn giao:

- `ALPRResult` và mock JSON cho Người 3, 4 và 5.
- AI runtime boundary cho Người 3 gọi trong giai đoạn sau.
- Compose và hướng dẫn chạy local cho cả nhóm.
- Báo cáo QA cuối vòng.

## 5. Người 2 — Backend Core

Phạm vi sở hữu:

```text
backend/app/main.py
backend/app/api/router.py
backend/app/core/
backend/app/database/
backend/app/modules/auth/
backend/app/modules/users/
backend/tests/unit/core/
backend/tests/unit/auth/
```

| ID | Subtask | Point | Phụ thuộc | Definition of Done |
| --- | --- | ---: | --- | --- |
| `BE1-01` | Khởi tạo Python/FastAPI project | 2 | Không | Uvicorn chạy được bằng một lệnh |
| `BE1-02` | Tạo settings/environment loader | 2 | `BE1-01` | Thiếu biến bắt buộc có lỗi rõ ràng |
| `BE1-03` | Cấu hình CORS và API prefix | 2 | `BE1-01` | Frontend local gọi được health API |
| `BE1-04` | Tạo correlation middleware | 2 | `BE1-01` | Mỗi response có correlation ID |
| `BE1-05` | Tạo error handler dùng chung | 2 | Contract Người 1 | Lỗi đúng schema thống nhất |
| `BE1-06` | Tạo PostgreSQL engine/session scaffold | 2 | `BE1-02` | Backend kết nối được container DB |
| `BE1-07` | Tạo live/ready health | 2 | `BE1-06`, AI state | Health phản ánh DB và model riêng biệt |
| `BE1-08` | Scaffold auth/users module | 3 | `BE1-05` | Router có trên Swagger và trả `501` |
| `BE1-09` | Viết backend core tests | 3 | Các task trên | Startup, config, health và error test đạt |
|  | **Tổng** | **20** |  |  |

Đầu ra bàn giao:

- Backend foundation cho Người 3 gắn domain router.
- Router registration convention.
- Database dependency placeholder cho giai đoạn viết repository thật.
- Health contract cho Người 1 kiểm thử.

## 6. Người 3 — Backend Domain

Phạm vi sở hữu:

```text
backend/app/modules/lanes/
backend/app/modules/parking/
backend/app/modules/monthly_tickets/
backend/app/modules/pricing/
backend/app/modules/payments/
backend/app/modules/reports/
backend/app/modules/audit_logs/
backend/app/api/endpoints/
backend/tests/unit/modules/
```

| ID | Subtask | Point | Phụ thuộc | Definition of Done |
| --- | --- | ---: | --- | --- |
| `BE2-01` | Tạo domain module template | 2 | Error contract | Có schema/repository/service/router boundary |
| `BE2-02` | Tạo Lane router placeholder | 2 | Router convention Người 2 | Route xuất hiện trên Swagger |
| `BE2-03` | Tạo Parking router placeholder | 2 | `BE2-01` | Route giao dịch trả đúng `501` |
| `BE2-04` | Tạo Monthly Ticket router | 2 | `BE2-01` | Route vé tháng trả đúng `501` |
| `BE2-05` | Tạo Pricing router | 2 | `BE2-01` | Route biểu phí trả đúng `501` |
| `BE2-06` | Tạo Payment router | 2 | `BE2-01` | Route thanh toán trả đúng `501` |
| `BE2-07` | Tạo Report và Audit router | 2 | `BE2-01` | Hai module có tag riêng trên Swagger |
| `BE2-08` | Tạo ALPR endpoint placeholder | 3 | ALPR contract Người 1 | Endpoint công bố input/output nhưng trả not-ready |
| `BE2-09` | Viết domain router tests | 3 | Các task trên | Toàn bộ route và error response được kiểm tra |
|  | **Tổng** | **20** |  |  |

Đầu ra bàn giao:

- Domain router exports cho Người 2 đăng ký.
- Swagger trình bày đầy đủ các nhóm API tương lai.
- Module boundary rõ để từng API được triển khai sau mà không đổi kiến trúc.

## 7. Người 4 — Frontend Station và Operations

Phạm vi sở hữu:

```text
frontend/src/layouts/StationLayout.tsx
frontend/src/modules/station/
frontend/src/modules/transactions/
frontend/src/modules/payments/
frontend/tests/station/
frontend/tests/operations/
```

| ID | Subtask | Point | Phụ thuộc | Definition of Done |
| --- | --- | ---: | --- | --- |
| `FE1-01` | Tạo Station layout | 2 | App shell Người 5 | Route Station render trong shell chung |
| `FE1-02` | Tạo lane/video selector | 2 | Mock service Người 5 | Chọn được lane và MP4 hợp lệ |
| `FE1-03` | Tạo video player | 2 | Không | Play, pause, replay và EOF hoạt động |
| `FE1-04` | Tạo ALPR state machine | 2 | Contract Người 1 | Có idle/processing/detected/error/not-ready |
| `FE1-05` | Tạo bbox/result overlay mock | 2 | `FE1-03/04` | Bbox giữ tỷ lệ khi video resize |
| `FE1-06` | Tạo confirmation workflow | 2 | Mock service | Xác nhận đúng hoặc sửa biển số được lưu mock |
| `FE1-07` | Tạo recent detection history | 2 | `FE1-06` | Hiển thị và lọc được kết quả gần nhất |
| `FE1-08` | Dựng Transactions và Payments UI | 3 | Shared components Người 5 | Hai trang lọc/xem chi tiết bằng mock |
| `FE1-09` | Viết Station/Operations tests | 3 | Các task trên | Video state, ALPR state và confirmation test đạt |
|  | **Tổng** | **20** |  |  |

Đầu ra bàn giao:

- Station hoàn chỉnh ở mock mode.
- Trang giao dịch và thanh toán mô phỏng.
- Station entrypoint để Người 5 gắn vào router chung.

## 8. Người 5 — Frontend Foundation và Admin

Phạm vi sở hữu:

```text
frontend/src/app/
frontend/src/api/
frontend/src/components/
frontend/src/layouts/AdminLayout.tsx
frontend/src/layouts/AuthLayout.tsx
frontend/src/modules/auth/
frontend/src/modules/dashboard/
frontend/src/modules/lanes/
frontend/src/modules/users/
frontend/src/modules/monthly-tickets/
frontend/src/modules/pricing-rules/
frontend/src/modules/reports/
frontend/src/modules/audit-logs/
frontend/src/services/
frontend/tests/admin/
```

| ID | Subtask | Point | Phụ thuộc | Definition of Done |
| --- | --- | ---: | --- | --- |
| `FE2-01` | Khởi tạo React/Vite/TypeScript | 2 | Không | Dev server và production build chạy được |
| `FE2-02` | Tạo router và layouts | 2 | `FE2-01` | Login, Station và Admin route tồn tại |
| `FE2-03` | Tạo mock auth/role guard | 2 | `FE2-02` | Bốn role điều hướng đúng |
| `FE2-04` | Tạo domain service interfaces | 2 | Contract Người 1 | UI không phụ thuộc trực tiếp storage/API |
| `FE2-05` | Tạo localStorage mock adapter | 2 | `FE2-04` | Seed, CRUD và reset mock data được |
| `FE2-06` | Tạo shared table/form/dialog/state | 2 | `FE2-01` | Người 4 tái sử dụng được |
| `FE2-07` | Dựng Dashboard, Lane và User | 2 | `FE2-05/06` | Ba trang hoạt động bằng mock |
| `FE2-08` | Dựng Ticket, Pricing, Report, Audit | 3 | `FE2-05/06` | Các trang lọc/CRUD/xem chi tiết được |
| `FE2-09` | Viết foundation/Admin tests | 3 | Các task trên | Router, role, mock CRUD và form test đạt |
|  | **Tổng** | **20** |  |  |

Đầu ra bàn giao:

- Frontend application shell dùng chung.
- Auth context, route guard, mock services và shared components.
- Các trang quản trị chạy độc lập bằng dữ liệu mock.

## 9. Lịch thực hiện đề xuất

### Ngày 1 — Chạy local ổn định

- Buổi sáng: Người 1, 2 và 5 ghép Compose, backend và frontend tối thiểu.
- Người 3 tạo Lane router mẫu; Người 4 tạo Station route mẫu.
- Cuối ngày: cả nhóm cùng chạy Local Gate trên ít nhất hai máy.
- Chỉ khi Local Gate đạt mới merge baseline và bắt đầu module riêng.

### Ngày 2 — Phát triển module độc lập

- Người 1: ALPR contract, runtime interface, mock fixtures.
- Người 2: core middleware, error handler, DB readiness.
- Người 3: domain module template và các router chính.
- Người 4: video player, Station states và bbox mock.
- Người 5: auth, shared components và mock adapter.

### Ngày 3 — Hoàn thiện chức năng mock

- Người 1: normalization, bbox clamp và AI unit test.
- Người 2: auth/users placeholder và core test.
- Người 3: hoàn thiện toàn bộ router và test.
- Người 4: confirmation, history, transaction/payment pages.
- Người 5: hoàn thiện các trang Admin.

### Ngày 4 — Integration

- Người 2 đăng ký router của Người 3.
- Người 5 đăng ký Station/Operations của Người 4.
- Người 1 chạy Compose, smoke test và contract review.
- Mỗi owner sửa lỗi trong đúng phạm vi module của mình.

### Ngày 5 — Regression và bàn giao

- Chạy clean setup trên máy chưa từng cài dự án.
- Chạy backend tests, frontend tests và build.
- Kiểm tra toàn bộ route và role.
- Tổng hợp evidence và lỗi còn lại.
- Không bàn giao nếu còn lỗi Critical/High hoặc Local Gate không ổn định.

## 10. Điểm bàn giao bắt buộc

| Bên giao | Bên nhận | Nội dung | Hạn |
| --- | --- | --- | --- |
| Người 1 | Cả nhóm | Error contract, ALPRResult, env convention | Trưa ngày 1 |
| Người 2 | Người 3 | Router registration và backend core | Cuối ngày 1 |
| Người 5 | Người 4 | App shell, service interface, shared UI | Cuối ngày 1 |
| Người 3 | Người 2 | Domain router exports | Cuối ngày 3 |
| Người 4 | Người 5 | Station/Operations entrypoints | Cuối ngày 3 |
| Người 2–5 | Người 1 | Test/build evidence | Trưa ngày 4 |

Nếu bàn giao trễ quá nửa ngày, task phải chuyển `BLOCKED` và ghi rõ người cần hỗ trợ.

## 11. Definition of Done chung

- Module nằm đúng thư mục owner.
- Không có business logic thật trong scaffold placeholder.
- Không giả lập rằng YOLO/PaddleOCR đã hoạt động.
- Mỗi route/page có loading, empty hoặc error state phù hợp.
- Test của module đạt trên local.
- Docker build thành công.
- Không có lỗi hoặc warning nghiêm trọng trong browser console/backend log.
- README của module nêu rõ phần đã có, phần chưa làm và điểm thay mock bằng implementation thật.
- PR ghi task ID, cách chạy test và evidence.
- Không merge khi Local Gate, lint, test hoặc build thất bại.

## 12. Ngoài phạm vi vòng scaffold

- Train hoặc tích hợp YOLO.
- Tích hợp hoặc fine-tune PaddleOCR.
- Authentication/JWT thật.
- Migration và bảng nghiệp vụ thật.
- API CRUD thật.
- Check-in/check-out, tính phí hoặc thanh toán thật.
- Camera, barrier, VietQR và Redis thật.
- Thiết kế giao diện cuối cùng.
