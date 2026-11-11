# Kế hoạch cải thiện và nghiệm thu VisionPark ở chế độ FILE_UPLOAD

Ngày lập: 08/11/2026  
Phạm vi đánh giá: nhánh `van-dev`, sau khi hợp nhất `origin/main` tại commit `d133345`  
Mục tiêu: nghiệm thu hệ thống vận hành thật với đầu vào JPEG/PNG/MP4; `LIVE_CAMERA/RTSP` là tích hợp tiếp theo và ALPR quality được đánh giá bằng gate độc lập

## 1. Kết luận hiện trạng

VisionPark là hệ thống thật gồm đăng nhập, nhận diện biển số, check-in, check-out, thu tiền mặt, cập nhật sức chứa, dashboard và audit log. Chế độ đầu vào hiện tại là upload JPEG/PNG hoặc MP4; frontend trích frame video và gửi vào real ALPR provider. Mức sẵn sàng nghiệm thu hệ thống hiện được ước tính khoảng 70%.

Các phần còn ngăn cản nghiệm thu hệ thống đáng tin cậy:

1. Checkout CASH chưa ghi thống nhất vào sổ `Invoice`/`Payment`, nên doanh thu và lượt xe ra có thể không khớp dashboard.
2. Backend còn chấp nhận `payment_method` dưới dạng chuỗi tùy ý và chưa xác thực số tiền tại luồng `record_payment`.
3. Station OUT chưa có giao diện xử lý đầy đủ cho sai loại xe, mất vé, xe không biển số hoặc tìm phiên bằng mã vé.
4. Release gate ALPR hiện tại không còn khớp README và có nhánh benchmark tổng hợp không chứng minh độ chính xác model thật.
5. Backend formatter check đang thất bại; Docker runtime chưa được xác nhận vì Docker daemon chưa chạy tại lần kiểm tra.
6. Chưa có một bộ acceptance media và quy trình chuẩn bị lại môi trường kiểm thử có thể chạy nhiều lần.

Sau khi hoàn thành kế hoạch này, mục tiêu là nghiệm thu được toàn bộ phạm vi `FILE_UPLOAD`. Tích hợp camera live/RTSP, các thiết bị ngoại vi chưa kết nối và vận hành quy mô production có kế hoạch riêng.

## 2. Phạm vi nghiệm thu hệ thống

### 2.1. Chức năng phải chạy thật

- Đăng nhập bằng tài khoản `OPERATOR` hoặc `BUILDING_ADMIN`.
- Chọn làn IN và nhận diện biển số từ ảnh JPEG/PNG hoặc video MP4 đã chuẩn bị.
- Xác nhận hoặc sửa biển số khi confidence thấp.
- Check-in và cập nhật số xe đang trong bãi.
- Chặn check-in trùng biển số.
- Chọn làn OUT, tìm phiên đang gửi và hiển thị ảnh vào/ra.
- Preview thời gian gửi và phí từ price snapshot.
- Xác nhận thu tiền mặt `CASH`.
- Hoàn tất checkout, giảm bộ đếm và ghi barrier event thật vào hệ thống. Việc điều khiển barrier vật lý được kết luận riêng theo adapter/controller thực tế.
- Xem dashboard, lịch sử giao dịch và audit log.
- Trình diễn một xe vé tháng nếu dữ liệu và pricing đã được seed ổn định.

### 2.2. Ngoài phạm vi FILE_UPLOAD hiện tại

- Camera RTSP trực tiếp.
- Phần cứng nào chưa có adapter/controller được xác nhận trên môi trường triển khai.
- VietQR hoặc ngân hàng thật.
- Heartbeat từ thiết bị thật.
- Vận hành offline và đồng bộ lại khi có mạng.
- Benchmark ALPR thực địa hoặc tuyên bố độ chính xác thương mại.
- Backup/restore production, HA và disaster recovery.
- Portal cư dân, voucher, đặt chỗ và dự báo cao điểm.
- Chuỗi xử lý sự cố cháy/khói ngoài hiện trường.

