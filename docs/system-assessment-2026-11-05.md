# Đánh giá chức năng và khả năng triển khai VisionPark

Ngày kiểm tra: 05/11/2026 (Việt Nam). Nhánh `van-dev`, commit `8cbc7bf`.

## Kết luận

VisionPark đã có nền backend nghiệp vụ khá rộng, frontend quản trị và check-in hoạt động ở mức kiểm thử. Hệ thống **chưa đủ điều kiện triển khai vận hành thương mại**: thiếu UI xe ra, có lỗi xác nhận tiền và báo cáo doanh thu, chưa chứng minh chất lượng ALPR trên model hiện tại và chưa tích hợp barrier/camera trực tiếp đủ cho vận hành tại cổng.

Không quy đổi thành phần trăm hoàn thiện: repo chưa có danh sách tiêu chí được chốt với trọng số; số test qua không phải phần trăm sản phẩm sẵn sàng. Mốc hợp lý hiện tại là **MVP đang hoàn thiện để nghiệm thu/pilot có người giám sát**.

## 1. Tài liệu có Phase 5 chưa?

- Không tìm thấy kế hoạch/spec/nghiệm thu có tên **Phase 5**, **Phase V** hoặc **Giai đoạn 5** trong `docs`, `openspec`, `frontend/docs` và các README đã kiểm tra.
- Có [`M5-README.md`](../M5-README.md): patch báo cáo và thiết bị ngày 18/10/2026, có danh sách phần chưa hoàn chỉnh. Đây không phải bằng chứng đã hoàn tất Phase 5.
- Có code `backend/app/modules/m5`, migration M5 và UI `/admin/m5`.
- [`phan-cong-nhiem-vu-5-thanh-vien.md`](phan-cong-nhiem-vu-5-thanh-vien.md) phiên bản 2 ngày 02/11/2026 là kế hoạch bàn giao, ưu tiên **CASH**, loại online/VietQR/webhook khỏi đợt bàn giao. `M5` ở tài liệu này còn chỉ **thành viên 5**, không mặc nhiên là giai đoạn 5.
- README và `frontend/docs/OVERVIEW.md` vẫn mô tả nhiều phần đã có backend là ngoài phạm vi. Cần cập nhật bảng trạng thái chung theo code và kết quả nghiệm thu, tránh coi các tài liệu cũ là hiện trạng.

## 2. Ma trận chức năng

“Có backend” chỉ xác nhận có API/logic trong repo; không đồng nghĩa UI và thiết bị thật đã chạy trọn luồng.

| Nhóm | Bằng chứng triển khai | Phần còn thiếu / kết luận |
| --- | --- | --- |
| Đăng nhập, JWT, phân quyền, tài khoản | `modules/auth`, `modules/users`; UI login/users; test auth/RBAC | Có nền tảng. Cần tiếp tục kiểm tra quyền từng API mới, đặc biệt báo cáo M5 và các hành động override. |
| Nhiều tòa nhà, membership, cô lập dữ liệu | `database/tenant.py`, `modules/buildings`; test building isolation | Đã có nền backend đa tòa nhà; chưa đủ để tuyên bố có sản phẩm quản lý chuỗi bãi hoàn chỉnh. |
| ALPR ảnh/video | YOLO + PaddleOCR, crop/đọc biển, xác nhận và sửa tay, video MP4/ảnh | Có workflow. Chất lượng nhận diện hiện tại chưa được chứng minh bằng benchmark độc lập phù hợp model đang dùng. |
| Check-in, trùng biển, idempotency, audit | `modules/checkin`, Station, test tích hợp | Có cả API và UI. Station chỉ lọc làn `IN` tại `frontend/src/modules/station/api.ts:27`. |
| Check-out, tính phí, mất vé, miễn phí | `modules/checkout`; test checkout và 6 kịch bản cash workflow | Backend có; **không tìm thấy UI gọi API check-out** trong `frontend/src`. Các lỗi tiền ở mục 4 chặn bàn giao. |
| Giá theo phiên bản/snapshot, loại vé, hạng khách, quota | `modules/pricing`; `PricingSettings.tsx` | Có backend và UI cấu hình giá. Cần kiểm thử xuyên suốt đổi giá, vé tháng và xe ra thực tế. |
| Xe cư dân, subscriptions, guest invites, import CSV | `pricing/tickets_router.py` | Có API; chưa thấy trang quản lý/gia hạn vé tháng hoặc UI import xe. Có lựa chọn MONTHLY tại Station không có nghĩa đã có màn quản lý vé tháng. |
| Hóa đơn và thanh toán | `pricing/billing.py`, callback HMAC cho `VIETQR_MOCK` | Có sổ invoice/payment riêng, nhưng checkout CASH chưa nối sổ này. QR hiện là mock; không phải tích hợp ngân hàng thật. QR không nằm trong phạm vi handover CASH hiện tại. |
| Bộ đếm, sức chứa, đối soát | `checkin/counter_service.py`, `counter_reconciliation.py`, API `/availability` | Backend có; Settings UI chưa gọi `/settings/lot`; dashboard M5 chưa dùng được sức chứa này. |
| Barrier và mở khẩn cấp | `modules/barriers`, `operations/emergency_service.py` | Có nghiệp vụ/API/audit **mô phỏng**. `barrier_opened=True` được gán sau ghi DB, chưa phải xác nhận thiết bị đã mở. |
| Báo cáo M5 | Dashboard, daily stats, CSV/PDF, trang `/admin/m5` | Có UI/API; doanh thu/lượt ra có thể thiếu do không nối checkout CASH; peak luôn 0, capacity/available là null. |
| Thiết bị | Heartbeat, ONLINE/DEGRADED/OFFLINE, trang cảnh báo | Có API và polling UI mỗi 15 giây; chưa thấy agent thu heartbeat thiết bị thật, lưu alert và quy trình xử lý cảnh báo hoàn chỉnh. |
| Phát hiện khói/lửa | `alpr/fire_provider.py`, endpoint `/alpr/fire-detection`, unit tests | Có runtime/API, dù README cũ ghi deferred. Chưa thấy chuỗi incident lưu DB, gửi cảnh báo, xác nhận/xử lý và kiểm chứng hiện trường hoàn chỉnh. |
| Vận hành và khôi phục | Docker Compose, migration, health, backup script, runbook và CI | Có nền triển khai; Docker daemon không chạy ở lần kiểm tra này nên chưa xác nhận runtime Compose/backup-restore/thiết bị thật. |

