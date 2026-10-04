làm m# Phase 2 — ALPR trên video và check-in end-to-end

## 0. Mục tiêu

Xây dựng vertical slice chạy thật bằng video MP4 local trên trình duyệt:

```text
Video MP4
  -> capture frame bằng canvas
  -> YOLO phát hiện vùng biển số
  -> crop + quality gate
  -> PaddleOCR recognition-only đọc ký tự
  -> consensus nhiều frame
  -> Operator xác nhận hoặc sửa
  -> check-in PARKED
  -> history và audit
```

Phase này phục vụ demo thật, không phải camera production. Mục tiêu là hệ thống có thể chạy ổn định, đo được và có fallback rõ ràng khi model không đọc được.

## 1. Phạm vi

### Có trong Phase 2

- Chọn video `.mp4` local trong Station UI.
- Chọn một lane `IN` đang active.
- Sampling frame từ video bằng HTML video + canvas.
- Real detector dùng YOLO `best.pt` hiện tại.
- Real OCR dùng PaddleOCR recognition-only.
- Hiển thị bbox, biển số, confidence và latency.
- Consensus `2/3` frame để giảm kết quả nhảy.
- Operator xác nhận hoặc sửa biển số.
- Tạo parking transaction `PARKED`.
- Chống duplicate và idempotency.
- Lưu audit và lịch sử.
- Mock provider cho CI/local khi không có model.
- Benchmark trên video/ảnh validation cố định.

### Không có trong Phase 2

- Camera vật lý hoặc RTSP.
- Multi-camera, tracking nhiều xe hoặc nhận diện đồng thời nhiều lane.
- WebSocket, Redis hoặc distributed inference.
- Barrier, thanh toán, tính phí, vé tháng.
- Train model YOLO/OCR mới trong luồng chính.
- Export ONNX nếu chưa có bằng chứng `.pt` không đạt latency.

## 2. Quyết định kỹ thuật đã chốt

### 2.1. Detector

Giữ model detector hiện tại:

```text
Ultralytics YOLO
weights: backend/app/alpr/weights/best.pt
```

Không train lại detector trước khi có benchmark. Nếu detector bỏ sót biển số trên tập validation thật, mở nhánh fine-tune riêng sau khi vertical slice chạy được.

### 2.2. OCR

Dùng PaddleOCR của PaddlePaddle, model recognition-only:

```text
latin_PP-OCRv5_mobile_rec
```

Có thể benchmark đối chứng với `PP-OCRv5_mobile_rec`. Vì YOLO đã trả bbox biển số, không chạy thêm text detection tổng quát.

Tài liệu tham khảo:

- https://github.com/PaddlePaddle/PaddleOCR
- https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/module_usage/text_recognition.html
- https://paddlepaddle.github.io/PaddleOCR/main/en/quick_start.html

Model OCR phải được tải/caching trước trong môi trường demo. Request runtime không được phụ thuộc Internet để tải model.

### 2.3. Runtime

- Mock provider là mặc định của CI.
- Real provider bật bằng environment.
- Runtime lazy-load hoặc warm-up một lần, không load model lại cho từng request.
- `onnx_provider.py` chưa được dùng làm provider demo vì phần decode output hiện chưa hoàn chỉnh.
- Nếu `.pt` đạt latency thì giữ `.pt` trong Phase 2.

### 2.4. Video sampling

- Demo ban đầu: 1 frame/giây.
- Sau khi benchmark đạt: cho phép 2 frame/giây.
- Mỗi lane chỉ có một request đang xử lý.
- Không xếp hàng vô hạn; frame cũ có thể bị bỏ qua.
- Sau khi candidate stable, giảm hoặc dừng OCR cho đến khi xe thay đổi.

## 3. Kiến trúc module

```text
M0 Contract / asset / route gate
  |
  +--> M1.1 Image input và decode
  +--> M1.2 YOLO detector
  +--> M1.3 Crop và quality gate
  +--> M1.4 PaddleOCR recognizer
  +--> M1.5 Normalize và confidence
  +--> M1.6 Ghép real provider
  +--> M1.7 API preview và persistence boundary
  |
  +--> M2 Check-in domain và database
  |
  +--> M3 Video Station UI và temporal consensus
  |
  +--> M4 Benchmark, hardening và demo
```

Nguyên tắc làm việc: hoàn thành và test pass từng module trước khi ghép module kế tiếp. Không debug toàn bộ pipeline cùng lúc.

## 4. M0 — Gate trước khi code

### M0.1. Chốt route Station

Hiện `/station/scan` đang trỏ vào `ScanPage`, trong khi `StationPage` đã có `VideoPlayer` thật. Agent phải chọn một flow canonical:

- giữ `/station/scan` là route chính;
- đưa player/canvas thật vào flow này;
- không duy trì hai implementation ALPR song song;
- fullscreen chỉ là view của cùng state, không tạo pipeline riêng.

### M0.2. Chốt contract

Response preview tối thiểu:

```json
{
  "detection_id": null,
  "raw_plate": "29A-123.45",
  "normalized_plate": "29A12345",
  "bbox": [120, 340, 250, 410],
  "detector_confidence": 0.94,
  "ocr_confidence": 0.91,
  "combined_confidence": 0.91,
  "requires_confirmation": false,
  "quality_flags": [],
  "model_version": "...",
  "processing_time_ms": 180,
  "provider_status": "ready"
}
```

Quy tắc:

- preview không tạo parking transaction;
- final/confirm mới tạo `PARKED`;
- no-plate/low-confidence không làm request crash;
- raw result không bị mất khi Operator sửa biển số;
- frontend dùng `/api/v1/alpr/detections/{id}/confirm`;
- confirm phải có idempotency key.

### M0.3. Gate test

Pass khi:

- có video MP4 demo chính;
- có lane `IN` fixture;
- mock flow chạy được;
- route Station canonical đã được xác định;
- contract response/request được backend và frontend cùng sử dụng.

## 5. M1 — Real ALPR provider, chia nhỏ để test độc lập

M1 là module AI cốt lõi. Mỗi submodule phải có test riêng và exit gate riêng.

### M1.1. Image input và decode

**Input:** bytes JPEG/PNG từ API.

**Output:** ảnh OpenCV hợp lệ.

**Cần làm:**

- kiểm tra content type;
- giới hạn kích thước request;
- decode bằng OpenCV;
- trả typed error cho ảnh hỏng;
- không gọi YOLO/OCR nếu decode thất bại.

**Test:**

- JPEG hợp lệ;
- PNG hợp lệ;
- bytes rỗng;
- file sai định dạng;
- ảnh vượt giới hạn.

**Exit gate:** tất cả test pass, lỗi trả đúng `INVALID_IMAGE` hoặc mã tương đương.

### M1.2. YOLO detector adapter

**Input:** ảnh OpenCV.

**Output:** bbox biển số và `detector_confidence`.

**Cần làm:**

- load `best.pt` một lần;
- đọc `plate_class` từ manifest;
- chọn bbox biển số tốt nhất;
- clamp bbox vào kích thước ảnh;
- trả no-plate hợp lệ;
- đo latency detector;
- readiness phân biệt model missing, checksum mismatch và dependency missing.

**Test:**

- một biển số;
- nhiều biển số;
- không có biển số;
- bbox sát biên;
- class không phải `plate`;
- confidence thấp;
- model không tồn tại;
- checksum sai;
- YOLO inference exception.

**Exit gate:** detector chạy được trên fixture thật và trả bbox không vượt biên.

### M1.3. Crop và quality gate

**Input:** ảnh + bbox từ M1.2.

**Output:** crop hợp lệ hoặc quality flags.

**Cần làm:**

- mở rộng bbox 8–12%;
- clamp sau khi mở rộng;
- kiểm tra chiều rộng/chiều cao tối thiểu;
- kiểm tra aspect ratio;
- đo blur bằng variance of Laplacian hoặc tiêu chí tương đương;
- kiểm tra brightness/contrast;
- giữ crop tốt nhất cho OCR;
- không chạy OCR khi crop không đạt gate.

**Quality flags:**

```text
bbox_out_of_bounds
bbox_too_small
crop_blurry
crop_dark
crop_low_contrast
crop_invalid_ratio
ocr_skipped_quality
```

**Test:**

- crop bình thường;
- crop sát biên;
- crop quá nhỏ;
- crop mờ;
- crop tối;
- crop sai tỷ lệ;
- bbox bị clamp.

**Exit gate:** crop không làm mất ký tự ở fixture rõ và quality gate chặn đúng ảnh xấu.

### M1.4. PaddleOCR recognition adapter

**Input:** crop biển số từ M1.3.

**Output:** `raw_plate` và `ocr_confidence`.

**Cần làm:**

- dùng `TextRecognition`;
- dùng `latin_PP-OCRv5_mobile_rec`;
- không chạy text detection trên crop;
- lazy-load/warm-up một lần;
- hỗ trợ CPU trước;
- parse được output PaddleOCR hiện tại;
- typed error cho OCR dependency/model/inference;
- có timeout hoặc cơ chế chặn request treo.

**Test:**