Không được gọi toàn hệ thống là mock hoặc mô phỏng. UI/tài liệu phải ghi rõ input mode là `FILE_UPLOAD`, `LIVE_CAMERA/RTSP` chưa tích hợp, và trạng thái thiết bị ngoại vi đúng theo evidence triển khai.

## 3. Baseline kỹ thuật

Kết quả kiểm tra ngày 08/11/2026:

| Hạng mục | Kết quả |
| --- | --- |
| Backend tests | 343 test được thu thập; 340 PASS, 3 PostgreSQL concurrency test SKIP |
| Backend lint | `ruff check app scripts tests` PASS |
| Backend format | FAIL; 6 file cần format, trong đó có file thuộc phạm vi CI |
| Frontend tests | 83/83 PASS |
| Frontend lint | Exit code 0, còn 13 cảnh báo React/hooks |
| Frontend build | PASS; bundle chính khoảng 532 kB, có cảnh báo code splitting |
| Docker Compose | `docker compose config --quiet` PASS |
| Model assets | 5 checksum detector/OCR PASS |
| Docker runtime | Chưa xác nhận do Docker daemon không chạy |
| ALPR evidence gần nhất | Quality gate vẫn HOLD: validation exact match 25%, demo exact match 0% |

Ba OpenSpec change vẫn đang mở:

- `phase-2-alpr-checkin`: 128/131 task.
- `complete-real-data-system`: 61/62 task.
- `build-local-system-with-mock-alpr`: 89/92 task.

## 4. Hạng mục cần build mới và cần cải thiện

Phần này là phạm vi implementation chính thức cho đợt nghiệm thu hệ thống. Mỗi hạng mục phải tạo ra code, migration, test hoặc tài liệu có thể kiểm tra được; không chỉ dừng ở việc mô tả hiện trạng.

### 4.1. Các thành phần cần build mới

#### BUILD-01 — Checkout idempotency record

Xây một bảng/bản ghi idempotency riêng cho checkout và payment, thay cho việc chỉ dò key trong `ParkingTransaction.notes`.

Đầu ra dự kiến:

- Alembic migration tạo bảng hoặc unique constraint cần thiết.
- Model chứa `key`, `operation`, `request_fingerprint`, `transaction_id`, trạng thái và response tham chiếu.
- Repository/service để tạo, replay và phát hiện key được dùng lại với payload khác.
- Test retry tuần tự và test đồng thời trên PostgreSQL.

Vị trí code dự kiến:

- `backend/app/database/idempotency.py` hoặc module idempotency chuyên biệt.
- `backend/app/modules/checkout/service.py`.
- `backend/alembic/versions/`.
- `backend/tests/integration/`.

#### BUILD-02 — Checkout ledger orchestration

Xây một lớp orchestration dùng chung để hoàn tất CASH checkout và ghi đồng bộ:

- `ParkingTransaction`.
- `Invoice`.
- `Payment`.
- Lifecycle events.
- Audit log.
- Parking counter.

Orchestration phải chạy trong transaction phù hợp và không tạo bản ghi trùng khi retry.

Đầu ra dự kiến:

- Service/hàm hoàn tất checkout dùng chung cho direct CASH và `record_payment`.
- Mapping rõ trạng thái `PENDING`, `PAID`, `WAIVED`, `FAILED` và `COMPLETED`.
- Test chứng minh invoice/payment/report khớp với phí checkout.

Vị trí code dự kiến:

- `backend/app/modules/checkout/service.py`.
- `backend/app/modules/pricing/billing.py` hoặc một adapter ledger dùng chung.
- `backend/app/modules/m5/service.py`.

#### BUILD-03 — Station OUT exception panel

Xây component giao diện cho các trường hợp Station OUT không thể xử lý bằng nút CASH thông thường:

- Tìm phiên bằng biển số hoặc mã vé.
- Đánh dấu mất vé.
- Hiển thị sai loại xe/sai thông tin.
- Nhập lý do override.
- Kiểm tra quyền trước khi cho phép override.
- Yêu cầu preview lại khi phí thay đổi.

Đầu ra dự kiến:

- Component exception/override riêng, không nhồi toàn bộ logic vào `StationPage.tsx`.
- API payload truyền `ticket_code`, `is_lost_ticket`, `vehicle_type_out` và `override_reason`.
- Test UI cho từng nhánh ngoại lệ.

Vị trí code dự kiến:

- `frontend/src/modules/station/components/`.
- `frontend/src/modules/station/api.ts`.
- `frontend/src/modules/station/StationPage.tsx`.
- `frontend/tests/station/`.

#### BUILD-04 — Chuẩn bị và reset môi trường acceptance

Xây command chuyên dụng để chuẩn bị lại môi trường test/acceptance mà không chỉnh thủ công trong database.

Command cần:

- Tạo/cập nhật building acceptance.
- Tạo user acceptance từ mật khẩu được cung cấp qua biến môi trường.
- Tạo làn IN/OUT.
- Tạo capacity và pricing version.
- Tạo ticket product, xe và subscription acceptance.
- Chỉ xóa/reset dữ liệu nằm trong namespace acceptance được xác định rõ; không reset production.
- Chạy lặp lại không tạo dữ liệu trùng.

Đầu ra dự kiến:

- Script `backend/scripts/seed_demo_environment.py` hoặc mở rộng script seed hiện có.
- Chế độ `--check`, `--apply` và xác nhận database target.
- Integration test cho lần chạy thứ nhất và lần chạy lặp lại.

Không hard-code secret hoặc tự động chạy trên production.

#### BUILD-05 — Acceptance media manifest

Xây manifest cho bộ ảnh/video dùng để kiểm thử và nghiệm thu, chứa:

- ID kịch bản.
- Đường dẫn media.
- SHA-256.
- Expected plate/scenario.
- Nguồn và quyền sử dụng.
- Phân loại rõ functional acceptance media và independent quality dataset.

Đầu ra dự kiến:

- Manifest trong `backend/datasets/` hoặc `docs/demo-evidence/`.
- Script kiểm tra file tồn tại và checksum đúng.
- Bộ media đủ cho success, low confidence, no plate, manual fallback và ảnh vào/ra.

#### BUILD-06 — System Functional Gate

Xây một gate riêng đánh giá tính đúng của hệ thống thật ở chế độ `FILE_UPLOAD`:

- Database readiness.
- API/frontend health.
- Dữ liệu acceptance hợp lệ.
- Check-in và duplicate protection.
- Checkout CASH và idempotency.
- Ledger/report/counter nhất quán.
- Manual fallback.

Gate phải trả exit code khác 0 khi bất kỳ điều kiện nào thất bại và xuất JSON report có commit/environment.

Đầu ra dự kiến:

- Script `backend/scripts/system_gate.py`.
- Không dùng tên hoặc kết quả của gate này để tuyên bố ALPR accuracy.
- Được gọi trong checklist dry-run hoặc CI profile phù hợp.

#### BUILD-07 — System E2E test

Xây test xuyên suốt cho kịch bản chính:

```text
check-in → counter tăng → preview checkout → CASH payment
→ invoice/payment → checkout complete → counter giảm
→ dashboard/report → audit
```

Đầu ra dự kiến:

- Backend integration/E2E test kiểm tra dữ liệu database cuối luồng.
- Frontend test kiểm tra người dùng thao tác đúng nút và payload.
- Test replay cùng idempotency key.
- PostgreSQL test cho hai request checkout đồng thời.

### 4.2. Các thành phần hiện có cần sửa hoặc cải thiện

#### IMPROVE-01 — Payment schema và validation