## 3. Kết quả kiểm tra tại lần đánh giá này

- Backend: **284 test PASS, 3 skipped**, thời gian 437 giây. Ba ca skipped là race tests yêu cầu PostgreSQL; lần này chỉ chạy SQLite. Bộ test hiện hữu qua vẫn chưa bao phủ ba lỗi tiền tái hiện bên dưới.
- Frontend: **75/75 test**, 20 file; build **PASS**. Build cảnh báo bundle trên 500 kB và import động không tách được `errorLog`.
- Frontend lint: exit 0, có 13 cảnh báo React/hooks.
- Backend lint: **FAIL, 22 lỗi hiện hữu**, tập trung ở `scripts/benchmark_alpr_and_fire.py`.
- Model bundle: **PASS 5 checksum detector/OCR**. Checksum đúng chỉ xác nhận file khớp manifest.
- Phase 2 functional gate (`--functional-only --skip-tests`): **PASS**, dựa trên evidence đã lưu; không phải nghiệm thu checkout/M5 mới hoặc chạy lại camera hiện trường.
- Phase 2 quality gate (`--skip-tests`): **FAIL**, đọc benchmark đã lưu: validation exact match 25%, demo 0%, ngưỡng 80%.
- Đã chạy ba probe chẩn đoán qua FastAPI TestClient trên database SQLite được migration riêng, dùng fixtures của bộ cash workflow. Cả ba tái hiện hành vi lỗi trong mục 4; ALPR dùng test double, không chạm database vận hành.
- Không chạy stress test live vào database đang dùng. Không diễn giải `benchmark-stress-test.json` như kết quả đo bãi thật: file thiếu mode, commit, môi trường và dữ liệu đo; script hỗ trợ cả mock lẫn live.

## 4. Các vấn đề cần xử lý trước bàn giao

### P0 — Thu tiền thiếu vẫn hoàn tất và báo mở cổng

`backend/app/modules/checkout/service.py:661`, đặc biệt đoạn chuyển `tx.status = PAID` tại dòng 687, không kiểm tra `amount` có đủ so với `tx.fee`. Schema chỉ yêu cầu số tiền không âm.

Tái hiện: tạo phiên đỗ 90 phút với phí 15.000đ, chuyển `PAYMENT_PENDING`, gọi `POST /parking/sessions/{id}/payments` với `{ "payment_method": "CASH", "amount": 0 }`. Kết quả **HTTP 200, COMPLETED, barrier_opened=true**.

Đề nghị: xác thực tiền đã thu, phương thức và trạng thái trước chuyển PAID; miễn/giảm phải là nghiệp vụ có quyền/lý do riêng. Không lấy việc gửi tên phương thức làm bằng chứng thanh toán điện tử thành công.

### P0 — Tiền mặt và lượt ra không vào báo cáo M5

`checkout/service.py:342` và `_complete_session` chỉ ghi lifecycle/audit, trạng thái và counter; không tạo Invoice/Payment. `m5/service.py:aggregate_day` đếm lượt ra theo Invoice và doanh thu theo Payment PAID.