- crop biển rõ;
- crop biển hai dòng;
- crop hơi nghiêng;
- crop mờ;
- crop tối;
- crop không có ký tự;
- OCR model missing;
- OCR dependency missing;
- OCR inference error.

**Exit gate:** OCR trả text và score trên fixture rõ; không tải model trong mỗi request.

### M1.5. Normalize và confidence policy

**Input:** raw OCR text, detector score, OCR score.

**Output:** normalized plate và confidence fields.

**Cần làm:**

- uppercase;
- loại khoảng trắng, dấu chấm, dấu gạch khi so sánh;
- giữ raw text để audit;
- không tự ý sửa ký tự mạnh tay trước khi Operator xác nhận;
- trả riêng detector/OCR/combined confidence;
- dùng `min(detector_confidence, ocr_confidence)` làm combined conservative ban đầu;
- threshold cấu hình được, không hard-code trong UI.

**Test:**

- `29A-123.45` → `29A12345`;
- text có whitespace;
- text rỗng;
- confidence ngoài khoảng 0–1;
- detector cao/OCR thấp;
- detector thấp/OCR cao;
- requires confirmation theo threshold.

**Exit gate:** normalization deterministic và UI/API không còn phụ thuộc một confidence chung.

### M1.6. Ghép real provider

**Input:** image bytes.

**Output:** ALPR contract thống nhất.

**Pipeline:**

```text
decode
  -> detector
  -> bbox validation
  -> crop margin
  -> quality gate
  -> OCR recognition
  -> normalize
  -> confidence aggregation
```

**Cần làm:**

- giữ runtime boundary hiện tại;
- lock inference nếu provider chưa hỗ trợ concurrent inference;
- load model một lần;
- đo detector/OCR/full latency riêng;
- readiness chỉ `ready` khi detector và OCR đều sẵn sàng;
- no-plate trả kết quả hợp lệ, không exception;
- quality fail trả `requires_confirmation=true`.

**Test:**

- happy path;
- no-plate;
- low confidence;
- quality fail;
- OCR disabled;
- model missing;
- dependency missing;
- processing error;
- concurrent calls không làm hỏng runtime.

**Exit gate:** real provider chạy được bằng một ảnh fixture và giữ API tương thích mock provider.

### M1.7. API preview và persistence boundary

**Cần làm:**

- thêm mode preview/final nếu contract hiện tại cần;
- preview mặc định không persist detection/ảnh;
- final hoặc confirm mới persist metadata cần thiết;
- không ghi database liên tục cho từng frame video;
- response trả detection id chỉ khi cần cho confirm;
- log provider, model version và latency.

**Test:**

- 10 preview liên tiếp không tạo 10 parking transaction;
- preview lỗi không làm mất session;
- final có detection link;
- model not ready trả HTTP 503;
- no-plate trả HTTP 200 với `requires_confirmation=true`.

**Exit gate:** M1 hoàn thành khi toàn bộ test AI/provider pass và có lệnh smoke real provider.

## 6. M2 — Check-in domain và database

### M2.1. Database

- parking transaction `PARKED`;
- link tới detection;
- normalized plate;
- lane;
- operator;
- confirmation source;
- idempotency key/fingerprint;
- timestamps;
- additive migration, không phá dữ liệu Phase 1.

### M2.2. Check-in service

- chỉ cho lane `IN` active;
- reject plate rỗng/không hợp lệ;
- reject plate đang `PARKED`;
- hỗ trợ `AI_ACCEPTED`, `OPERATOR_CORRECTED`, `MANUAL_ENTRY`;
- transaction database atomic;
- retry cùng idempotency key trả cùng kết quả;
- cùng key khác payload trả conflict.

### M2.3. API

Canonical endpoint:

```text
POST /api/v1/alpr/detections/{detection_id}/confirm
```

Test bắt buộc:

- check-in AI accepted;
- sửa biển số;
- manual entry;
- lane inactive;
- lane OUT;
- duplicate active parked;
- double-click;
- retry cùng key;
- retry khác payload;
- unauthorized.

**Exit gate:** mock provider chạy được từ detection đến transaction `PARKED`.

## 7. M3 — Video Station UI

### M3.1. Video input

- chọn MP4 local;
- tạo/revoke object URL đúng lifecycle;
- play/pause/replay;
- capture frame bằng canvas;
- hiển thị video name;
- báo lỗi khi video không đọc được.

### M3.2. Sampling/throttle

- mặc định 1000 ms/frame;
- không gửi request song song;
- không tạo queue vô hạn;
- dừng auto capture khi video kết thúc;
- disable control phù hợp khi đang xử lý;
- hỗ trợ capture thủ công để debug.

### M3.3. Result/overlay

