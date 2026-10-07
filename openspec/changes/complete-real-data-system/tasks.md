## 1. P0 — Kiểm kê và bảo vệ dữ liệu trước thay đổi

- [x] 1.1 Ghi baseline container/mount/volume/project name, database/schema head, model manifest và các service đang chạy; không xuất credentials vào báo cáo.
- [x] 1.2 Kiểm kê ID/count và liên kết tài khoản/làn/detection/giao dịch/audit cùng checksum ảnh; phân loại provenance nếu có bằng chứng, không tự xóa bản ghi cũ hoặc kết luận unknown là mock.
- [x] 1.3 Viết script backup DB + media nhất quán có manifest trong cửa sổ tạm dừng ghi và lưu ngoài volume ứng dụng; script không xóa hoặc ghi đè nguồn.
- [x] 1.4 Viết script restore vào project/database/volume riêng, kiểm tra target không phải DB/volume đang vận hành và kiểm chứng ID/count/checksum/reference ảnh.
- [x] 1.5 Cố định cách Compose tham chiếu đúng volume đang có, ngăn đổi project/storage path tạo DB rỗng mà không phát hiện.
- [x] 1.6 Kiểm tra seed; mặc định AUTO_SEED=false, bootstrap admin cài mới idempotent và mật khẩu được cung cấp, không tạo giao dịch/làn/operator giả hay reset dữ liệu đã có.
- [x] 1.7 Hoàn thành gate P0: backup restore đọc được dữ liệu/ảnh và baseline dữ liệu đang vận hành còn nguyên; chưa sửa schema/deployment trước gate này.

## 2. P1 — Loại mock khỏi ứng dụng và mặc định chạy model thật

- [x] 2.1 Kiểm kê mọi caller của FakeALPRRuntime/ai_runtime/fake repositories/mock API/fixtures/ONNX placeholder và phân biệt code ứng dụng với test.
- [x] 2.2 Xóa provider fake và ONNX placeholder khỏi application, chỉ cho phép real provider; giá trị mock/unknown báo lỗi cấu hình rõ ràng.
- [x] 2.3 Xóa endpoint check-in cũ/repository giả sau khi xác nhận router canonical và cập nhật import/caller.
- [x] 2.4 Xóa frontend fixture fallback, dev mock server và biến/header/scenario mock khỏi runtime/build/env mẫu.
- [x] 2.5 Chuyển test doubles cần thiết vào thư mục tests, sửa tests không import fake ứng dụng và kiểm tra image phát hành không đóng gói test doubles.
- [x] 2.6 Đồng bộ Compose/Dockerfile/env mẫu để build YOLO/OCR và mount model thật mặc định, warmup/readiness rõ ràng, checksum/version giữ đúng model đã chọn.
- [x] 2.7 Test model thiếu/hỏng/OCR lỗi trả readiness false và ALPR 503, không trả biển số giả; manual check-in vẫn ghi đúng nguồn thật.
- [x] 2.8 Hoàn thành gate P1: API/frontend không có đường trả dữ liệu mock, real model readiness pass và toàn bộ dữ liệu cũ giữ nguyên.

## 3. P2 — Hoàn thiện lưu detection, ảnh và luồng Station