Tái hiện: checkout CASH 15.000đ thành công, phiên COMPLETED; database có **0 Invoice, 0 Payment**; rebuild thống kê cùng ngày cho ra **0 lượt ra, 0đ doanh thu**.

Đề nghị: thống nhất một sổ giao dịch thu tiền và nguồn dữ liệu báo cáo; trong một transaction ghi phiên, hóa đơn/biên nhận nội bộ, khoản thu, audit và sự kiện. Lượt ra phải có định nghĩa thống nhất kể cả vé tháng miễn phí. Thêm test xuyên suốt checkout → báo cáo → chốt ca, có hoàn/miễn/giảm.

### P1 — Phương thức tùy ý cũng được chấp nhận

`checkout/schemas.py:32` khai báo `payment_method` là chuỗi tùy ý; `checkout/service.py:342` coi mọi chuỗi không rỗng là thanh toán trực tiếp.

Tái hiện: phiên phí 15.000đ, gửi `payment_method="NOT_A_PAYMENT"`; kết quả **HTTP 200, COMPLETED**.

Đề nghị: enum theo phạm vi CASH hiện tại; khi bổ sung thanh toán điện tử, chỉ cho hoàn tất theo khoản thanh toán đã xác minh. Test phương thức lạ, thanh toán sai tiền, gọi lại và trạng thái không phù hợp.

### P1 — Chưa có UI xe ra và các màn hình handover cần thiết

Station hiện chỉ có làn IN và API check-in. Không thấy màn xe ra gọi `/parking/check-out`, ảnh vào/ra song song, thu tiền và phím tắt; chưa thấy trang subscriptions/import hoặc UI cấu hình `/settings/lot` như kế hoạch bàn giao yêu cầu.

Đề nghị: hoàn thiện UI vận hành theo task handover trước khi mở rộng thêm dashboard. UAT phải do nhân viên thao tác từ UI, không chỉ gọi API.

### P1 — Báo cáo AI kết luận đạt sai với số đo

[`backend/BENCHMARK_REPORT.md`](../backend/BENCHMARK_REPORT.md) đánh dấu ĐẠT cho recall xe **69,4% < 90%**, recall biển **55,6% < 85%**, yêu cầu xác nhận **100%** trong khi mục tiêu **<10%**, và fire latency **223,51 ms > 100 ms**.

`scripts/benchmark_alpr_and_fire.py:generate_markdown_report` chèn sẵn chữ ĐẠT; không tính verdict từ các ngưỡng. Benchmark ALPR ở script này tính có bbox/có chuỗi đọc được, chưa so biển dự đoán với nhãn đúng để chứng minh exact match. Fire dùng 30 frame nền tổng hợp, không đủ đánh giá dương tính/báo giả thực tế.

Evidence Phase 2 ngày 09/10 thuộc model detector khác model dual hiện có trong manifest. **Không coi 25%/0% là phép đo mới của model hiện tại**, cũng không coi báo cáo 21/10 là bằng chứng đã gỡ HOLD.

Đề nghị: verdict máy tính theo metric; benchmark model/hash hiện tại trên bộ nhãn độc lập từ bãi mục tiêu, tách xe máy/ô tô, biển 1/2 dòng, ngày/đêm/mưa. Báo cáo exact match, tỷ lệ sửa tay, nhận nhầm, p95 và kích thước tập. Không tự mở cổng dựa vào model chỉ vì readiness/checksum qua.

### P1 — Số liệu và tích hợp vận hành còn dang dở

- `m5/service.py` gán `occupancy_peak=0`; `m5/router.py:dashboard` trả capacity/available null dù backend đã có counter/settings.
- Daily rebuild cần chạy tay hoặc scheduler bên ngoài; chưa có bằng chứng scheduler được cài và có cảnh báo thất bại.
- Heartbeat/alert hiện là API và truy vấn; chưa chứng minh nhận trạng thái tự động từ thiết bị thật.
- Barrier chỉ ghi sự kiện mô phỏng. Cần adapter, timeout, xác nhận controller/cảm biến và phân biệt lệnh mở với xe đã thực sự qua cổng.

### P1 — Còn thiếu bằng chứng chống lỗi đồng thời

Checkout key được tìm trong `notes` bằng LIKE (`checkin/repository.py:210`), chưa có bản ghi idempotency riêng kèm fingerprint cho checkout; các lookup phiên không dùng khóa hàng trong luồng này. Các test replay tuần tự không đủ chứng minh chống hai trạm checkout đồng thời hoặc retry khác nội dung. Đây là rủi ro qua đọc code, **chưa tái hiện race trên PostgreSQL** ở lần kiểm tra này.

Ngoài ra, `counter_reconciliation.py:get_active_session_counts` chỉ đếm PARKED; cần test xe ở ENTERED/PAYMENT_PENDING/PAID vẫn còn vật lý trong bãi trước khi cho job tự điều chỉnh counter. Không coi việc có hàm `compensate_offline_session` là đã có vận hành offline hoàn chỉnh.

