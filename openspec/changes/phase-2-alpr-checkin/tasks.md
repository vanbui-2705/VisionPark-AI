## 0. Agent execution rules

- [x] 0.1 Đọc `docs/phase-2-ocr-checkin-plan.md` trước khi sửa code.
- [x] 0.2 Chỉ làm một module active tại một thời điểm.
- [x] 0.3 Viết/chỉnh test cùng module rồi chạy test module đó.
- [x] 0.4 Chỉ chuyển module kế tiếp khi exit gate của module hiện tại pass.
- [x] 0.5 Sau mỗi milestone chạy backend/frontend regression.
- [x] 0.6 Không dùng ONNX provider placeholder cho real demo.
- [x] 0.7 Không train model mới trong luồng chính Phase 2.

## 1. M0 — Contract, asset và route gate

- [x] 1.1 Chạy Phase 1 clean-install/regression gate và ghi carry-over Critical/High.
- [x] 1.2 Chốt `/station/scan` là route Station canonical; loại bỏ duplicate flow hoặc chuyển component về một flow duy nhất.
- [x] 1.3 Chốt input demo là MP4 local, một lane `IN`, một xe/lane tại một thời điểm.
- [x] 1.4 Chốt ALPR response có raw/normalized plate, bbox, detector/OCR/combined confidence, quality flags, model version và latency.
- [x] 1.5 Chốt preview không persist và confirm mới tạo transaction.
- [x] 1.6 Sửa frontend persist final capture rồi gọi endpoint canonical `/api/v1/alpr/detections/{id}/confirm` với `check_in=true` và `Idempotency-Key`; manual gọi parking check-in.
- [x] 1.7 Chốt manifest/checksum/model distribution ngoài Git.
- [x] 1.8 Tạo fixture lane `IN`, user Operator và video/ảnh smoke không nhạy cảm.

**Exit gate M0:** mock flow và contract fixture chạy được; route canonical không còn mơ hồ.

## 2. M1 — Real ALPR provider, làm tuần tự theo submodule

### 2.1 M1.1 — Image input và decode

- [x] 2.1.1 Validate JPEG/PNG content type và kích thước file.
- [x] 2.1.2 Decode bytes thành OpenCV image.
- [x] 2.1.3 Trả typed error cho bytes rỗng, file hỏng và file quá lớn.
- [x] 2.1.4 Viết unit test ảnh hợp lệ, ảnh hỏng, ảnh rỗng và vượt kích thước.

**Exit gate:** decode test pass; lỗi decode không gọi detector/OCR.

### 2.2 M1.2 — YOLO detector adapter

- [x] 2.2.1 Load `backend/app/alpr/weights/best.pt` một lần.
- [x] 2.2.2 Validate manifest, path, checksum và `plate_class`.
- [x] 2.2.3 Trả bbox biển số và `detector_confidence`.
- [x] 2.2.4 Clamp bbox vào kích thước ảnh.
- [x] 2.2.5 Xử lý no-plate không exception.
- [x] 2.2.6 Đo detector latency.
- [x] 2.2.7 Phân biệt model missing, checksum mismatch, dependency error và inference error.
- [x] 2.2.8 Viết unit/contract test một biển, nhiều biển, no-plate, bbox biên, confidence thấp và model lỗi.

**Exit gate:** detector chạy trên fixture thật, bbox hợp lệ và readiness đúng.

### 2.3 M1.3 — Crop và quality gate

- [x] 2.3.1 Mở rộng bbox 8–12% rồi clamp lại.
- [x] 2.3.2 Kiểm tra crop min width/height và aspect ratio.
- [x] 2.3.3 Đo blur, brightness và contrast.
- [x] 2.3.4 Trả quality flags `bbox_too_small`, `crop_blurry`, `crop_dark`, `crop_low_contrast`, `crop_invalid_ratio`.
- [x] 2.3.5 Bỏ qua OCR khi crop không đạt gate.
- [x] 2.3.6 Viết unit test crop bình thường, sát biên, quá nhỏ, mờ, tối và sai tỷ lệ.

**Exit gate:** crop rõ không mất ký tự; crop xấu bị chặn deterministic.

### 2.4 M1.4 — PaddleOCR recognition adapter

- [x] 2.4.1 Cài extra OCR và pin version tương thích môi trường demo.
- [x] 2.4.2 Dùng `TextRecognition` với `latin_PP-OCRv5_mobile_rec`.
- [x] 2.4.3 Không chạy text detection trên crop biển số.
- [x] 2.4.4 Warm/load OCR một lần, không load theo request.
- [x] 2.4.5 Parse raw text và OCR score thành `raw_plate`, `ocr_confidence`.
- [x] 2.4.6 Trả typed error cho OCR model/dependency/inference/timeout.
- [x] 2.4.7 Viết test adapter bằng mock OCR để CI không cần tải model.
- [x] 2.4.8 Chạy real smoke OCR với model cache; fixture biển số thực sẽ bổ sung ở M4.