- Đổi `payment_method` từ chuỗi tự do thành enum/tập giá trị kiểm soát.
- Bắt buộc `expected_fee` đối với direct CASH có phí.
- So sánh `amount` với phí phải thu trong `record_payment`.
- Quy định rõ thu thừa, thu thiếu, miễn/giảm và override.
- Không cho chuyển `PAID` trước khi validation hoàn tất.

#### IMPROVE-02 — Checkout transaction boundary

- Gom các thay đổi transaction, ledger, counter và audit vào transaction boundary rõ ràng.
- Rollback toàn bộ nếu invoice/payment/counter ghi thất bại.
- Phân biệt barrier business event đã ghi trong hệ thống với ACK của controller vật lý; kết luận trạng thái thiết bị theo adapter triển khai.

#### IMPROVE-03 — M5 dashboard và báo cáo

- Đếm lượt ra từ nguồn dữ liệu phản ánh mọi checkout, gồm cả lượt miễn phí/vé tháng.
- Tính doanh thu từ payment đã xác nhận.
- Không hiển thị `occupancy_peak=0` như số liệu thật; dùng `null`/`not_calculated` cho đến khi có cách tính.
- Thêm test đối soát một lượt CASH từ Station tới daily stats và cash shift.

#### IMPROVE-04 — Station OUT UX

- Tách state machine rõ giữa detect, preview, exception, payment, completed.
- Không để nút bị disable mà không có hướng dẫn xử lý.
- Khóa submit lặp và giữ cùng idempotency key cho cùng một phiên.
- Sau checkout chỉ hiển thị nút xe tiếp theo.
- Hiển thị rõ trạng thái barrier business event và trạng thái controller vật lý, không suy diễn hai trạng thái là một.

#### IMPROVE-05 — Release gate ALPR

- Khôi phục hoặc thay thế lệnh functional gate đã ghi trong README.
- Loại bỏ nhánh dùng `expected_plate` làm đầu vào rồi tính accuracy.
- Giữ quality gate ở trạng thái HOLD nếu không có dataset thực độc lập.
- System Functional Gate và ALPR Quality Gate phải là hai command/report khác nhau.

#### IMPROVE-06 — CI và code quality

- Format các file đang làm `ruff format --check` thất bại.
- Chạy test/lint/format trong cùng môi trường với CI.
- Xử lý warning hooks ảnh hưởng Station/settings.
- Chỉ tối ưu bundle sau khi luồng nghiệp vụ hệ thống ổn định.

#### IMPROVE-07 — Tài liệu và operational runbook

- Đồng bộ README với command thực tế.
- Cập nhật `docs/UAT-Demo-Script.md` theo kịch bản A–E.
- Ghi tài khoản/secret bằng biến môi trường, không commit giá trị thật.
- Thêm checklist preflight, reset, warmup, port, health và troubleshooting.
- Ghi rõ: hệ thống thật ở chế độ `FILE_UPLOAD`, chưa tích hợp `LIVE_CAMERA/RTSP`, trạng thái barrier theo adapter thực tế, CASH operational workflow và ALPR quality PASS/FAIL/HOLD độc lập.

### 4.3. Thành phần chưa cần build trong phạm vi FILE_UPLOAD

Các hạng mục sau được đưa vào backlog tích hợp/pilot riêng, không nằm trong critical path nghiệm thu hiện tại:

- RTSP/live camera adapter.
- Barrier controller vật lý, PLC và cảm biến xe qua cổng.
- VietQR/ngân hàng production.
- Device agent và persistent alert workflow.
- Offline sync.
- HA, autoscaling và disaster recovery production.
- Portal cư dân, voucher, đặt chỗ và dự báo.
- Incident workflow cháy/khói đầy đủ.

## 5. Thứ tự triển khai

```text
Sửa CASH và ledger
        ↓
Hoàn thiện Station OUT tối thiểu
        ↓
Tạo dữ liệu acceptance và acceptance media
        ↓
Sửa release gate, CI và tài liệu
        ↓
Chạy E2E + Docker dry-run
        ↓
Nghiệm thu theo UAT System Script
```

