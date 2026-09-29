## Why

Phase 1 đã tạo được nền tảng, mock ALPR và contract chung nhưng hệ thống chưa có model ALPR thật hoặc luồng nghiệp vụ ghi nhận xe vào bãi. Phase 2 cần biến baseline đó thành một vertical slice có thể đo được: ALPR thật ở chế độ tùy chọn và check-in có xác nhận, vẫn giữ mock provider để CI và local development ổn định.

## What Changes

- Bổ sung dataset/benchmark và real ALPR provider theo runtime boundary hiện có.
- Giữ mock provider làm mặc định cho CI; real provider được bật bằng cấu hình và model manifest, không commit model weight.
- Bổ sung nghiệp vụ check-in: chọn lane IN, nhận kết quả ALPR, xác nhận hoặc sửa biển số, tạo parking transaction trạng thái `PARKED`.
- Chống tạo giao dịch trùng cho cùng biển số đang `PARKED` và hỗ trợ idempotency cho request check-in.
- Bổ sung API/UI xem lịch sử check-in, trạng thái xử lý, lỗi và thao tác xác nhận thủ công.
- Bổ sung audit cho xác nhận/sửa biển số và các quyết định check-in.
- Bổ sung integration/E2E tests, CI checks và báo cáo benchmark cho Phase 2.
- Không đưa payment, VietQR, tính phí, vé tháng, barrier thật, RTSP, CRM, slot map, Redis hoặc WebSocket vào phase này.

## Capabilities

### New Capabilities

- `real-alpr-provider`: Chạy detector/OCR thật qua ALPR runtime interface, có manifest, readiness, version và benchmark.
- `parking-check-in`: Tạo và xác nhận lượt xe vào, chống trùng, idempotency, lưu trạng thái và audit.
- `check-in-operations-ui`: Giao diện Station và Operations cho nhận diện, xác nhận/sửa biển số và xem lịch sử check-in.

### Modified Capabilities

Không thay đổi requirement của `alpr-runtime-boundary`; real provider phải tuân thủ contract hiện có. Việc chuyển từ mock sang real provider được mô tả như capability mới.

## Impact

- Backend: `backend/app/alpr`, modules parking/check-in, persistence models, Alembic migrations, API schemas và integration tests.
- Frontend: Station check-in flow, API client/types, confirmation dialog, history/operations view và UI tests.
- DevOps/QA: model manifest/configuration, dataset fixture metadata, CI job, benchmark script và E2E evidence.
- Runtime dependencies: provider AI tùy chọn; CI không phụ thuộc model weight hoặc GPU.
- Database/API: thêm parking transaction/check-in records, idempotency key và audit fields; các thay đổi contract phải được review trước khi merge.