**Exit gate:** OCR recognition-only chạy được trên crop fixture; warm call không tải lại model.

### 2.5 M1.5 — Normalize và confidence

- [x] 2.5.1 Normalize uppercase và loại separator để so sánh.
- [x] 2.5.2 Giữ raw OCR text để audit.
- [x] 2.5.3 Tách detector/OCR/combined confidence trong schema.
- [x] 2.5.4 Dùng combined conservative `min(detector, ocr)` ban đầu.
- [x] 2.5.5 Cấu hình threshold qua settings.
- [x] 2.5.6 Không tự sửa ký tự mạnh tay trước Operator confirmation.
- [x] 2.5.7 Viết unit test normalize, confidence bounds và requires_confirmation.

**Exit gate:** output deterministic và UI/API không phụ thuộc confidence chung cũ.

### 2.6 M1.6 — Ghép real provider

- [x] 2.6.1 Ghép decode → detector → crop → quality gate → OCR → normalize.
- [x] 2.6.2 Giữ `ALPRRuntime` boundary và caller không biết implementation.
- [x] 2.6.3 Lock inference nếu runtime chưa hỗ trợ concurrent calls.
- [x] 2.6.4 Trả no-plate/quality-fail với `requires_confirmation=true`.
- [x] 2.6.5 Readiness chỉ ready khi detector và OCR cùng sẵn sàng.
- [x] 2.6.6 Trả detector/OCR/full latency.
- [x] 2.6.7 Viết contract tests success, no-plate, low-confidence, quality-fail, dependency missing và processing error.

**Exit gate:** real provider trả đúng contract mock provider trên một ảnh fixture.

### 2.7 M1.7 — Preview API và persistence boundary

- [x] 2.7.1 Thêm mode preview/final nếu cần cho API hiện tại.
- [x] 2.7.2 Preview mặc định không tạo parking transaction.
- [x] 2.7.3 Không persist mọi frame video.
- [x] 2.7.4 Persist detection metadata/ảnh chỉ khi policy final yêu cầu.
- [x] 2.7.5 Trả HTTP 503 khi provider chưa ready.
- [x] 2.7.6 Trả HTTP 200 no-plate với confirmation flag.
- [x] 2.7.7 Test 10 preview liên tiếp không tạo 10 transaction.

**Exit gate M1:** toàn bộ `backend/tests/unit/alpr` pass; real smoke chạy được trên máy có model; mock vẫn pass.

## 3. M2 — Check-in domain và database

- [x] 3.1 Thiết kế additive migration cho transaction `PARKED`, detection link, source, actor, audit và idempotency.
- [x] 3.2 Tạo repository/service check-in tách khỏi ALPR provider.
- [x] 3.3 Validate lane `IN` active và normalized plate.
- [x] 3.4 Chặn duplicate active `PARKED`.
- [x] 3.5 Hỗ trợ `AI_ACCEPTED`, `OPERATOR_CORRECTED`, `MANUAL_ENTRY`.
- [x] 3.6 Implement idempotency cùng payload/cùng key và conflict khác payload.
- [x] 3.7 Ghi audit AI plate, final plate, source, actor, lane và timestamp.
- [x] 3.8 Implement history/filter endpoint cần cho demo.
- [x] 3.9 Viết unit/integration test happy path, manual, duplicate, retry, unauthorized, inactive lane và race.

**Exit gate M2:** mock detection → confirm → `PARKED` → history/audit end-to-end.

## 4. M3 — Video Station UI

- [x] 4.1 Đưa VideoPlayer/canvas thật vào `/station/scan` canonical flow.
- [x] 4.2 Chọn MP4 local, tạo/revoke object URL đúng lifecycle.
- [x] 4.3 Play/pause/replay/capture thủ công.
- [x] 4.4 Sampling mặc định 1000ms; có thể tăng lên 500ms sau benchmark.
- [x] 4.5 Không gửi request song song và không queue vô hạn.
- [x] 4.6 Overlay bbox theo tọa độ video.
- [x] 4.7 Hiển thị plate, detector/OCR/combined confidence, latency, model version và quality flags.
- [x] 4.8 Implement state `idle`, `detecting`, `reading`, `stable`, `needs_confirmation`, `confirming`, `success`, `error`.
- [x] 4.9 Implement buffer 3–5 candidate và consensus 2/3.
- [x] 4.10 Reset buffer khi bbox đổi lớn hoặc chuyển xe.
- [x] 4.11 Implement confirm đúng, edit plate và manual entry.
- [x] 4.12 Khóa double-click, retry timeout/network/provider error.
- [x] 4.13 Sau confirm hiển thị transaction id và history mới nhất.
- [x] 4.14 Viết component/integration tests cho video selection, throttle, bbox, consensus, confirmation và error.

**Exit gate M3:** Operator chạy video demo và tạo được một check-in thật từ UI.

## 5. M4 — Benchmark, hardening và demo

