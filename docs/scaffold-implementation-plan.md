# Kế hoạch dựng bộ khung VisionPark

## 1. Mục tiêu

Dựng một codebase có thể chạy và chia module cho các thành viên:

- Backend FastAPI khởi động được, có kiến trúc modular monolith.
- Health endpoint hoạt động thật.
- Các router nghiệp vụ tồn tại nhưng trả `501 NOT_IMPLEMENTED`.
- Frontend React có đầy đủ màn hình MVP.
- Các thao tác frontend hoạt động bằng mock service cục bộ.
- Chưa dùng PostgreSQL, authentication thật, API nghiệp vụ, YOLO hoặc PaddleOCR.
- Giao diện chỉ là baseline nhất quán; từng thành viên có thể thiết kế lại sau.

## 2. Backend scaffold

### Cấu trúc

```text
backend/
├── app/
│   ├── api/endpoints/
│   ├── core/
│   ├── database/
│   ├── modules/
│   │   ├── auth/
│   │   ├── users/
│   │   ├── lanes/
│   │   ├── parking/
│   │   ├── monthly_tickets/
│   │   ├── pricing/
│   │   ├── payments/
│   │   ├── reports/
│   │   └── audit_logs/
│   ├── alpr/
│   │   ├── detector/
│   │   ├── recognition/
│   │   ├── normalization/
│   │   └── runtime/
│   ├── integrations/
│   └── main.py
├── tests/
├── pyproject.toml
└── Dockerfile
```

### Chức năng thật

- FastAPI application chạy bằng Uvicorn.
- Prefix nghiệp vụ `/api/v1`.
- CORS cho frontend local.
- Config đọc từ environment.
- Middleware sinh `correlation_id`.
- Exception handler chung.
- OpenAPI/Swagger hoạt động.
- `GET /health/live` trả `200`.
- `GET /health/ready` trả trạng thái `scaffold`, không tuyên bố DB/model đã sẵn sàng.

### Router placeholder

Tạo router cho:

```text
/api/v1/auth
/api/v1/users
/api/v1/lanes
/api/v1/alpr
/api/v1/parking
/api/v1/monthly-tickets
/api/v1/pricing-rules
/api/v1/payments
/api/v1/reports
/api/v1/audit-logs
```

Mỗi router có endpoint đại diện nhưng chưa chứa nghiệp vụ. Khi được gọi, endpoint trả HTTP `501`:

```json
{
  "code": "NOT_IMPLEMENTED",
  "message": "This module has not been implemented.",
  "details": {
    "module": "lanes"
  },
  "correlation_id": "uuid"
}
```

Mỗi module có sẵn các file:

```text
models.py
schemas.py
repository.py
service.py
router.py
```

Các file chỉ chứa interface, kiểu placeholder và TODO gắn owner; không tạo ORM giả hoặc business logic giả.

## 3. Frontend scaffold đầy đủ

### Nền tảng chung

Sử dụng React, TypeScript và Vite:

- Một application cho Station và Admin.
- React Router quản lý route.
- Auth context chạy ở mock mode.
- Shared API/service interface.
- Mock adapter dùng `localStorage`.
- Dữ liệu mock có thể reset về seed ban đầu.
- Shared component cho form, bảng, dialog, trạng thái loading/empty/error.
- Hiển thị banner `DEMO MODE — dữ liệu cục bộ`.
- Không gọi các API `501` trong chế độ mock.

Service được thiết kế theo interface:

```text
UI component
    ↓
Domain service interface
    ↓
Mock adapter hiện tại
    ↓
HTTP API adapter trong giai đoạn sau
```

Khi API thật hoàn thành, chỉ thay adapter; page và component không phải viết lại.

### Route và phân quyền mock

```text
/login
/station
/admin/dashboard
/admin/transactions
/admin/monthly-tickets
/admin/pricing-rules
/admin/payments
/admin/users
/admin/lanes
/admin/reports
/admin/audit-logs
```

Role mô phỏng:

- `ADMIN`: truy cập toàn bộ Admin và Station.
- `OPERATOR`: chỉ truy cập Station.
- `ACCOUNTANT`: Dashboard, giao dịch, thanh toán và báo cáo.
- `TECHNICIAN`: Station, làn và trạng thái kỹ thuật.

Mock login dùng tài khoản demo được ghi rõ trong màn hình. Không xem đây là authentication thật.

### Station

Dựng đầy đủ giao diện vận hành:

