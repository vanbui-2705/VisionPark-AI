# VisionPark — danh sách khoảng trống và việc cần cải thiện

Ngày rà soát: 06/11/2026  
Phạm vi: README, tài liệu M5, OpenSpec đang mở và code backend/frontend. Đây là rà soát tĩnh; lượt này không chạy lại test, build, Docker hay thiết bị thật. Các số liệu test/benchmark bên dưới nếu nhắc tới là từ báo cáo ngày 05/11/2026, không phải kết quả chạy mới.

## Kết luận

VisionPark đã có nền tảng backend cho check-in/check-out, pricing, ticket, báo cáo M5, device heartbeat và quản lý làn; frontend đã có màn hình vận hành Station cho check-in, dashboard và các trang quản trị. Tuy nhiên, chưa thể coi đây là sản phẩm sẵn sàng vận hành thương mại: còn lỗi nghiêm trọng ở xác nhận thanh toán, sổ doanh thu không nối với checkout CASH, luồng giao diện xe ra OUT chưa được tìm thấy trong code frontend của nhánh đang rà soát và chất lượng ALPR đang bị giữ ở release gate.

Không dùng tỷ lệ phần trăm test để đại diện độ hoàn thiện sản phẩm. Mức phù hợp hiện tại là MVP cần hoàn tất chức năng cốt lõi và nghiệm thu có giám sát.

## Việc cần làm theo ưu tiên

### P0 — Chặn sai lệch thu tiền và mở cổng

- [ ] Xác thực số tiền thu so với phí phải thu trong luồng `record_payment`; quy định rõ trường hợp miễn/giảm/override, quyền thực hiện và lý do bắt buộc.
- [ ] Chỉ chấp nhận payment method thuộc danh sách hỗ trợ. Không coi việc client gửi tên phương thức là bằng chứng thanh toán điện tử đã thành công.
- [ ] Nối checkout CASH với sổ giao dịch/hóa đơn/thanh toán và báo cáo; cập nhật phiên, khoản thu, audit và counter nhất quán trong transaction phù hợp.
- [ ] Định nghĩa lượt ra để bao gồm trường hợp miễn phí/vé tháng, không phụ thuộc vào việc mọi lượt đều có invoice thu tiền.
- [ ] Khi trả kết quả mở cổng, phân biệt lệnh mở đã gửi với phản hồi xác nhận thiết bị đã mở; hiện code ghi event mô phỏng rồi đặt `barrier_opened=True`.
- [ ] Bổ sung kiểm thử âm và xuyên suốt: thu thiếu/thu thừa, phương thức lạ, retry, ghi trùng, miễn/giảm, checkout → báo cáo → đối soát.

Bằng chứng code: `backend/app/modules/checkout/schemas.py` nhận `amount >= 0` và `payment_method` dạng chuỗi; `backend/app/modules/checkout/service.py` gán trạng thái `PAID` mà không so `amount` với phí, và nhánh checkout có thể hoàn tất khi chỉ cần `payment_method` có giá trị. `_complete_session` ghi barrier event mô phỏng và trả `barrier_opened=True`. M5 tổng hợp lượt ra từ `Invoice` và doanh thu từ `Payment`, trong khi checkout hiện chưa ghi các bản ghi tương ứng.

### P1 — Bổ sung luồng check-out vào Station (không phải tạo làn OUT)

- Đã có model/API và UI quản lý làn `IN/OUT`; admin có thể tạo, sửa, lọc và xem chi tiết làn OUT.
- Đã có backend API check-out, preview phí và ghi nhận thanh toán.
- Đã có màn hình Station vận hành check-in; mục này **không nói toàn bộ màn hình vận hành hoặc làn OUT đang thiếu**.
- [ ] Mở rộng Station hiện có để dùng làn OUT: tìm phiên xe, xem ảnh vào/ra và biển số, xem thời gian/phí, xử lý lệch xe/mất vé, thu CASH và hoàn tất xe ra.
- [ ] Bổ sung quản lý/gia hạn vé tháng và import xe CSV có preview, kiểm lỗi, kết quả từng dòng và khả năng đối soát.
- [ ] Nối giao diện cấu hình sức chứa bãi với API settings; dùng số liệu sức chứa đáng tin cậy trên dashboard.
- [ ] Chạy UAT các kịch bản tại UI với vai trò nhân viên; không chỉ xác nhận API/backend.

Bằng chứng code: `backend/app/modules/lanes/models.py` có `LaneDirection.OUT`; `frontend/src/modules/lanes/LaneForm.tsx` cho chọn IN/OUT và `LaneListPage.tsx` lọc/hiển thị cả hai hướng. `backend/app/modules/checkout/router.py` cung cấp API preview/check-out/payment. Điểm thiếu là `frontend/src/modules/station/api.ts` chỉ lấy làn `IN`, còn `StationPage.tsx` hiện triển khai ALPR/check-in; chưa thấy giao diện gọi checkout/payment API. Dashboard M5 đang trả `capacity`/`available` là `null`. Đã đối chiếu cả `main` (767b72f) và `van-dev` (8cbc7bf): `van-dev` đã chứa `main`, nhưng tìm kiếm frontend trên hai ref không thấy gọi checkout hoặc payment API.

