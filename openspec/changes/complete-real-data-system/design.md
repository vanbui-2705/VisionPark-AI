## Context

Xem proposal.md về mục tiêu. Ngày 2026-10-07 Docker hiện dùng real YOLO/PaddleOCR nhưng Compose base còn mặc định ALPR_PROVIDER=mock, AUTO_SEED=true và mẫu tài khoản demo. Database dùng postgres_data, ảnh dùng media_data trong project visionpark. Phần lớn API đọc thật; notifications/error log chỉ lưu bộ nhớ, settings chỉ lưu localStorage. Phase 2 còn thiếu dữ liệu xe thật có nhãn để đóng gate chất lượng.

## Goals / Non-Goals

**Goals:** cập nhật tuần tự, bảo toàn dữ liệu trước tiên; duy trì modular monolith, REST, PostgreSQL và storage adapter; lỗi model không ảnh hưởng nhập xe thủ công.

**Non-Goals:** không tự train/fine-tune; không biến video_source thành camera integration trong đợt này; không thiết kế lại bãi xe hoặc thêm nghiệp vụ xe ra/thanh toán. Không tự xóa bản ghi bị nghi là mock hoặc thay DB đang chạy bằng DB test.

## Decisions

### D1. Bảo toàn volume trước mọi sửa Docker

Kiểm kê mount thực tế bằng Docker inspect, tên project/volume, DATABASE_URL, schema head, ID/count các bảng và checksum ảnh. Tiếp tục dùng chính volume hiện có; chỉ dùng explicit/external volume nếu đã ánh xạ đúng tên thực tế. Không đổi project name, không down -v, không prune volume, không reset schema. Named volume hiện tại phù hợp máy đơn; chuyển sang bind mount không giải quyết backup và có nguy cơ đổi nơi lưu dữ liệu.

Backup database bằng dump và chụp media trong cửa sổ tạm dừng ghi nghiệp vụ để có snapshot nhất quán; lưu manifest schema/model/time và checksum. Restore thử vào project/database/volume riêng. Backup nằm ngoài volume ứng dụng. Không tuyên bố volume chống được xóa thủ công hoặc mất ổ đĩa.

### D2. Một cấu hình real-only

Đưa build dependencies/model manifest/mount/warmup vào cấu hình mặc định dễ chạy; giữ manifest và checksum để không âm thầm đổi model. Xóa FakeALPRRuntime, ai_runtime fake global, frontend fixtures/mock server và legacy fake check-in/ONNX placeholder sau khi kiểm tra caller. Test doubles chuyển vào tests; không đóng gói đường dẫn test vào image ứng dụng. Không giữ switch mock trong env/UI/CLI vận hành. Unknown/mocked provider báo cấu hình sai; model thiếu báo readiness false và ALPR 503. Không tự tải model mới để thay weights đã chọn.

### D3. Persistence có ranh giới

Station có bộ chọn Ảnh/Video trên cùng màn hình. Chế độ Ảnh chọn một JPEG/PNG, xem trước và bấm Nhận diện; không sampling hoặc consensus nhiều frame. Chế độ Video giữ MP4 local, play/pause, capture thủ công và sampling/consensus hiện có. Cả hai chuyển dữ liệu ảnh về cùng API ALPR thật và dùng chung ConfirmationPanel/check-in service; không dựng hai luồng xác nhận riêng.

Đổi chế độ/file/làn phải dừng sampling, hủy hoặc bỏ response đang chờ, reset candidate và thu hồi object URL cũ; khóa đổi nguồn khi confirmation đang commit. Backend validate bytes/type/size, không chỉ dựa extension. Ảnh được xử lý theo cùng tọa độ hiển thị để bbox đúng khi scale và có EXIF orientation.

Lưu input_kind=IMAGE_UPLOAD hoặc VIDEO_FRAME độc lập với nguồn quyết định AI_ACCEPTED/OPERATOR_CORRECTED/MANUAL_ENTRY. Với frame video lưu thêm video_time_ms nếu có; bản ghi cũ thiếu loại đầu vào giữ unknown. Lịch sử hiển thị và lọc được hai loại đầu vào. Ảnh upload được chọn để final lưu đúng ảnh đã nhận diện; video lưu đúng frame đã chọn, không tự lưu file MP4.

Preview không lưu từng frame. Final capture và nút Lưu kết quả trên trang ALPR Test tạo detection/ảnh, không tự check-in. Confirmation ghi detection/giao dịch/audit trong cùng DB transaction với idempotency. Bổ sung metadata còn thiếu bằng migration additive sau kiểm kê schema: OCR gốc/chuẩn hóa, confidence thành phần, quality flags, version/latency, actor và context. Giữ snapshot tên/hướng làn tại thời điểm nghiệp vụ khi cần lịch sử không đổi theo việc sửa làn.

Ảnh vẫn lưu volume qua adapter, DB lưu object key. Dùng key không trùng, ghi file nguyên tử và cơ chế xử lý lỗi DB/file; không trả thành công khi ảnh chưa lưu. Báo orphan/missing file bằng công cụ kiểm tra; chưa tự dọn/xóa. Video gốc không lưu mặc định; chỉ lưu ảnh cuối, không toàn MP4 hay mọi frame. Không suy đoán provenance các bản ghi cũ: bản ghi chưa xác định nguồn giữ nguyên và hiển thị unknown.

### D4. Hoàn thiện API trước nối màn hình