Không đảo thứ tự bằng cách làm giao diện hoặc dashboard trước khi sổ tiền được thống nhất, vì hệ thống có thể báo checkout thành công nhưng báo cáo doanh thu bằng 0.

## 6. Backlog ưu tiên

| ID | Ưu tiên | Công việc | Kết quả đầu ra | Tiêu chí hoàn thành |
| --- | --- | --- | --- | --- |
| DEMO-01 | P0 | Giới hạn phương thức thanh toán Station | Enum/validation chỉ chấp nhận `CASH` trong workflow hiện tại | Chuỗi lạ bị backend từ chối bằng lỗi 422/400 có mã rõ ràng |
| DEMO-02 | P0 | Xác thực tiền phải thu | So sánh số tiền thanh toán với phí snapshot/fee hiện tại | Thu thiếu hoặc thu thừa bị từ chối; override cần quyền và lý do |
| DEMO-03 | P0 | Nối checkout CASH với ledger | Checkout tạo/settle `Invoice` và `Payment` trong transaction phù hợp | Một checkout chỉ sinh một invoice/payment; retry không tạo trùng |
| DEMO-04 | P0 | Đồng bộ dashboard và báo cáo | Lượt ra, doanh thu, số xe trong bãi đọc từ dữ liệu thống nhất | Sau một lượt vận hành, counter và báo cáo thay đổi đúng một lần |
| DEMO-05 | P0 | Sửa CI format | Format các file đang fail và chạy lại pipeline | Backend test/lint/format cùng PASS |
| DEMO-06 | P0 | Tách hai acceptance gate | Tách System Functional Gate khỏi ALPR Quality Gate | Functional gate không tuyên bố accuracy; README command chạy được |
| DEMO-07 | P1 | Hoàn thiện Station OUT tối thiểu | UI xử lý phí thay đổi, mismatch và override có lý do | Không còn trạng thái nút bị khóa mà không có cách xử lý |
| DEMO-08 | P1 | Tìm phiên theo mã vé | Station OUT hỗ trợ `ticket_code` cho xe không biển số/xe đạp | Có test frontend và integration tương ứng |
| DEMO-09 | P1 | Kịch bản mất vé có kiểm soát | Checkbox/action mất vé và hiển thị phí mất vé | Phí và audit thể hiện đúng `is_lost_ticket` |
| DEMO-10 | P1 | Dữ liệu acceptance idempotent | Một lệnh tạo lại building, users, lanes, pricing, capacity và vé tháng trên môi trường acceptance | Chạy hai lần không tạo bản ghi trùng hoặc đổi mật khẩu ngoài ý muốn |
| DEMO-11 | P1 | Acceptance media cố định | Ảnh/video được cấp quyền sử dụng và có manifest/checksum | Mỗi media gắn với expected scenario, không phụ thuộc Internet |
| DEMO-12 | P1 | System E2E tự động | Test check-in → checkout CASH → report → audit | Toàn bộ luồng PASS trên database test riêng |
| DEMO-13 | P1 | Deployment verification | Build, migrate, seed, health và chạy hệ thống bằng Compose | Backend/frontend/database healthy; restart và chạy lại thành công |
| DEMO-14 | P1 | Cập nhật tài liệu vận hành | README, UAT và troubleshooting thống nhất | Người khác có thể vận hành FILE_UPLOAD chỉ bằng tài liệu |
| DEMO-15 | P2 | Dọn cảnh báo frontend | Sửa warning hooks quan trọng và code splitting cơ bản | Không còn warning ảnh hưởng Station/settings; build vẫn PASS |

## 7. Thiết kế luồng CASH operational

### 7.1. Nguyên tắc