- Chọn làn `IN` hoặc `OUT`.
- Chọn video MP4.
- Play, pause, replay và thanh thời gian.
- Khung video và lớp bbox mô phỏng.
- Panel kết quả gồm biển số, confidence, latency và model version.
- Trạng thái idle, processing, detected, needs-confirmation, confirmed và error.
- Nút `Biển số đúng`.
- Nút `Biển số chưa đúng` mở form nhập lại.
- Lưu kết quả xác nhận vào mock storage.
- Danh sách các nhận diện gần nhất.
- Trạng thái “AI chưa được tích hợp” được thể hiện rõ.

Station chưa thực hiện:

- Tách frame thật để gửi backend.
- YOLO detection.
- PaddleOCR.
- Lưu detection vào PostgreSQL.
- Điều khiển barrier.

### Admin Dashboard

- Thẻ số xe trong bãi, lượt vào, lượt ra và doanh thu.
- Biểu đồ mô phỏng theo ngày.
- Danh sách hoạt động gần nhất.
- Bộ lọc khoảng thời gian.
- Dữ liệu lấy từ mock adapter và gắn nhãn demo.

### Quản lý giao dịch

- Danh sách giao dịch.
- Tìm theo biển số.
- Lọc theo trạng thái, loại vé, làn và ngày.
- Xem chi tiết ảnh vào/ra, thời gian và người xử lý.
- Form sửa biển số mô phỏng.
- Hủy giao dịch mô phỏng kèm lý do.
- Mọi thay đổi chỉ lưu localStorage.

### Vé tháng

- Danh sách và tìm kiếm vé.
- Tạo, xem, sửa, gia hạn và inactive.
- Các trường biển số, chủ xe, điện thoại, loại xe, ngày hiệu lực và trạng thái.
- Validation giao diện đầy đủ.

### Biểu phí

- Danh sách phiên bản biểu phí.
- Tạo và sửa bản nháp.
- Chọn loại xe, cách tính, khung giờ, mức tiền và hiệu lực.
- Active/inactive trong mock storage.
- Không triển khai công thức tính phí backend.

### Thanh toán

- Danh sách thanh toán.
- Lọc theo phương thức và trạng thái.
- Màn hình chi tiết.
- Mô phỏng xác nhận tiền mặt/VietQR.
- Không tạo QR thật và không kết nối ngân hàng.

### Người dùng

- Danh sách tài khoản.
- Tạo và sửa người dùng.
- Chọn role.
- Lock/unlock tài khoản.
- Reset password chỉ mô phỏng.
- Không lưu hoặc xử lý mật khẩu thật.

### Làn xe

- Danh sách làn.
- Tạo và sửa làn.
- Chọn hướng `IN/OUT`.
- Nhập nguồn video.
- Active/inactive.
- Seed `LANE_IN_01` và `LANE_OUT_01`.

### Báo cáo và audit

Báo cáo:

- Bộ lọc ngày, làn và loại vé.
- Bảng dữ liệu mô phỏng.
- Xuất CSV từ dữ liệu mock.

Audit:

- Danh sách nhật ký chỉ đọc.
- Lọc theo người dùng, hành động, module và thời gian.
- Xem dữ liệu trước/sau dạng JSON.
- Không cho sửa hoặc xóa.

## 4. Phân chia công việc cho đội 5 người

### 4.1. Nguyên tắc chia module

- Người 1 không dựng toàn bộ backend và frontend. Người 1 chỉ chốt contract, dựng phần ALPR boundary, môi trường chung và thực hiện integration/QA.
- Mỗi thư mục có đúng một người sở hữu chính để tránh hai người sửa cùng file.
- Module chỉ giao tiếp qua schema, router hoặc service interface đã chốt; không import trực tiếp implementation của module khác.
- Mỗi người tự viết test cho module mình sở hữu trước khi bàn giao.
- Thay đổi file dùng chung phải được báo trong nhóm và có Người 1 review.
- Các trang frontend chỉ gọi service interface, không truy cập trực tiếp `localStorage` hoặc endpoint placeholder.

### 4.2. Bảng phân công tổng quát