- [x] 3.1 Đối chiếu schema hiện có với response thật; thiết kế migration additive chỉ cho metadata còn thiếu và chạy trên DB restore trước.
- [x] 3.2 Lưu đủ OCR gốc/chuẩn hóa, confidence thành phần, quality flags, model/latency, actor và context làn cho final detection.
- [x] 3.3 Hoàn thiện ghi ảnh nguyên tử, key riêng, xử lý lỗi ảnh/DB và công cụ kiểm tra orphan/missing file không tự xóa.
- [x] 3.4 Bổ sung nút Lưu kết quả thật trên ALPR Test với chọn làn hợp lệ, quyền và chống lưu trùng khi retry; chỉ lưu detection, không tạo check-in.
- [x] 3.5 Kiểm tra final capture → confirm → transaction/audit nguyên tử, duplicate và idempotency dưới retry/race; UI đọc bản ghi vừa lưu qua API.
- [x] 3.6 Hoàn thiện reset/cancel candidate khi đổi xe/làn/video, chặn response cũ và giới hạn inference request; không lưu mọi frame preview.
- [x] 3.7 Hiển thị source/model/quality/confidence và nguồn nhập thủ công đúng thực tế; bản ghi cũ thiếu provenance hiển thị unknown.
- [x] 3.8 Chuẩn hóa video_source và trạng thái UI: MP4 local dùng được, RTSP chưa hỗ trợ; không báo connected giả.
- [x] 3.9 Hoàn thành gate P2: ảnh thật → detection → sửa/xác nhận → một giao dịch → lịch sử/audit, reload còn dữ liệu; lỗi ghi ảnh không trả thành công giả.
- [x] 3.10 Thêm bộ chọn Ảnh/Video trên Station, component chọn/xem trước JPEG/PNG và nút Nhận diện; dùng chung API/provider/confirmation với video.
- [x] 3.11 Hoàn thiện lifecycle đổi mode/file: dừng sampling, reset candidate, bỏ response cũ, revoke object URL và khóa đổi nguồn khi confirm đang commit.
- [x] 3.12 Kiểm tra bytes/type/size ảnh và bbox scale/orientation; lưu đúng ảnh upload hoặc frame cuối đã nhận diện.
- [x] 3.13 Bổ sung input_kind IMAGE_UPLOAD/VIDEO_FRAME và video_time_ms khi có bằng migration additive; không gộp với nguồn AI/sửa tay/manual, bản ghi cũ giữ unknown.
- [x] 3.14 Nghiệm thu hai chế độ Station cùng ghi nhận check-in thật; ảnh lỗi/no-plate không tự tạo giao dịch, video không ghi mỗi frame và đổi mode không dùng kết quả cũ.

## 4. P3 — Lịch sử, bộ lọc, audit và dashboard

- [x] 4.1 Bổ sung API phân trang/filter/sort ổn định, envelope items/total và index phù hợp cho detections.
- [x] 4.2 Đồng bộ API parking history và audit pagination; thêm actor_id/resource_id, timezone và metadata tên/hướng làn, actor theo quyền.
- [x] 4.3 Chuyển DetectionHistory/ParkingHistory khỏi giới hạn fetch 200 rồi lọc client; kiểm tra chuyển trang, tìm kiếm và empty/error/loading.
- [x] 4.4 Nối audit thật vào chi tiết detection/giao dịch/người dùng bằng filter server, không lấy 100 audit rồi lọc local.
- [x] 4.5 Đồng bộ dashboard với số tổng database và cơ chế refresh/poll giới hạn; không dùng số đếm từ danh sách giới hạn làm tổng.
- [x] 4.6 Hoàn thành gate P3 trên DB test riêng >200 bản ghi: tìm được bản ghi ngoài trang đầu, totals đúng và đổi tên làn không làm sai context lịch sử đã lưu.
- [x] 4.7 Thêm hiển thị/bộ lọc loại đầu vào Ảnh/Video phía API và lịch sử; phân trang/tổng số đúng theo bộ lọc, dữ liệu cũ unknown không bị gán loại tùy ý.

## 5. P4 — Hồ sơ, mật khẩu, thu hồi phiên và quyền

- [x] 5.1 Xây API sửa display_name/email cá nhân, validate trùng dữ liệu và audit không chứa thông tin nhạy cảm.
- [x] 5.2 Xây API đổi mật khẩu với current password, hash mới, thu hồi token cũ và audit; giữ admin reset-password hoạt động.
- [x] 5.3 Bổ sung token/session version trong DB và kiểm tra ở mọi API bảo vệ; endpoint Force Logout thu hồi toàn bộ phiên tài khoản theo quyền.
- [x] 5.4 Nối Profile/Force Logout với backend, đồng bộ auth state và xử lý token bị thu hồi/khóa tài khoản; bỏ nút chờ backend tương ứng.
- [x] 5.5 Hiển thị đủ ma trận ADMIN/OPERATOR/ACCOUNTANT/TECHNICIAN theo policy hiện có, đồng bộ guard/API và không tự mở quyền nghiệp vụ mới.
- [x] 5.6 Hoàn thành gate P4: token cũ bị từ chối sau revoke/đổi mật khẩu, user không sửa người khác, role chỉ đọc không ghi được và audit không lộ password/token.

## 6. P5 — Settings, notifications và Error Center bền vững