- Station chỉ gửi `CASH` cho lượt có phí.
- Phí bằng 0 được hoàn tất không cần tạo khoản thu, nhưng vẫn phải tạo dấu vết checkout.
- Với phí lớn hơn 0, transaction chỉ chuyển `COMPLETED` khi payment đã được tạo và xác nhận.
- Invoice, payment, parking transaction, lifecycle event và counter phải nhất quán.
- Retry cùng idempotency key và cùng payload trả lại kết quả cũ.
- Retry cùng key nhưng payload khác phải trả lỗi xung đột.
- Không dùng chuỗi trong `notes` làm cơ chế idempotency chính cho code mới.

### 7.2. Test bắt buộc

- CASH đúng số tiền → hoàn tất, một invoice, một payment.
- Thu thiếu → từ chối, barrier không mở, session chưa hoàn tất.
- Thu thừa → từ chối hoặc yêu cầu quy trình được chốt rõ.
- Phương thức lạ → từ chối.
- Double-click nút thu tiền → không tạo thanh toán trùng.
- Retry cùng key → cùng response nghiệp vụ.
- `expected_fee` cũ → trả `FEE_CHANGED`, yêu cầu preview lại.
- Checkout hoàn tất → counter giảm đúng một lần.
- Dashboard/report → doanh thu và lượt ra khớp payment/transaction.

## 8. Hoàn thiện Station OUT cho phạm vi hiện tại

Station OUT phải có các trạng thái rõ ràng:

1. Chưa nhận diện được xe.
2. Đã nhận diện nhưng chưa tìm thấy phiên vào.
3. Đã tìm thấy phiên và đang preview phí.
4. Cần xác nhận ngoại lệ.
5. Sẵn sàng thu CASH hoặc mở cổng miễn phí.
6. Đang xử lý, khóa submit lặp.
7. Hoàn tất và sẵn sàng cho xe tiếp theo.

Các thay đổi tối thiểu:

- Thêm lựa chọn tìm bằng biển số hoặc mã vé.
- Thêm lựa chọn mất vé cho workflow vận hành.
- Hiển thị cảnh báo sai loại xe và trường nhập lý do override.
- Chỉ cho role có quyền thực hiện override.
- Hiển thị riêng barrier event của hệ thống và ACK của controller vật lý; không tuyên bố thiết bị đã mở nếu chưa nhận ACK.
- Khi API trả `FEE_CHANGED`, bắt buộc preview lại trước khi xác nhận.
- Sau khi hoàn tất, vô hiệu hóa nút thu tiền và chỉ cho chuyển sang xe tiếp theo.

## 9. Dữ liệu và acceptance media

### 9.1. Dữ liệu seed tối thiểu

- Building: `DEMO-BUILDING`.
- Tài khoản: một building admin và một operator.
- Hai làn: `DEMO-IN-01`, `DEMO-OUT-01`.
- Sức chứa cho ô tô và xe máy.
- Một pricing version đang hiệu lực.
- Một ticket product loại `MONTHLY`.
- Một xe vé tháng còn hạn.
- Không seed giao dịch đang mở trừ khi kịch bản cụ thể yêu cầu.

Mật khẩu môi trường acceptance phải được cung cấp qua biến môi trường hoặc hướng dẫn cục bộ, không commit secret vào repository.

### 9.2. Acceptance media tối thiểu

- Ảnh biển rõ để kiểm tra luồng thành công.
- Ảnh confidence thấp để kiểm tra xác nhận/sửa tay.
- Ảnh không có biển để kiểm tra manual fallback.
- Video MP4 ngắn dùng cùng workflow với ảnh.
- Ảnh vào và ảnh ra cho cùng một xe để đối chiếu.

Mỗi file cần có nguồn/quyền sử dụng, checksum và expected result. Functional acceptance media và independent quality dataset phải được phân loại riêng.

## 10. System Functional Gate và ALPR Quality Gate

Hai gate phải tách biệt:

### 10.1. System Functional Gate

Được phép sử dụng test double/fixture có ghi nhãn rõ để xác nhận:

- API và UI chạy đúng workflow.
- Manual fallback hoạt động.
- Check-in/check-out idempotent trong workflow thật.
- Payment, counter, report và audit nhất quán.
- Lỗi dependency không làm mất khả năng xử lý thủ công.

### 10.2. ALPR quality gate

Chỉ được PASS khi chạy model thật trên dataset ảnh/video thật có ground truth độc lập. Không lấy `expected_plate` làm đầu vào inference hoặc fallback tính accuracy. Nếu chưa đủ evidence, giữ trạng thái `HOLD`; trạng thái này độc lập với nghiệm thu chức năng hệ thống.

## 11. Kịch bản trình diễn chuẩn

### Kịch bản A — Xe vãng lai vào và trả CASH khi ra

1. Đăng nhập operator.
2. Chọn `DEMO-IN-01`.
3. Upload ảnh/video xe vào.
4. Kiểm tra biển số, confidence và ảnh.
5. Xác nhận check-in.
6. Kiểm tra số xe trong bãi tăng một.
7. Chuyển sang `DEMO-OUT-01`.
8. Upload ảnh xe ra hoặc nhập biển số.
9. Xem ảnh vào/ra, thời gian và phí.
10. Xác nhận đã thu đủ CASH.
11. Hệ thống hoàn tất phiên và ghi barrier event; ACK thiết bị vật lý được kiểm tra riêng nếu adapter đã kết nối.
12. Kiểm tra số xe trong bãi giảm một.
13. Kiểm tra lượt ra và doanh thu tăng đúng số tiền.
14. Mở audit log và lịch sử giao dịch.

### Kịch bản B — AI confidence thấp

1. Upload media confidence thấp.
2. UI yêu cầu xác nhận.
3. Operator sửa biển số.
4. Check-in thành công.
5. Audit log lưu giá trị ban đầu, giá trị xác nhận và người thực hiện.

### Kịch bản C — Check-in trùng

1. Dùng lại biển số đang có phiên mở.
2. Hệ thống từ chối tạo phiên thứ hai.
3. Counter không tăng và barrier không được báo mở thêm.

### Kịch bản D — Manual fallback

1. Upload ảnh không nhận diện được hoặc kiểm tra nhánh real provider unavailable.
2. Operator nhập biển số thủ công.
3. Giao dịch được đánh dấu đúng nguồn manual và có audit.

### Kịch bản E — Xe vé tháng

1. Dùng xe có subscription còn hạn.
2. Check-in nhận đúng entitlement.
3. Check-out áp đúng chính sách đã seed.
4. Không tạo doanh thu CASH nếu chính sách cho miễn phí.

## 12. Lệnh kiểm tra trước nghiệm thu

### Backend

```powershell
cd backend
py -3 -m pytest tests
py -3 -m ruff check app scripts tests
py -3 -m ruff format --check app scripts tests
py -3 scripts/verify_model_bundle.py
py -3 scripts/system_gate.py --image <path-to-image> --video <path-to-mp4>
py -3 scripts/release_gate.py --dataset datasets/phase2-release.json
```

### Frontend

```powershell
cd frontend
npm test -- --run
npm run lint
npm run build
```

### Docker

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Sau khi stack healthy, chạy System Functional Gate và toàn bộ kịch bản A–E. Không chạy `docker compose down -v` trên môi trường cần giữ dữ liệu.

## 13. Definition of Done cho phạm vi FILE_UPLOAD

Hệ thống chỉ được coi là sẵn sàng trong phạm vi hiện tại khi đáp ứng toàn bộ điều kiện sau:

- [ ] Backend tests, lint và format PASS.
- [ ] Frontend tests, lint và build PASS; warning còn lại đã được đánh giá không ảnh hưởng vận hành.
- [ ] Docker Compose build và health check PASS trên máy sẽ trình diễn.
- [ ] Chuẩn bị/reset dữ liệu acceptance chạy lại được ít nhất hai lần mà không tạo dữ liệu trùng.
- [ ] Kịch bản A–E chạy thành công theo đúng thứ tự.
- [ ] CASH checkout tạo dữ liệu ledger và báo cáo khớp nhau.
- [ ] Double-click/retry không tạo payment hoặc checkout trùng.
- [ ] Counter tăng/giảm đúng sau check-in/check-out.
- [ ] Không có nút Station OUT bị khóa mà không có hướng dẫn hoặc đường xử lý.
- [ ] Input mode được ghi rõ là `FILE_UPLOAD`; `LIVE_CAMERA/RTSP` ghi `NOT_INTEGRATED`.
- [ ] Barrier event và trạng thái controller vật lý được báo cáo riêng theo evidence.
- [ ] System Functional Gate và ALPR Quality Gate được tách biệt.
- [ ] README/UAT khớp đúng command và UI hiện tại.
- [ ] Có checklist khởi động, reset và xử lý sự cố nhanh cho người trình diễn.
- [ ] Không còn lỗi Critical/High trong phạm vi FILE_UPLOAD.

## 14. Rủi ro và phương án giảm thiểu

| Rủi ro | Tác động | Giảm thiểu |
| --- | --- | --- |
| Model không warmup kịp | FILE_UPLOAD ALPR bị chờ hoặc unavailable | Warmup trước, chuẩn bị manual fallback và kiểm tra health |
| Dữ liệu cũ làm trùng biển số | Check-in acceptance thất bại | Reset namespace acceptance hoặc dùng biển số fixture cố định |
| Phí thay đổi giữa preview và checkout | Station trả `FEE_CHANGED` | Preview lại và giữ pricing/time ổn định trong ca nghiệm thu |
| Dashboard không khớp checkout | Mất độ tin cậy | Hoàn thành DEMO-03/04 và test E2E trước tổng duyệt |
| Docker hoặc port bị chiếm | Không khởi động stack | Checklist port/process, xác minh deployment trên đúng máy vận hành |
| Acceptance media không ổn định | Kết quả ALPR thay đổi | Dùng bộ media có checksum và tách khỏi quality dataset |
| Mạng Internet không ổn định | Tải dependency hoặc asset thất bại | Cài sẵn dependency/image; hệ thống không phụ thuộc dịch vụ Internet cho workflow hiện tại |

## 15. Những việc không nên làm trước nghiệm thu

- Không thêm tính năng lớn như đặt chỗ, voucher hoặc portal cư dân.
- Không tích hợp ngân hàng thật trước khi ledger CASH ổn định.
- Không dùng mock/synthetic benchmark để tuyên bố model đạt độ chính xác thương mại.
- Không trình diễn báo cáo doanh thu nếu checkout chưa ghi cùng một sổ dữ liệu.
- Không mô tả camera live là đã tích hợp khi hệ thống đang ở `FILE_UPLOAD` mode.
- Không suy diễn barrier business event thành ACK thiết bị nếu controller chưa xác nhận.
- Không dành thời gian tối ưu giao diện nhỏ trước các lỗi tiền, counter, retry và chuẩn bị lại môi trường acceptance.

## 16. Kết quả bàn giao của đợt cải thiện hệ thống

Đợt này cần bàn giao tối thiểu:

1. Code sửa CASH/ledger/report và Station OUT tối thiểu.
2. Test backend/frontend cho các lỗi đã sửa.
3. Chuẩn bị/reset dữ liệu acceptance idempotent.
4. Acceptance media có manifest/checksum.
5. System Functional Gate chạy lại được.
6. README và UAT đã cập nhật.
7. Biên bản deployment verification gồm kết quả command, môi trường và các giới hạn đã biết.

Khi các đầu ra trên hoàn thành, VisionPark được nghiệm thu như một hệ thống thật trong phạm vi `FILE_UPLOAD`. Tích hợp `LIVE_CAMERA/RTSP` và các thiết bị ngoại vi còn thiếu dùng kế hoạch riêng; ALPR quality tiếp tục theo trạng thái PASS/FAIL/HOLD độc lập.