| Thành viên | Vai trò | Module sở hữu | Kết quả phải bàn giao |
| --- | --- | --- | --- |
| Người 1 | PM Lead, AI boundary, DevOps, QA | Contract, `backend/app/alpr`, Compose, CI, test liên thông | Contract ổn định, ALPR placeholder, môi trường chạy chung, báo cáo QA |
| Người 2 | Backend Core | FastAPI core, database foundation, auth, users | Backend chạy được, health thật, auth/users trả `501`, error contract |
| Người 3 | Backend Domain | Lanes, parking, ticket, pricing, payment, report, audit router | Toàn bộ domain router/module scaffold xuất hiện trên Swagger |
| Người 4 | Station Frontend | `StationLayout`, video UI, ALPR mock, xác nhận biển số | Station hoạt động độc lập bằng mock service |
| Người 5 | Frontend Foundation và Admin | App shell, router, mock auth, shared UI, toàn bộ trang Admin | Frontend shell, phân quyền mock và các trang quản trị chạy được |

### 4.3. Người 1 — PM, ALPR boundary, DevOps và QA

Phạm vi sở hữu:

```text
backend/app/alpr/
deployment/
tests/e2e/
.github/workflows/
compose.yaml
docs/api/
docs/testing/
```

Công việc:

| ID | Công việc | Đầu ra | Phụ thuộc |
| --- | --- | --- | --- |
| `SC-PM-01` | Chốt phạm vi scaffold và Definition of Done | Backlog được cả nhóm xác nhận | Không |
| `SC-PM-02` | Chốt error contract và quy tắc route | Tài liệu contract dùng chung | Không |
| `SC-AI-01` | Định nghĩa `ALPRResult` và runtime interface | Interface chưa chứa YOLO/PaddleOCR | Không |
| `SC-AI-02` | Chuẩn bị ALPR mock result | Bộ kết quả detected/no-plate/error | `SC-AI-01` |
| `SC-OPS-01` | Tạo Dockerfile/Compose baseline | Backend và frontend chạy cùng nhau | Build từ Người 2 và 5 |
| `SC-OPS-02` | Tạo CI lint/test/build | Workflow kiểm tra cả hai application | Test từng module |
| `SC-QA-01` | Viết test plan và acceptance checklist | Checklist kiểm thử 5 workstream | Contract đã chốt |
| `SC-QA-02` | Chạy integration và regression | Báo cáo pass/fail, danh sách lỗi | Bàn giao từ Người 2–5 |

Người 1 không viết API nghiệp vụ, không dựng trang Admin và không thiết kế thay Station. Khi chưa có model đã train, `backend/app/alpr` chỉ có interface, kiểu kết quả và trạng thái `NOT_READY`.

### 4.4. Người 2 — Backend Core

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

Công việc:

| ID | Công việc | Đầu ra | Phụ thuộc |
| --- | --- | --- | --- |
| `SC-BE1-01` | Khởi tạo FastAPI/Python project | Uvicorn khởi động được | Contract Người 1 |
| `SC-BE1-02` | Tạo config và CORS | Settings đọc environment | `SC-BE1-01` |
| `SC-BE1-03` | Tạo correlation middleware | Mọi response có correlation ID | `SC-BE1-01` |
| `SC-BE1-04` | Tạo exception handler | Lỗi đúng format chung | Contract Người 1 |
| `SC-BE1-05` | Tạo live/ready health | Health endpoint hoạt động thật | `SC-BE1-02` |
| `SC-BE1-06` | Scaffold auth/users | Router và module trả `501` | `SC-BE1-04` |
| `SC-BE1-07` | Tạo API router registry | Có điểm gắn router của Người 3 | `SC-BE1-01` |
| `SC-BE1-08` | Viết smoke/unit test | Test startup, health và lỗi `501` | Các task trên |

Người 2 sở hữu `main.py` và router registry. Người 3 chỉ export domain router để Người 2 gắn vào registry, không tự sửa `main.py`.

### 4.5. Người 3 — Backend Domain

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

Công việc:

| ID | Công việc | Đầu ra | Phụ thuộc |
| --- | --- | --- | --- |
| `SC-BE2-01` | Tạo module template | Cấu trúc models/schemas/repository/service/router | Contract Người 1 |
| `SC-BE2-02` | Scaffold Lane | Router Lane xuất hiện trên Swagger | Template module |
| `SC-BE2-03` | Scaffold Parking | Router giao dịch trả `501` | Template module |
| `SC-BE2-04` | Scaffold Monthly Ticket | Router vé tháng trả `501` | Template module |
| `SC-BE2-05` | Scaffold Pricing và Payment | Hai router trả `501` | Template module |
| `SC-BE2-06` | Scaffold Report và Audit | Hai router trả `501` | Template module |
| `SC-BE2-07` | Tạo ALPR HTTP endpoint placeholder | Nhận route nhưng chưa decode/chạy model | ALPR contract Người 1 |
| `SC-BE2-08` | Viết test router | Mọi placeholder trả đúng `501` | Các task trên |

