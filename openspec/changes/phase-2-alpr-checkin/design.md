## Context

Phase 2 cần đưa VisionPark từ mock ALPR sang một vertical slice chạy thật trên
video MP4 local: YOLO detector hiện tại, OCR pretrained, Operator xác nhận, rồi
tạo parking transaction `PARKED`. Phase này chưa tích hợp camera vật lý/RTSP.

Repository đã có runtime boundary, mock provider, model manifest, Station video
components và các endpoint ALPR cơ bản. Tuy nhiên real OCR, temporal consensus,
preview persistence boundary và check-in end-to-end chưa được chứng minh.

## Goals

- Chạy real detector + OCR trên video MP4 local.
- Tách và test độc lập từng module AI trước khi ghép.
- Giữ mock provider deterministic cho CI.
- Không ghi database rác từ preview frame.
- Cho Operator xác nhận/sửa biển số.
- Tạo đúng một transaction `PARKED` với duplicate protection và idempotency.
- Có benchmark latency/accuracy và runbook chạy lại được.

## Non-goals

- Camera thật, RTSP, WebSocket, Redis.
- Tracking nhiều xe/multi-camera.
- Barrier, payment, pricing, ticketing.
- Train YOLO/OCR mới trong luồng Phase 2 chính.
- ONNX production path khi output decoder chưa được chứng minh.

## Decisions

### 1. Video MP4 là input duy nhất của demo

Browser dùng HTML video + canvas để capture frame. Sampling ban đầu là 1 FPS,
sau benchmark có thể tăng lên 2 FPS. Một lane chỉ có một request đang xử lý;
không tạo queue frame vô hạn.

### 2. Giữ YOLO `.pt` hiện tại làm detector

Không train lại trước benchmark. Nếu recall detector không đạt trên validation
thật, fine-tune là một nhánh riêng sau khi vertical slice đã chạy ổn định.

### 3. Dùng PaddleOCR recognition-only

Dùng `latin_PP-OCRv5_mobile_rec` qua `TextRecognition` trên crop biển số.
Không chạy text detection vì YOLO đã trả bbox. OCR model phải được cache/mount
trước runtime, không tải ngầm từ Internet trong request.

### 4. Quality gate trước OCR

Crop phải được mở rộng 8–12%, clamp và kiểm tra kích thước, aspect ratio, blur,
brightness và contrast. Crop không đạt gate trả quality flag và yêu cầu Operator
xác nhận/manual entry, không cố OCR vô hạn.

### 5. Tách confidence

Contract trả riêng `detector_confidence`, `ocr_confidence` và
`combined_confidence`. Combined ban đầu dùng giá trị conservative `min` của hai
score; threshold phải cấu hình được.

### 6. Temporal consensus ở Station session

Frontend giữ tối đa 3–5 candidate gần nhất. Candidate stable khi cùng
`normalized_plate` xuất hiện ít nhất 2/3 kết quả. Consensus chỉ quyết định UI
candidate; confirm mới được phép tạo transaction.

### 7. Preview và final tách biệt

Preview phục vụ hiển thị/consensus và mặc định không persist detection/ảnh.
Confirm/final mới persist metadata nghiệp vụ cần thiết. Raw AI result phải được
giữ lại khi Operator sửa biển số.

### 8. Check-in thuộc parking domain

ALPR chỉ trả kết quả nhận diện. Check-in service chịu trách nhiệm lane `IN`,
duplicate active `PARKED`, transaction, audit và idempotency.

### 9. Không dùng ONNX provider hiện tại trong demo

`onnx_provider.py` còn placeholder output decoding. Phase 2 dùng provider
Ultralytics `.pt`; ONNX chỉ được mở sau benchmark nếu cần tối ưu latency và phải
có task decoder/test riêng.

## Module boundaries

```text
M0 contract/asset/route gate
M1.1 image decode
M1.2 YOLO detector
M1.3 crop + quality gate
M1.4 PaddleOCR recognizer
M1.5 normalize + confidence
M1.6 real provider composition
M1.7 preview/persistence boundary
M2 check-in/database
M3 video Station/consensus
M4 benchmark/demo hardening
```

Mỗi module phải có test và exit gate trước khi chuyển sang module tiếp theo.

## Error and fallback policy

- Model missing/checksum/dependency error: readiness `not_ready`, HTTP 503.
- Ảnh hỏng: HTTP 422, không gọi inference.
- Không có biển: kết quả hợp lệ với `requires_confirmation=true`.
- Crop kém chất lượng: quality flags + manual fallback.
- OCR timeout/error: typed error + retry/manual fallback.
- Confidence thấp: không auto-confirm.
- Duplicate plate: conflict, không tạo transaction mới.
- Confirm retry cùng key: trả lại transaction cũ.

## Distribution

Model weights và OCR model cache không commit vào Git. Manifest phải ghi provider,
model version, path, checksum và trạng thái artifact. CI dùng mock/fixture nhỏ;
real benchmark chạy ở môi trường có asset được cấp quyền.

## Migration and rollout

1. Chạy Phase 1 regression gate.
2. Hoàn thành M0 và M1 bằng fixture.
3. Hoàn thành mock check-in vertical slice.
4. Bật real provider trên máy demo có model asset.
5. Chạy video benchmark.
6. Chỉ demo khi readiness, latency, consensus, confirm và fallback đều pass.
7. Nếu real provider lỗi, chuyển config về mock; không xóa dữ liệu nghiệp vụ.

## Acceptance gate

- `/station/scan` chạy video MP4 local.
- Real provider đọc được video demo chính.
- Bbox hiển thị đúng trên video.
- Candidate stable bằng consensus 2/3.
- Operator xác nhận/sửa được biển số.
- Confirm tạo đúng một `PARKED`.
- Duplicate/idempotency/audit pass.
- Mock CI xanh không cần GPU/model thật.
- Có benchmark report và runbook.


### Integration contract reconciliation

Station luôn gọi backend qua shared API client và token `visionpark.access_token`.
Provider mock/real được quyết định ở backend. Preview trả `detection_id=null`;
frontend giữ candidate UUID và ảnh trong buffer giới hạn. Final gửi UUID bằng
`capture_id`; database lưu fingerprint và trả lại detection cho cùng ảnh/lane khi retry,
reject khi UUID dùng cho payload khác. Capture và confirmation là hai request;
confirmation thất bại có thể để lại final detection chưa confirmed để retry.

POST `/api/v1/alpr/detections/{id}/confirm` nhận `confirmed_plate`; với
`check_in=true` và `Idempotency-Key`, check-in service ghi confirmed metadata,
PARKED và audit atomically. Không bật check_in thì chỉ xác nhận metadata.
Manual dùng `/api/v1/parking/check-in`, không gọi provider. UI khóa capture/lane/video
trong confirmation và reset candidate khi chuyển lane/video/xe.

Operator được đọc lanes và vận hành Station/detections/parking; Admin được thêm
quyền quản lý lane/users/roles/audit. Accountant/Technician không được ép thành
Operator. Admin user CRUD là carry-over để UI có endpoint thật; registration tắt mặc
định, khi bật chỉ tạo OPERATOR. Migrations additive giữ dữ liệu hiện có.

Benchmark real yêu cầu image_path tồn tại trong dataset, không dùng ảnh tổng hợp
làm bằng chứng độ chính xác thật. Browser smoke dùng MP4 tổng hợp và backend mock;
503 trong smoke là lỗi được inject có ghi rõ trong report.