- overlay bbox theo đúng hệ tọa độ video;
- hiển thị raw/normalized plate;
- hiển thị detector/OCR/combined confidence;
- hiển thị latency và model version;
- trạng thái `idle`, `detecting`, `reading`, `stable`, `needs_confirmation`, `confirming`, `success`, `error`.

### M3.4. Temporal consensus

- buffer tối đa 3–5 candidate;
- stable khi cùng normalized plate xuất hiện ít nhất 2/3;
- reset khi bbox thay đổi lớn hoặc video chuyển sang xe khác;
- cooldown sau stable;
- candidate thay đổi phải hiển thị rõ cho Operator;
- consensus không tạo transaction tự động.

### M3.5. Confirm/fallback

- nút xác nhận biển số đúng;
- ô sửa biển số;
- manual entry khi no-plate;
- khóa double-click;
- hiển thị duplicate/timeout/provider error;
- sau confirm hiển thị transaction id và history mới nhất.

**Exit gate:** Operator chạy được video demo, thấy bbox, thấy candidate stable và tạo được check-in.

## 8. M4 — Benchmark và demo

### Dataset/video split

- `smoke`: vài frame để kiểm tra wiring;
- `validation`: video cố định, không dùng trong tuning từng request;
- `demo`: video dùng trình diễn;
- `edge_cases`: mờ, tối, nghiêng, no-plate, nhiều frame không có biển.

Không split ngẫu nhiên các frame liền nhau của cùng một xe vào cả train/validation vì sẽ làm số liệu ảo.

### Chỉ số

- detection success rate;
- OCR exact match;
- character accuracy;
- no-plate rate;
- false positive rate;
- detector p50/p95;
- OCR p50/p95;
- full pipeline p50/p95;
- time-to-stable;
- OCR calls per vehicle;
- candidate flip rate;
- provider error rate.

### Release gate

- real readiness hợp lệ;
- warm inference p95 mục tiêu dưới 1 giây;
- biển rõ stable trong khoảng 1–2 giây;
- tối đa 1–2 OCR call/giây/lane;
- không có request preview đồng thời trên cùng lane;
- preview không tạo transaction;
- confirm tạo đúng một `PARKED`;
- duplicate/idempotency pass;
- manual fallback pass;
- mock CI xanh;
- benchmark report và video evidence được lưu.

## 9. Quy tắc train sau Phase 2

Không train model mới trước khi M1–M4 có số liệu.

| Kết quả benchmark                  | Hành động                                 |
| ---------------------------------- | ----------------------------------------- |
| YOLO bỏ sót biển số                | Bổ sung bbox dataset và fine-tune YOLO    |
| Bbox đúng nhưng OCR sai            | Fine-tune OCR trên crop có transcription  |
| Từng frame đúng nhưng kết quả nhảy | Cải thiện crop, quality gate và consensus |
| Sai chủ yếu ban đêm/góc nghiêng    | Bổ sung dữ liệu theo điều kiện đó         |
| Accuracy đạt nhưng chậm            | Tối ưu mobile model, sau đó cân nhắc ONNX |
| Accuracy và latency đạt            | Giữ model, không train thêm               |

## 10. Agent protocol

Agent phải làm theo thứ tự:

1. Đọc plan này và kiểm tra trạng thái repo.
2. Chỉ sửa một module đang active.
3. Viết test trước hoặc cùng lúc với implementation.
4. Chạy test module đó.
5. Chỉ chuyển module kế tiếp khi exit gate pass.
6. Không đổi API contract ngầm giữa các module.
7. Không thay ONNX provider trong Phase 2 nếu chưa có task riêng.
8. Không train model trong luồng chính.
9. Sau mỗi milestone chạy regression toàn bộ.
10. Khi có lỗi model, giữ manual fallback và ghi lại artifact/version.

## 11. Lệnh kiểm tra chuẩn

Backend:

```powershell
cd backend
py -3 -m pytest tests/unit/alpr -q
py -3 -m pytest tests -q
py -3 -m ruff check .
```

Frontend:

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Real provider smoke test phải chạy riêng trên máy có model và OCR dependency; CI chỉ bắt buộc mock/contract tests.

## 12. Trạng thái hoàn thành Phase 2

Phase 2 chỉ đóng khi có đủ:

- real model manifest và checksum;
- provider readiness;
- module M1 test pass;
- mock vertical slice pass;
- real video demo pass;
- temporal consensus pass;
- check-in/idempotency/duplicate pass;
- manual fallback pass;
- frontend/backend regression pass;
- benchmark report;
- README/runbook cho agent hoặc thành viên khác chạy lại được.