Người 3 không triển khai SQL, ORM, authentication hoặc thuật toán AI trong scaffold. Mỗi router phải có tag, mô tả module và TODO owner rõ ràng.

### 4.6. Người 4 — Station Frontend

Phạm vi sở hữu:

```text
frontend/src/layouts/StationLayout.tsx
frontend/src/modules/station/
frontend/tests/station/
```

Công việc:

| ID | Công việc | Đầu ra | Phụ thuộc |
| --- | --- | --- | --- |
| `SC-FE1-01` | Tạo Station layout | Khung vận hành gắn được vào router chung | App shell Người 5 |
| `SC-FE1-02` | Tạo lane/video selector | Chọn làn và video MP4 | Mock service Người 5 |
| `SC-FE1-03` | Tạo video player | Play, pause, replay, EOF | Không |
| `SC-FE1-04` | Tạo bbox/result mock | Hiển thị bbox và ALPRResult giả | Contract Người 1 |
| `SC-FE1-05` | Tạo state machine | Đủ idle/processing/detected/error | `SC-FE1-04` |
| `SC-FE1-06` | Tạo confirmation UI | Nút đúng/sai và form sửa biển số | `SC-FE1-05` |
| `SC-FE1-07` | Lưu lịch sử nhận diện mock | Danh sách gần nhất qua service interface | Mock adapter Người 5 |
| `SC-FE1-08` | Viết component test | Test video state, result và confirmation | Các task trên |

Người 4 không tạo router, auth context hoặc HTTP client riêng. Các dependency dùng chung phải lấy từ Người 5.

### 4.7. Người 5 — Frontend Foundation và Admin

Phạm vi sở hữu:

```text
frontend/src/app/
frontend/src/api/
frontend/src/components/
frontend/src/layouts/AdminLayout.tsx
frontend/src/layouts/AuthLayout.tsx
frontend/src/modules/auth/
frontend/src/modules/admin/
frontend/src/services/
frontend/tests/admin/
```

Công việc:

| ID | Công việc | Đầu ra | Phụ thuộc |
| --- | --- | --- | --- |
| `SC-FE2-01` | Khởi tạo React/Vite/TypeScript | Frontend build được | Không |
| `SC-FE2-02` | Tạo router và layouts | Login, Station và Admin route | `SC-FE2-01` |
| `SC-FE2-03` | Tạo mock auth và role guard | Điều hướng đúng bốn role | `SC-FE2-02` |
| `SC-FE2-04` | Tạo service interface/mock adapter | Mock data qua localStorage | Contract Người 1 |
| `SC-FE2-05` | Tạo shared components | Table, form, dialog, feedback state | `SC-FE2-01` |
| `SC-FE2-06` | Dựng Dashboard và Transactions | Hai trang hoạt động bằng mock | `SC-FE2-04/05` |
| `SC-FE2-07` | Dựng Tickets, Pricing, Payments | Ba trang hoạt động bằng mock | `SC-FE2-04/05` |
| `SC-FE2-08` | Dựng Users và Lanes | CRUD mô phỏng | `SC-FE2-04/05` |
| `SC-FE2-09` | Dựng Reports và Audit | Filter, CSV và JSON detail | `SC-FE2-04/05` |
| `SC-FE2-10` | Viết frontend foundation/admin test | Route, role, form và mock CRUD | Các task trên |

Người 5 bàn giao router, auth context, shared components và mock service sớm để Người 4 không bị chặn. Các trang Admin dùng chung template bảng/form để giảm khối lượng và giữ nhất quán.

## 5. Trình tự triển khai song song

### Ngày 1 — Contract và nền tảng

- Người 1 chốt scope, error contract, ALPRResult, directory ownership và Git rule.
- Người 2 khởi tạo backend, health và router registry.
- Người 3 tạo module template và danh sách domain router.
- Người 5 khởi tạo frontend, router, auth context và service interface.
- Người 4 dựng video player độc lập và Station wireframe.

Bàn giao bắt buộc cuối ngày:

- Người 1 → Người 2/3/4/5: contract và mock types.
- Người 2 → Người 3: cách export/gắn domain router.
- Người 5 → Người 4: app shell, auth context và mock service interface.

### Ngày 2 — Phát triển độc lập