- [ ] 5.1 Tạo split `smoke`, `validation`, `demo`, `edge_cases` theo video/xe, không random frame liền nhau.
- [x] 5.2 Viết benchmark JSON/CSV cho detector, OCR và full pipeline.
- [x] 5.3 Đo exact match, character accuracy, no-result, false positive, p50/p95 latency.
- [x] 5.4 Đo time-to-stable, OCR calls/vehicle, candidate flip rate và provider error rate.
- [x] 5.5 Chạy cold/warm benchmark CPU demo.
- [x] 5.6 Chạy restart/model missing/OCR disabled/timeout/duplicate/idempotency checks.
- [x] 5.7 Real-only runbook and schema-compatible rollback; obsolete mock rollback removed.
- [ ] 5.8 Chụp screenshot/video evidence cho flow thành công, low-confidence, no-plate, sửa tay, duplicate và retry.
- [x] 5.9 Chạy backend pytest/ruff và frontend test/lint/build.
- [ ] 5.10 Chỉ đóng Phase 2 khi release gate pass.

## 6. Lệnh kiểm tra

```powershell
cd backend
py -3 -m pytest tests/unit/alpr -q
py -3 -m pytest tests -q
py -3 -m ruff check .
```

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Real provider smoke/benchmark chạy riêng trên môi trường có model asset và OCR
cache. CI không tải model thật và không yêu cầu GPU.

## 7. Release gate

- [x] `/station/scan` chạy video MP4 local.
- [x] Real readiness hợp lệ trên máy đã provision model asset.
- [x] YOLO + OCR đọc được video demo chính trên máy đã provision model asset.
- [x] Bbox overlay đúng.
- [x] Consensus 2/3 hoạt động.
- [x] Operator xác nhận/sửa/manual entry được.
- [x] Confirm tạo đúng một `PARKED`.
- [x] Duplicate/idempotency/audit pass.
- [x] Preview không tạo transaction rác.
- [x] CI với test doubles xanh; mock ứng dụng đã loại bỏ.
- [x] Warm p95 mục tiêu dưới 1 giây hoặc có benchmark ghi rõ giới hạn phần cứng. (CPU limit report: p95 3.03s; sub-second target not met.)
- [ ] Có benchmark report thật, runbook và đầy đủ evidence; còn thiếu coverage thật đa cảnh cho nghiệm thu chất lượng.

## 8. Integration reconciliation (2026-10-07)

- [x] 8.1 Station dùng shared token/client và backend provider, bỏ mock ALPR trong frontend.
- [x] 8.2 Preview không persist; final capture có UUID/fingerprint chống retry tạo detection trùng.
- [x] 8.3 Canonical confirmation ghi detection, PARKED và audit trong cùng transaction.
- [x] 8.4 Đồng bộ lane is_active, ALPR readiness, detection detail/filter và bbox pixel.
- [x] 8.5 Hoàn thiện Admin users/roles API; bảo toàn bốn role và policy read/write; registration mặc định tắt.
- [x] 8.6 Dashboard đọc số tổng từ database; manual entry không phụ thuộc provider.
- [x] 8.7 Additive migrations và regression SQLite/PostgreSQL; kiểm tra frontend test/lint/build.
- [x] 8.8 Refresh Compose và chạy browser smoke với video tổng hợp, lưu evidence có ghi rõ mock.
- [x] 8.9 Đồng bộ runbook/contracts; bỏ claim benchmark thật dựa trên fixture tổng hợp.
- [x] 8.10 Bật real provider trong Docker: CPU dependencies, model/cache mounts, startup warmup và API/OCR inference smoke.

## 9. Real-data completion reconciliation (2026-10-07)

Các ghi chú thiếu video có nhãn trước đây được thay bằng kết quả mới: video miLPR
trong Downloads do người dùng chỉ định đã chạy YOLO/PaddleOCR thật, 10 frame
positive thuộc hai xe và một title-frame negative. Exact match 8/10, character
accuracy 97,5%; warm p50/p95 1,30/3,03 giây, cold 36,86 giây.
Chrome đã confirm ảnh `29A90101` và video `30V4495` thành PARKED trên môi trường
restore riêng; Docker lifecycle giữ nguyên row/media hashes. OCR smoke 2.4.8 và
đo 5.3–5.5 có evidence thật, không train hay đổi weights.

Evidence: `docs/phase-2-evidence/completion-user-video-benchmark.json`,
`completion-browser.json`, `completion-lifecycle-final.json` và
`docs/real-data-completion-report-2026-10-07.md`.
M4 vẫn mở: 5.1 chưa đủ dữ liệu để chia validation/demo/edge_cases độc lập;
5.8 chưa có đầy đủ screenshot/video từng tình huống thật; 5.10/release chất lượng
chưa đóng. Không suy ra accuracy tổng quát từ hai xe/frame liền nhau, không tự động
thông xe. Evidence mock/synthetic ở mục lịch sử chỉ chứng minh contract.
Ứng dụng hiện chỉ có real provider; test doubles giữ trong tests.
