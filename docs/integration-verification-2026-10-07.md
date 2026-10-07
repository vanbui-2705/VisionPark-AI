# Integration verification — 07/10/2026

Các lệch đã được sửa trong code, contract, tài liệu và Compose local.

| Luồng | Kết quả hiện tại |
|---|---|
| Station | Shared token/client; backend quyết định provider, không còn check-in giả trong frontend |
| Preview/final | Preview không ghi DB; final capture UUID/fingerprint chống bản ghi trùng khi retry |
| Confirm | Canonical confirmed_plate + check_in=true; detection/PARKED/audit commit atomically |
| Retry/duplicate | Cùng key/payload trả cùng transaction; payload khác hoặc biển đang PARKED trả 409 |
| Manual | Gọi parking API trực tiếp, vẫn hoạt động khi ALPR 503 |
| Lane | Map is_active; Operator đọc, Admin thêm/sửa/deactivate |
| Detection | Detail/filter đúng API; ảnh và bbox pixel hiển thị đúng tỉ lệ |
| Users/roles | API Admin thật; bốn role được giữ nguyên; đổi mật khẩu/active qua PATCH |
| Readiness | UI map status/version của backend; mock trả đúng nhãn provider |
| Dashboard | Số tổng parking từ DB, không lấy độ dài năm bản ghi làm tổng |
| Docker | Bản mới đang chạy, migration head 20261007_0008; giữ volume dữ liệu |
| OpenSpec | Checklist sửa theo evidence; real benchmark/video gate còn mở |

Kiểm chứng cuối:

- Backend: 234 pass, 3 skip trên SQLite và disposable PostgreSQL; 237 test collected.
- Ruff check và format: pass (119 files).
- Frontend: 40 pass / 13 files; production build pass; lint exit 0 còn 11 warning React có sẵn.
- Compose: db/backend/frontend healthy; frontend http://localhost:5174, backend port 8002.
- OpenSpec validate all: 3 pass, 0 fail; git diff --check pass.
- [Browser smoke](phase-2-evidence/browser-smoke.json): MP4 tổng hợp + backend mock,
  PostgreSQL thật; preview, corrected check-in, idempotent retry, duplicate, manual
  fallback sau injected 503, users/roles/RBAC, detection detail/media; 0 page errors.
- Snapshot backup database trước migration nằm ở backend/var/backups (ignored).
- QA lane và bản ghi/ảnh của smoke đã dọn; không lưu token/mật khẩu trong evidence.

Local YOLO + PaddleOCR đã load và readiness=True với model version
ultralytics-8.4.165-yolo26n-plate-v1. Đây là kiểm tra host có model/cache, không phải
Docker đang bật real provider. Docker hiện chạy mock, OCR disabled.

Chưa có video biển số thật/dataset ảnh gắn nhãn để chứng minh OCR inference, accuracy,
CPU cold/warm p95 và toàn bộ release evidence. Benchmark real giờ từ chối fixture
thiếu image, thay vì dùng ảnh tổng hợp để báo cáo như kết quả thật. Phase 2 chưa archive.
Lịch sử parking hiện tải và lọc trong 200 giao dịch gần nhất; UI đã ghi rõ giới hạn.
Camera/RTSP, check-out, tính phí/payment/barrier vẫn ngoài phạm vi Phase 2.


## Sau đó: bật nhận diện thật cho phiên local

Đã chuyển Docker đang chạy sang `ALPR_PROVIDER=real`, `ALPR_OCR_ENABLED=true`,
cài thư viện AI CPU, mount weights/cache read-only và warmup trước khi serve.
Root `.env` giữ Compose real override cho lần restart tiếp theo. Mặc định mock
trong clean checkout/CI được giữ nguyên.

API real readiness, YOLO inference trên ảnh trống, OCR trên rendered crop và capture
video qua Station đã pass; xem `phase-2-evidence/real-provider-smoke.json` và
`real-video-smoke.json`. Kiểm tra này không chứng minh accuracy trên video xe thật.