- Người 1 tạo ALPR boundary, test plan và Compose skeleton.
- Người 2 hoàn thiện core, middleware, error handling, auth/users placeholder.
- Người 3 hoàn thiện Lane, Parking, Ticket, Pricing và Payment scaffold.
- Người 4 hoàn thiện video UI, mock result, bbox và state machine.
- Người 5 hoàn thiện shared components, login, Dashboard và Transactions.

### Ngày 3 — Hoàn thiện module

- Người 1 tạo CI và bộ integration smoke test.
- Người 2 hoàn thiện backend unit test và tài liệu bootstrap.
- Người 3 hoàn thiện Report/Audit/ALPR router và router test.
- Người 4 hoàn thiện confirmation UI, history và Station test.
- Người 5 hoàn thiện Tickets, Pricing, Payments, Users và Lanes.

### Ngày 4 — Ghép hệ thống

- Người 2 ghép router của Người 3 vào FastAPI.
- Người 5 ghép Station route của Người 4 vào app shell.
- Người 1 ghép Docker Compose, chạy lint/test/build và kiểm tra contract.
- Người 3 sửa lỗi backend domain; Người 4/5 sửa lỗi frontend theo đúng ownership.

### Ngày 5 — Regression và bàn giao

- Cả nhóm chạy checklist trên môi trường sạch.
- Người 1 tổng hợp lỗi và quyết định pass/fail.
- Không còn lỗi Critical/High.
- README ghi rõ module owner, mock boundary và phần chưa triển khai.

### Điểm bàn giao giữa các thành viên

| Bên giao | Bên nhận | Nội dung | Hạn |
| --- | --- | --- | --- |
| Người 1 | Cả nhóm | Error contract, ALPRResult, DoD | Trưa ngày 1 |
| Người 2 | Người 3 | FastAPI/router registration convention | Cuối ngày 1 |
| Người 5 | Người 4 | Router, auth context, service interface | Cuối ngày 1 |
| Người 3 | Người 2 | Domain router exports và router tests | Cuối ngày 3 |
| Người 4 | Người 5 | Station route/component entrypoint | Cuối ngày 3 |
| Người 2–5 | Người 1 | Build và test evidence | Trưa ngày 4 |

Task bị chậm quá nửa ngày phải chuyển sang `BLOCKED`, ghi rõ nguyên nhân, người cần hỗ trợ và ảnh hưởng đến bàn giao.

## 6. Kiểm thử và tiêu chí nghiệm thu

### Backend

- FastAPI khởi động không lỗi.
- Swagger liệt kê đầy đủ module.
- `/health/live` trả `200`.
- `/health/ready` phản ánh đây là scaffold.
- Router chưa triển khai trả đúng `501`.
- Mọi lỗi có `correlation_id`.
- Module không import ngược vào endpoint hoặc module không liên quan.

### Frontend

- Tất cả route mở được theo role.
- Operator không truy cập trang Admin.
- Mỗi trang có loading, empty và error state.
- CRUD mô phỏng hoạt động và giữ dữ liệu sau refresh.
- Có thể reset toàn bộ mock data.
- Station chọn và phát được MP4.
- Nút xác nhận/sửa biển số hoạt động với mock result.
- Không có request ngoài ý muốn tới backend.
- Không có lỗi hoặc warning trong browser console.
- Build production thành công.

### Definition of Done

Bộ khung được chấp nhận khi:

- Backend và frontend cùng chạy được.
- Toàn bộ module backend đã có đúng vị trí.
- Toàn bộ trang MVP đã có route và chức năng mô phỏng.
- UI không khiến người dùng nhầm dữ liệu mock là dữ liệu thật.
- Các module có thể giao riêng cho từng thành viên.
- Thay mock adapter bằng HTTP adapter không yêu cầu viết lại page.
- README chỉ rõ phần đã dựng, phần chưa triển khai và owner dự kiến.
- CI lint/test/build đều đạt.
- Không có thành viên sửa ngoài thư mục sở hữu khi chưa được owner review.
- Mỗi module có README/TODO nêu rõ điểm mở rộng cho API thật.

## 7. Ngoài phạm vi giai đoạn này

- PostgreSQL schema, migration và seed thật.
- Authentication/JWT thật.
- API CRUD thật.
- YOLO, PaddleOCR và huấn luyện model.
- Frame sampling và gửi ảnh thật tới backend.
- Check-in/check-out nghiệp vụ.
- Tính phí và thanh toán thật.
- Redis hoặc cache nghiệp vụ.
- Camera, barrier và VietQR thật.
- Thiết kế UI cuối cùng.
