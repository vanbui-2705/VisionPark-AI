## Context

Phase 1 đã có modular monolith FastAPI, PostgreSQL/Alembic, JWT/RBAC, ALPR runtime boundary với mock provider, Station UI và CI. Backend handoff còn yêu cầu giữ mock làm đường chạy ổn định; real provider và check-in phải được thêm mà không kéo business logic vào module ALPR.

Phase 2 được tổ chức cho 5 người trong 3 tuần làm việc, theo một vertical slice duy nhất: real ALPR tùy chọn → xác nhận biển số → check-in `PARKED` → xem lịch sử. Mỗi người giữ owner cũ và mọi thay đổi contract đi qua Người 1 review.

## Goals / Non-Goals

**Goals:**

- Có real ALPR provider chạy qua interface hiện có, có manifest, readiness, benchmark và version.
- Có check-in API có auth, lane validation, duplicate protection, idempotency và audit.
- Có Station/Operations UI dùng được end-to-end với manual fallback.
- CI vẫn chạy được không cần GPU, model weight hoặc dataset nhạy cảm.
- Có migration, integration/E2E tests và evidence cho demo.

**Non-Goals:**

- Không triển khai check-out, fee calculation, monthly ticket, payment/VietQR.
- Không kết nối camera RTSP, barrier thật hoặc thiết bị I/O.
- Không triển khai CRM, slot map, Redis, WebSocket hoặc production MLOps.
- Không đưa model weight hay dữ liệu biển số thật vào Git.

## Decisions

### 1. Giữ runtime boundary và tách provider

Real provider implement cùng interface với mock provider. Config chọn provider; mock là mặc định trong local/CI, real provider chỉ bật khi manifest và model path hợp lệ. Cách này giữ test deterministic và cho phép rollback bằng một biến cấu hình.

**Alternative considered:** gọi YOLO/OCR trực tiếp từ endpoint. Không chọn vì phá boundary hiện có và làm backend phụ thuộc implementation AI.

### 2. Check-in thuộc domain parking, không thuộc ALPR

ALPR chỉ trả dữ liệu nhận diện. Parking/check-in chịu trách nhiệm lane, transaction, duplicate, idempotency và audit. Detection có thể được liên kết với transaction nhưng không quyết định trạng thái bãi xe.

**Alternative considered:** để ALPR tự tạo parking transaction. Không chọn vì khó test, sai ownership và cản trở payment/check-out về sau.

### 3. Confirm-before-create

API chỉ tạo `PARKED` sau khi người vận hành xác nhận biển số. Confidence cao vẫn được phép xác nhận nhanh; confidence thấp/no-plate bắt buộc nhập tay. Điều này giữ manual fallback và tránh tạo giao dịch từ kết quả AI chưa kiểm chứng.

### 4. Idempotency ở application boundary

Check-in nhận `Idempotency-Key`, lưu fingerprint payload và transaction result. Retry cùng payload trả kết quả cũ; payload khác với cùng key trả conflict. Unique rule trên active parked plate là lớp bảo vệ thứ hai.

### 5. Dataset và model ngoài Git

Repository chỉ lưu manifest, schema, fixture nhỏ không nhạy cảm và script benchmark. Dataset thật/model weight đặt ngoài repository; CI dùng mock và fixture tổng hợp. Benchmark phải ghi rõ dataset version, model version và môi trường chạy.

### 6. Kế hoạch 5 người và nhịp triển khai

| Người | Owner Phase 2 | Đầu ra chính |
|---|---|---|
| 1 | AI Lead, PM, DevOps, QA | contract, provider, manifest/benchmark, CI, E2E và release gate |
| 2 | Backend Core | transaction schema/migration, idempotency infrastructure, auth/error wiring |
| 3 | Backend Domain | check-in service/API, duplicate/lane rules, audit/history |
| 4 | Station Frontend | capture, result display, confirm/edit/manual fallback, check-in state |
| 5 | Admin/Operations Frontend | API types/client, history/filter, permissions, UI integration tests |

Các task bắt đầu bằng contract/schema chung trong ngày 1; backend/API hoàn thiện skeleton trong tuần 1; UI và real provider tích hợp trong tuần 2; tuần 3 dành cho integration, regression, benchmark và demo.

## Risks / Trade-offs

- **[Model accuracy chưa đủ] →** báo cáo baseline trước khi đặt ngưỡng; giữ manual confirmation và mock fallback, không tuyên bố production accuracy.
- **[Model weight làm CI nặng hoặc lộ dữ liệu] →** không commit weight/dataset; real-provider test chạy riêng có asset được cấp quyền, CI chỉ chạy contract/mock tests.
- **[Migration làm hỏng DB Phase 1] →** migration additive, backup trước khi áp dụng, test upgrade/downgrade trên DB disposable.
- **[Duplicate do retry hoặc race condition] →** idempotency fingerprint kết hợp unique constraint/transaction ở database.
- **[Scope bị kéo sang payment/barrier] →** các hạng mục đó ghi backlog Phase 3+, không nhận vào PR Phase 2.
- **[Phase 1 còn hạng mục chưa hoàn tất] →** chạy Phase 1 exit gate trước; blocker Critical/High phải được đóng hoặc ghi nhận rõ là carry-over trước khi demo Phase 2.

## Migration Plan

1. Chạy CI và clean-install gate của Phase 1.
2. Thêm bảng/field check-in theo migration additive, seed lane IN fixture và kiểm tra upgrade/downgrade trên DB test.
3. Deploy với mock provider mặc định; xác nhận API/UI check-in hoạt động end-to-end.
4. Bật real provider ở môi trường có model manifest hợp lệ; kiểm tra readiness và benchmark trước demo.
5. Nếu real provider lỗi, chuyển config về mock; dữ liệu transaction/check-in không bị xóa.