API lịch sử trả items/total/limit/offset và sort ổn định theo timestamp cùng ID, lọc ngày theo timezone quy định, tìm biển số chuẩn hóa, làn/hướng/trạng thái. Chuyển frontend khỏi fetch 200 rồi lọc tại client; giữ tương thích hoặc cập nhật đồng bộ caller nếu envelope thay đổi. Audit hỗ trợ actor_id và entity/resource_id. Dashboard dùng endpoint tổng hợp và refresh/poll có giới hạn; chưa thêm WebSocket.

### D5. Hồ sơ, phiên và quyền

API cập nhật hồ sơ riêng theo current user, đổi mật khẩu kiểm tra mật khẩu hiện tại. Thêm session/token version hoặc session registry ở DB để vô hiệu JWT hiện có; thay mật khẩu, khóa tài khoản hoặc Force Logout thu hồi token, logout server thu hồi phiên tương ứng. Chọn token-version cho Force Logout toàn bộ phiên tài khoản; không cần refresh-token subsystem trong phạm vi này. Ma trận quyền cố định hiện có là nguồn chuẩn của bốn vai trò, thêm coverage backend/frontend; chưa mở editor quyền động. Không tự cấp ACCOUNTANT/TECHNICIAN quyền mới ngoài policy hiện có.

### D6. Preferences, notifications và lỗi

Preferences lưu theo user ở DB, hỗ trợ light/dark và vi/en cho các màn hình hiện có; localStorage chỉ cache tạm. Notification tạo từ event nghiệp vụ thật, lưu receiver/read_at và deduplicate theo event/receiver trong cùng transaction hoặc thao tác có retry an toàn. Polling REST có backoff, không thêm broker; không thông báo mỗi frame preview hoặc spam mọi check-in thành công.

Error Center đọc error_event có correlation ID, timestamp, category, severity, actor và thông điệp đã sanitize. Endpoint client-error có RBAC/rate limit/size limit, không lưu request body/credentials/ảnh. Structured server logs vẫn là nguồn chẩn đoán đầy đủ; chỉ lưu sự kiện được chọn vào DB, không đẩy mọi log vào database. Mặc định chưa tự retention-delete; có cảnh báo dung lượng.

### D7. Nghiệm thu thật độc lập với unit test

Unit test được dùng test doubles trong tests với DB tách biệt, để kiểm tra retry/lỗi/race. E2E/release gate dùng YOLO/PaddleOCR thật và dữ liệu xe thật. Chạy restart/rebuild/down-up trên môi trường restore riêng, không dùng dữ liệu đang vận hành làm test cleanup. Báo exact match/character accuracy/no-result/false-positive/cold-warm p50-p95/time-to-stable. Mục tiêu warm p95 dưới 1 giây kế thừa Phase 2; nếu phần cứng không đạt phải ghi nhận giới hạn, không tự đánh dấu pass. Ngưỡng accuracy cần thống nhất bằng baseline thật trước quyết định rollout tự động; Operator tiếp tục xác nhận.

## Risks / Trade-offs

- [Thiếu bộ video/ảnh xe thật có nhãn] → vẫn hoàn thiện được persistence/UI; gate accuracy và real vehicle E2E giữ mở tới khi có bộ dữ liệu phù hợp.
- [Named volume không phải backup] → dump + media backup ngoài volume, restore thử; lifecycle bảo toàn áp dụng cho thao tác không xóa volume.
- [Ảnh và DB không cùng transaction] → snapshot tạm dừng ghi, key riêng và ghi nguyên tử, kiểm tra file/reference và xử lý lỗi rõ ràng.
- [Migrations hoặc seed ghi đè dữ liệu] → migration additive, kiểm kê trước/sau, bootstrap idempotent chỉ khi cài mới; AUTO_SEED mặc định false.
- [Thông báo/lỗi tăng dung lượng] → không lưu preview, deduplicate/rate-limit và theo dõi dung lượng; retention là chính sách review sau, không tự xóa.
- [Thay API phân trang/token-version làm client cũ lỗi] → cập nhật backend/frontend đồng bộ, kiểm thử contract và buộc đăng nhập lại có thông báo khi cần.

## Migration Plan

1. Kiểm kê dữ liệu/volume hiện có; backup nhất quán và restore kiểm chứng trên môi trường riêng trước sửa deployment hoặc schema.
2. Thay cấu hình real-only; xóa mock khỏi application và chuyển test doubles sang tests. Bootstrap admin là thao tác cài mới có mật khẩu cung cấp, không sinh giao dịch/demo accounts/lanes mặc định.
3. Chạy migration additive trên bản restore, so ID/count/checksum; triển khai lên DB hiện có khi gate pass.
4. Hoàn thiện persistence, API và UI theo thứ tự tasks.md; không thực hiện destructive cleanup dữ liệu cũ.
5. Chạy real E2E, benchmark và lifecycle persistence gate trên môi trường riêng; cập nhật docs và gate Phase 2 tương ứng bằng evidence.
6. Rollback bằng image/config phiên bản real trước đó tương thích schema mới; không downgrade xóa cột/dữ liệu và không rollback sang mock. Restore backup chỉ khi cần phục hồi sự cố, phải tính các bản ghi mới phát sinh để không làm mất chúng.

## Open Questions

- Nguồn bộ ảnh/video xe thật có nhãn phục vụ benchmark: tài sản người dùng cung cấp hoặc bộ dữ liệu có quyền sử dụng phù hợp; chưa có sẵn trong repo.
- Vị trí backup ngoài volume và lịch backup trên máy triển khai: lựa chọn đường dẫn/ổ đĩa không đổi hợp đồng bảo toàn và restore.

Các lựa chọn phạm vi vi/en, lưu ảnh cuối thay vì toàn video, polling và giữ quyền cố định là đề xuất cụ thể để người dùng review trước triển khai.