### P1 — Gỡ HOLD ALPR bằng phép đo đúng

- [ ] Sửa benchmark để so kết quả nhận diện với ground truth và tính verdict tự động từ ngưỡng đã công bố.
- [ ] Chạy trên dữ liệu có quyền sử dụng, tách tập theo xe/video, ghi provenance, model/hash, phần cứng và điều kiện ngày/đêm/mưa; báo cáo exact match, character accuracy, false positive, tỷ lệ sửa tay và p95.
- [ ] Giữ manual confirmation/fail-safe cho kết quả chưa đủ tin cậy; không tự mở barrier chỉ dựa vào readiness hoặc checksum model.
- [ ] Chỉ đóng release gate khi có evidence độc lập, truy vết và chạy lại được.

Bằng chứng tài liệu: OpenSpec Phase 2 còn task quality blocker; báo cáo đánh giá 05/11 ghi benchmark hiện có không chứng minh exact match của model đang triển khai và release gate chất lượng chưa đạt. Các số liệu cũ cần được chạy lại đúng model/hash trước khi kết luận.

### P1 — Đảm bảo đúng khi retry và nhiều trạm cùng thao tác

- [ ] Dùng idempotency record có unique constraint và request fingerprint cho checkout; tránh dò key trong chuỗi `notes`.
- [ ] Khóa/kiểm tra phiên phù hợp để hai trạm không cùng thu tiền hoặc đóng một phiên hai lần.
- [ ] Chạy test concurrency trên PostgreSQL; kiểm tra retry cùng payload và retry khác payload.
- [ ] Rà soát đối soát counter cho mọi trạng thái xe còn hiện diện vật lý trong bãi, không chỉ `PARKED`.
- [ ] Xác minh tenant/building scope cho checkout, báo cáo, settings, heartbeat và các thao tác override.

### P1 — Nghiệm thu vận hành và khôi phục

- [ ] Kết nối adapter camera/barrier/heartbeat thật, có timeout, trạng thái thiết bị, xác nhận lệnh, cảnh báo được lưu và lịch sử xử lý.
- [ ] Chạy backup/restore và Docker lifecycle trên môi trường riêng, có đối chiếu số bản ghi và checksum media.
- [ ] Chứng minh quy trình daily-stat rebuild có lịch chạy và cảnh báo thất bại; hiện tài liệu M5 yêu cầu cấu hình scheduler riêng.
- [ ] Bổ sung checklist triển khai, rollback tương thích migration, monitoring và hướng dẫn xử lý mất điện/mất mạng.

### P2 — Nâng cấp tạo khác biệt sau khi luồng lõi ổn định

- [ ] Đối soát ca: tiền đầu ca, phải thu, tiền đếm, chênh lệch, miễn/giảm/hoàn và bàn giao có audit.
- [ ] Hoạt động LAN khi mất Internet, đồng bộ lại có chống trùng và quy trình xử lý xung đột.
- [ ] Tương thích camera/đầu đọc cũ và import dữ liệu bãi đang hoạt động để giảm chi phí chuyển đổi.
- [ ] Portal cư dân/vé tháng, QR và thanh toán điện tử sau khi sổ CASH và đối soát đã đáng tin cậy.
- [ ] Đa bãi/cảnh báo chủ động khi có yêu cầu khách hàng và bằng chứng vận hành thực tế.

## Trạng thái OpenSpec cần dọn

`openspec list --json` hiện có ba change còn mở:

- `phase-2-alpr-checkin`: 128/131 task; còn quality blocker và yêu cầu evidence độc lập.
- `complete-real-data-system`: 61/62 task; gate P6 vẫn mở vì thiếu report/evidence nghiệm thu chất lượng.
- `build-local-system-with-mock-alpr`: 89/92 task; còn xác nhận Local Gate trên hai máy và regression ban đầu.

Không đánh dấu các change này hoàn tất bằng readiness, mock evidence hoặc bằng chứng cũ không khớp model. Sau khi đối chiếu phạm vi trùng nhau, cập nhật task/evidence và archive change hoàn tất. Tài liệu hiện có module M5 và patch `M5-README.md`, nhưng không thấy một OpenSpec change hay kế hoạch nghiệm thu riêng có tên Phase 5; M5 trong một số tài liệu cũng có nghĩa là thành viên số 5.

## Thứ tự đề xuất

1. Sửa xác thực thanh toán, sổ giao dịch và điều kiện trả kết quả mở barrier.
2. Hoàn thành giao diện OUT, vé tháng và cấu hình bãi cho nhân viên vận hành.
3. Chạy test xuyên suốt và concurrency bằng PostgreSQL; nghiệm thu checkout → báo cáo → đối soát.
4. Chạy benchmark ALPR đúng model/hash trên dữ liệu độc lập và quyết định release gate.
5. Nghiệm thu thiết bị, backup/restore, scheduler và pilot có giám sát.
6. Sau pilot mới ưu tiên offline LAN, tích hợp thiết bị cũ, portal cư dân, QR và đa bãi.