## 5. Nâng cấp để cạnh tranh

Đối chiếu nguồn chính thức và giới hạn khảo sát nằm trong [nghiên cứu thị trường](parking-market-research-2026-11-05.md). Trong mẫu này, ALPR, vé tháng, QR, quản lý nhiều bãi và báo cáo đã được các hãng công bố. Chưa có cơ sở nói VisionPark vượt các hệ thống khác chỉ vì có AI hoặc web UI.

Định vị đề xuất: **bãi hỗn hợp xe máy–ô tô cho chung cư/văn phòng vừa và nhỏ; vận hành liên tục, đối soát rõ và chuyển đổi từ thiết bị cũ thuận tiện**. Đây là giả thuyết cần pilot/phỏng vấn chủ bãi.

| Ưu tiên | Tính năng/nâng cấp | Lợi ích và điều kiện nghiệm thu |
| --- | --- | --- |
| P0 | Hoàn thiện CASH đầu-cuối, sổ tiền thống nhất, UI xe ra, vé tháng và cấu hình bãi | Thu đúng, không bỏ sót/thu trùng; đối chiếu 1 ca từ UI tới báo cáo; test lỗi đã tái hiện phải được chặn. |
| P0 | ALPR thực địa và camera/barrier thật | Đo trên dữ liệu bãi dự kiến lắp; thử timeout, cảm biến và người duyệt khi nhận diện không chắc. |
| P1 | Đối soát ca: tiền đầu ca, phải thu, tiền đếm, chênh lệch, ký bàn giao | Chủ bãi truy được thất thoát theo ca/nhân viên; ca chốt không bị sửa âm thầm; miễn/giảm/hoàn có chứng cứ. |
| P1 | Hoạt động trên LAN khi đứt Internet; đồng bộ lại có kiểm soát | Ngắt Internet vẫn vào/ra/thu CASH; không tạo trùng khi kết nối lại. Mất LAN, server và điện có kịch bản riêng. |
| P1 | Chống tráo xe và mở cổng sai | Đối chiếu ảnh vào/ra, biển/thẻ/loại xe; mọi mở tay có lý do, người duyệt và bằng chứng; không dùng nhận diện khuôn mặt làm mặc định. |
| P1 | Tận dụng camera/đầu đọc cũ, nhập vé tháng/xe đang trong bãi | Có danh sách thiết bị thực sự đã thử; import có xem trước, kiểm lỗi, đối soát và quay lui. Giảm công thay mới khi bán hàng. |
| P2 | QR động và đối soát thật; portal cư dân gia hạn vé | Chỉ làm sau handover CASH; callback lặp/chậm/sai tiền được xử lý; gia hạn đồng bộ quyền ra vào, có CASH dự phòng. |
| P2 | Điều hành nhiều bãi và cảnh báo chủ động | Dashboard từ sổ thật, kiểm thử cách ly dữ liệu; alert có lưu, xác nhận và lịch sử xử lý thay vì chỉ polling. |
| P3 | Voucher, đặt chỗ, dự báo cao điểm, dẫn đường chỗ trống | Làm khi có nhu cầu khách hàng và dữ liệu occupancy đáng tin; chưa ưu tiên trước luồng tiền và cổng. |

Không chọn AI báo cháy làm điểm bán đầu tiên khi luồng incident, chất lượng mô hình và tích hợp hiện trường chưa hoàn chỉnh.

## 6. Nếu đặt tên một đợt tiếp theo là Phase 5

Đây là **đề xuất**, không phải Phase 5 đã có hoặc đã được duyệt trong repo.

1. **Nghiệm thu chức năng:** sửa ba lỗi tiền; hoàn thiện xe ra UI, quản lý/gia hạn vé tháng, import, cấu hình sức chứa; cập nhật docs trạng thái.
2. **Nghiệm thu vận hành:** nối thiết bị thật, cảnh báo mất kết nối, chốt ca; test retry/đồng thời PostgreSQL và thử backup/restore trên môi trường riêng.
3. **Nghiệm thu AI:** chạy benchmark model hiện tại với nhãn đúng và tập giữ lại; gỡ HOLD bằng kết quả có provenance.
4. **Pilot có giám sát:** đo thời gian phục vụ p50/p95, tỷ lệ sửa biển, chênh lệch tiền, số lần xử lý tay, giao dịch mất/trùng và phút gián đoạn; so với baseline tại cùng bãi.
5. **Sau pilot:** ưu tiên offline hoàn chỉnh, tương thích hệ thống cũ rồi mới QR/cư dân và đa bãi theo nhu cầu.

Không cam kết thời gian phục vụ 3 giây, uptime, ROI hoặc độ chính xác thương mại trước khi đo trên phần cứng và quy trình khách hàng.
