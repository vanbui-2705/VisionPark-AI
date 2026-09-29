## 1. Phase 1 gate và contract chung

- [ ] 1.1 [Người 1] Chạy Phase 1 clean-install/CI gate và lập danh sách Critical/High carry-over trước khi bắt đầu Phase 2.
- [ ] 1.2 [Cả đội, Người 1 chủ trì] Chốt request/response contract cho check-in, lỗi duplicate, idempotency và manual confirmation; cập nhật OpenAPI/schema fixture.
- [ ] 1.3 [Người 1] Chốt policy dataset/model ngoài Git, manifest format, provider config và benchmark command.
- [ ] 1.4 [Người 2, 3, 4, 5] Tạo branch theo task và thêm test fixture chung cho plate, lane IN, no-plate và confidence thấp.

## 2. Real ALPR provider — Người 1

- [x] 2.1 Tạo provider adapter/config để chọn `mock` hoặc `real` mà không thay đổi caller của runtime boundary.
- [x] 2.2 Bổ sung model manifest, kiểm tra path/checksum/version và readiness `not_ready` khi asset không hợp lệ.
- [ ] 2.3 Kết nối detector/OCR baseline thật theo interface hiện có; trả đúng plate, bbox, confidence, latency và model version.
- [ ] 2.4 Viết contract tests cho success, no-plate, confidence thấp, model thiếu và inference error.
- [ ] 2.5 Tạo benchmark script/report với dataset split cố định; ghi model version, số mẫu, detection/OCR result và latency summary.

## 3. Backend Core và persistence — Người 2

- [ ] 3.1 Thiết kế model/migration additive cho parking transaction `PARKED`, detection link, source confirmation và audit fields.
- [ ] 3.2 Bổ sung cơ chế lưu idempotency key và payload fingerprint theo transaction/check-in scope.
- [ ] 3.3 Gắn check-in dependency với auth, DB session, error contract và correlation ID hiện có.
- [ ] 3.4 Viết migration upgrade/downgrade và test trên SQLite/PostgreSQL disposable; xác nhận không làm mất detection Phase 1.
- [ ] 3.5 Cập nhật seed/fixture lane IN và tài liệu vận hành migration.

## 4. Check-in domain/API — Người 3

- [ ] 4.1 Implement request/response schema và application service tạo check-in từ ALPR result đã xác nhận hoặc biển số nhập tay.
- [ ] 4.2 Implement validation lane IN active, plate normalization, auth/role và reject input rỗng/không hợp lệ.
- [ ] 4.3 Implement duplicate protection cho plate đang `PARKED` và idempotency retry/conflict.
- [ ] 4.4 Implement audit cho AI plate, final plate, nguồn xác nhận, actor, lane và timestamp.
- [ ] 4.5 Implement history endpoint với filter plate, lane, time range và status.
- [ ] 4.6 Viết unit/integration tests cho happy path, manual fallback, duplicate, retry, unauthorized và inactive lane.

## 5. Station check-in UI — Người 4

- [ ] 5.1 Tích hợp Station với check-in contract và state machine loading/success/error/manual confirmation.
- [ ] 5.2 Hiển thị plate, bbox, confidence, latency, model version và cảnh báo `requires_confirmation`.
- [ ] 5.3 Implement confirm/edit plate trước khi submit; khóa submit lặp trong cùng request.
- [ ] 5.4 Implement UI cho provider not ready, duplicate, timeout, lỗi mạng và retry/fallback.
- [ ] 5.5 Viết component/integration tests cho kết quả tốt, no-plate, sửa biển số và check-in thành công/thất bại.

## 6. Operations/Admin UI — Người 5

- [ ] 6.1 Cập nhật API client/types cho check-in, history, audit và lỗi typed; không tạo HTTP client thứ hai.
- [ ] 6.2 Implement trang/danh sách lịch sử check-in với filter plate, lane, khoảng thời gian và trạng thái.
- [ ] 6.3 Áp dụng quyền Operator/Admin cho thao tác check-in, xem lịch sử và xem audit theo contract backend.
- [ ] 6.4 Hiển thị nguồn xác nhận, AI plate/final plate, actor và timestamp để hỗ trợ truy vết.
- [ ] 6.5 Viết UI tests cho filter, permission và empty/error states.

## 7. Integration, CI và nghiệm thu — Người 1 chủ trì

- [ ] 7.1 [Cả đội] Ghép flow mock end-to-end: Station frame → ALPR → confirm/edit → check-in `PARKED` → history/audit.
- [ ] 7.2 [Người 1, 2, 3] Chạy real provider trên môi trường có model asset; xác nhận readiness, benchmark và rollback về mock.
- [ ] 7.3 [Người 1] Cập nhật CI để chạy backend/frontend tests, migration checks và mock E2E không cần GPU/model weight.
- [ ] 7.4 [Cả đội] Chạy regression, security/role checks, duplicate race/idempotency checks và clean setup trên DB rỗng.
- [ ] 7.5 [Người 1] Hoàn tất QA report, benchmark report, API/docs/README và video hoặc screenshot evidence.
- [ ] 7.6 [Cả đội] Demo theo acceptance checklist; chỉ đóng Phase 2 khi CI xanh, migration pass, không còn Critical/High và manual fallback hoạt động.