- [x] 6.1 Thêm user preferences schema/API và migration additive cho theme/ngôn ngữ; localStorage chỉ cache, display_name cập nhật hồ sơ.
- [x] 6.2 Áp dụng light/dark và vi/en trên các màn hình hiện có; khôi phục preference sau login/reload/xóa localStorage.
- [x] 6.3 Thêm notification schema/API list/unread/read/read-all, receiver authorization và deduplicate; tạo từ lỗi/sự kiện nghiệp vụ thật đã chọn.
- [x] 6.4 Nối NotificationsPage với API và polling/backoff, giữ read state sau reload; không sinh notification cho mỗi preview frame.
- [x] 6.5 Thêm error_event schema/API đọc theo quyền, client-error ingest có sanitize/rate-size limit và correlation ID, chọn sự kiện backend cần lưu.
- [x] 6.6 Nối Error Center với lỗi DB thật, chống vòng lặp báo lỗi, bổ sung theo dõi dung lượng; không tự retention-delete dữ liệu.
- [x] 6.7 Hoàn thành gate P5: preference áp dụng và lưu thật, thông báo/lỗi còn sau restart; không đọc chéo notification riêng và không lưu credentials.

## 7. P6 — Nghiệm thu dữ liệu thật và bảo toàn Docker

- [x] 7.1 Chuẩn bị bộ ảnh/video xe thật có quyền sử dụng và ground truth; chia theo xe/video, ghi provenance, không dùng synthetic/mock thay nghiệm thu thực tế.
- [x] 7.2 Chạy detector/OCR/full pipeline benchmark thật: exact match, character accuracy, no-result, false-positive, cold/warm p50/p95 và phiên bản/phần cứng.
- [x] 7.3 Đo time-to-stable/candidate flips/provider errors trên video; đối chiếu mục tiêu warm p95 Phase 2 và ghi giới hạn phần cứng nếu chưa đạt.
- [x] 7.4 Chạy E2E real trên môi trường riêng: nhận diện được, no-plate, chất lượng thấp, sửa tay, manual, duplicate/retry, ảnh/history/audit và RBAC.
- [x] 7.5 Chạy persistence matrix trên môi trường restore riêng: restart, down/up không xóa volume, rebuild và force-recreate; so ID/count/nội dung/checksum ảnh trước-sau.
- [x] 7.6 Chạy upgrade migration và seed idempotency trên DB đã có dữ liệu; chứng minh không reset mật khẩu, không mất bản ghi và không tự đổi volume.
- [x] 7.7 Chạy regression backend pytest/ruff, frontend test/lint/build; tập trung test persistence/auth/race/contract, không thêm test chỉ lặp lại giao diện.
- [ ] 7.8 Hoàn thành gate P6 bằng report và evidence thật; thiếu dữ liệu xe có nhãn thì giữ gate chất lượng mở, không đánh dấu hoàn thành thay bằng readiness.
- [x] 7.9 Chạy real E2E riêng cho JPEG/PNG và MP4, chuyển mode khi request pending, xác nhận/retry, lưu ảnh/metadata input_kind và kiểm tra dữ liệu cả hai chế độ còn sau Docker lifecycle.

## 8. P7 — Tài liệu và bàn giao

- [x] 8.1 Cập nhật README/backend README/Help/API/env/runbook hiện hành về real-only, model provisioning, lưu detection và nguồn manual; bỏ hướng dẫn rollback sang mock.
- [x] 8.2 Viết runbook Docker giữ dữ liệu, backup/restore, bootstrap cài mới, migration/rollback tương thích và cảnh báo rõ thao tác xóa volume sẽ xóa dữ liệu.
- [x] 8.3 Đối chiếu gate liên quan ở phase-2-alpr-checkin, cập nhật bằng evidence tương ứng; giữ tài liệu mock cũ là lịch sử, không dùng làm hướng dẫn hiện hành.
- [x] 8.4 Bàn giao danh sách chức năng đã nghiệm thu, gate còn mở và baseline/backup của dữ liệu đang vận hành; chỉ triển khai thay đổi ứng dụng sau khi người dùng đã review kế hoạch này.

Báo cáo: `docs/real-data-completion-report-2026-10-07.md`. Gate 7.8 còn mở:
benchmark hai xe/11 frame có nhãn, 8/10 positive exact match, warm p95 3,03 giây CPU;
chưa đủ nghiệm thu chất lượng tổng quát.

