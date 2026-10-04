# Phase 2 — Kế hoạch riêng cho role AI

> Phạm vi của tài liệu này chỉ dành cho AI/ALPR. Không bao gồm việc triển khai parking transaction, UI Operations hay migration backend, ngoại trừ các contract và handoff mà role AI phải cung cấp cho các role đó.

## 1. Mục tiêu của role AI

Hoàn thiện một AI runtime có thể:

1. Nhận một frame ảnh từ backend/frontend.
2. Phát hiện biển số bằng model detector đã train.
3. Crop biển số ổn định, đủ chất lượng.
4. Đọc ký tự bằng OCR pretrained.
5. Trả về kết quả có cấu trúc, confidence và latency.
6. Báo readiness/model version rõ ràng.
7. Chạy được real mode khi có model asset.
8. Vẫn giữ mock mode cho CI và môi trường không có model.
9. Có benchmark reproducible để biết model có đủ tốt hay chưa.
10. Bàn giao contract ổn định cho backend check-in và frontend Station.

## 2. Phạm vi task Phase 2 của AI

### Task chính thuộc role AI

- 1.1: hỗ trợ Phase 1 gate và ghi lại Critical/High carry-over liên quan AI.
- 1.3: chốt model/dataset policy, manifest, provider config và benchmark command.
- 1.4: cung cấp fixture AI dùng chung.
- 2.1: provider adapter/config — đã hoàn thành.
- 2.2: manifest, checksum, version và readiness — đã hoàn thành nền tảng.
- 2.3: kết nối detector/OCR baseline thật.
- 2.4: contract tests cho provider.
- 2.5: benchmark script/report.
- 7.2: chạy real provider trên môi trường có model asset.
- 7.5: đóng góp benchmark report, README/runbook và evidence.

### Task AI hỗ trợ nhưng không sở hữu chính

- 1.2: thống nhất detection response contract.
- 7.1: ghép flow mock/real với backend và frontend.
- 7.3: đảm bảo CI test mock không cần model/GPU.
- 7.4: regression, timeout, provider error và clean setup.
- 7.6: acceptance demo và release gate.

### Không thuộc role AI

- Tạo parking transaction PARKED.
- Idempotency của check-in nghiệp vụ.
- Auth/RBAC và lane validation.
- History/audit UI.
- Database migration parking.
- UI confirm/edit ngoài việc cung cấp dữ liệu AI.

## 3. Hiện trạng cần chốt

### Đã có

- Detector weight tại backend/app/alpr/weights/best.pt.
- Runtime boundary cho mock/real provider.
- Manifest/checksum/model version.
- Lazy-load runtime.
- Cấu hình provider và OCR flag.
- Response hiện có plate, bbox, confidence và processing time.

### Còn thiếu

1. Chưa chứng minh detector/OCR thật chạy ổn định với ảnh fixture.
2. Chưa có benchmark report có dataset split cố định.
3. Chưa tách detector confidence và OCR confidence.
4. Chưa có quality gate trước khi gửi crop sang OCR.
5. Chưa có temporal consensus ở tầng AI/session.
6. Chưa thống nhất cách xử lý no-plate, low-confidence và OCR timeout.
7. Chưa có readiness detail đủ cho backend/UI.
8. Chính sách phân phối best.pt đang mâu thuẫn: design nói không commit model weight nhưng repository hiện đang có model weight.
9. Cần xác nhận dependency OCR chạy được trong Docker runtime.
10. Cần có runbook để thành viên khác chạy real provider.

## 4. Quyết định kỹ thuật đề xuất

### 4.1. Detector

- Giữ model YOLO hiện tại làm detector baseline.
- Không train lại detector trong Phase 2 nếu chưa có bằng chứng model hiện tại không đạt.
- Không thay đổi runtime boundary của caller.
- Mỗi prediction phải trả bbox, detector confidence, class/label, model version và processing time.

### 4.2. OCR

Dùng PaddleOCR pretrained trước, chưa train OCR ngay.

Lý do:

- OCR là bài toán khác detector; model biển số không tự đọc được ký tự.
- Có baseline sớm để phân biệt lỗi do detector, crop hay OCR.
- Fine-tune chỉ có ý nghĩa sau khi có tập validation đủ đại diện.

Chỉ chuyển sang fine-tune khi benchmark cho thấy lỗi có tính hệ thống: biển nghiêng, ánh sáng ban đêm, font/ký tự riêng, biển hai dòng, blur hoặc độ phân giải thấp.

### 4.3. Crop và quality gate

Pipeline AI:

    image
      -> detector
      -> bbox validation
      -> crop margin 5–10%
      -> quality gate
      -> resize/preprocess
      -> OCR
      -> normalize
      -> confidence aggregation

Quality gate kiểm tra:

- bbox không vượt ảnh;
- crop có kích thước tối thiểu;
- aspect ratio hợp lý;
- crop không bị cắt quá nhiều;
- độ sắc nét tối thiểu;
- brightness/contrast không quá thấp;
- không OCR lại cùng một crop nếu chưa có lý do.

Quality flags đề xuất:

- bbox_too_small;
- crop_blurry;
- crop_dark;
- crop_out_of_bounds;
- ocr_skipped_quality.

### 4.4. Confidence

Không dùng một confidence chung để che mất nguyên nhân lỗi.

Response cần có:

- detector_confidence;
- ocr_confidence;
- combined_confidence;
- requires_confirmation;
- quality_flags.

Cách tính ban đầu có thể conservative:

- detector không đạt threshold thì không OCR hoặc yêu cầu confirm;
- OCR không đạt threshold thì trả candidate nhưng requires_confirmation=true;
- combined confidence lấy min hoặc weighted score, phải ghi rõ trong config;
- không tự động confirm chỉ vì detector confidence cao.

### 4.5. Temporal consensus

Nếu session/lane cần đọc từ video, không chốt theo một frame.

- Giữ 3–5 candidate gần nhất.
- Chấp nhận khi cùng normalized plate xuất hiện 2/3 lần.
- Ưu tiên candidate có quality và OCR confidence cao hơn.
- Reset khi bbox thay đổi lớn hoặc xe đã đổi.
- Cooldown sau khi candidate ổn định.

Role AI phải cung cấp normalized plate, confidence, bbox, timestamp/processing time, model version và quality flags để caller thực hiện consensus.

## 5. Contract AI bàn giao

### Input

Provider nhận image bytes, optional lane/camera context, provider config, request timeout và mode preview/final nếu caller cần phân biệt.

Provider không tự tạo parking transaction.

### Output tối thiểu

- raw_plate;
- normalized_plate;
- bbox;
- detector_confidence;
- ocr_confidence;
- combined_confidence;
- requires_confirmation;
- model_version;
- provider;
- processing_time_ms;
- quality_flags;
- provider_status.

### Trạng thái readiness

Phải phân biệt:

- ready;
- not_ready;
- model_missing;
- manifest_invalid;
- checksum_mismatch;
- ocr_unavailable;
- dependency_error;
- warmup_failed;
- disabled_by_config.

Readiness cần hiển thị provider name, detector model version, OCR provider/version, artifact id, checksum, OCR enabled/disabled, last error và warmup status.

### Lỗi provider

Không nuốt exception thành plate rỗng. Cần phân biệt:

- ảnh không hợp lệ;
- không tìm thấy biển;
- detector inference error;
- OCR inference error;
- model chưa sẵn sàng;
- timeout;
- dependency missing;
- low quality;
- low confidence.

## 6. Cách chạy mượt khi xem video

Mục tiêu của role AI là giảm số lần OCR, không phải OCR mọi frame.

### Sampling đề xuất

- Frontend gửi preview khoảng 2 FPS.
- Chỉ có một request đang xử lý cho mỗi lane.
- Backend/provider không xếp hàng vô hạn.
- OCR tối đa khoảng 1–2 lần/giây/lane.
- Detector có thể chạy trên mỗi sampled frame.
- OCR chỉ chạy khi có bbox mới, crop tốt hơn, candidate chưa ổn định hoặc đã qua cooldown.

### Chuỗi xử lý

1. Nhận frame.
2. Detector trả bbox nhanh.
3. Quality gate loại crop xấu.
4. OCR đọc crop tốt nhất.
5. Normalize candidate.
6. Caller gom 2/3 candidate.
7. Trả candidate stable cho operator.
8. Sau confirm, dừng OCR cho xe đó hoặc chuyển cooldown.

### Không làm trong Phase 2

- Không OCR toàn bộ frame.
- Không lưu ảnh preview liên tục.
- Không chạy nhiều OCR song song trên cùng lane.
- Không đưa Redis/WebSocket vào chỉ để giải quyết một request stream.
- Không tự động tạo check-in từ AI result chưa confirm.

## 7. Kế hoạch triển khai theo thứ tự

### Mốc AI-0 — Chốt contract và asset

Đầu ra:

- quyết định model weight ở Git, Git LFS hay artifact;
- manifest schema ổn định;
- provider config;
- response schema;
- threshold config;
- benchmark command;
- fixture policy.

Việc cần làm:

- rà lại best.pt và checksum;
- cập nhật README model;
- ghi rõ cách bật real provider;
- ghi rõ cách bật/tắt OCR;
- thống nhất model_version và provider;
- thống nhất field confidence.

### Mốc AI-1 — Kết nối detector thật

Đầu ra:

- detector chạy được với một ảnh;
- bbox và confidence đúng;
- model missing/readiness đúng;
- latency đo được.

Test bắt buộc:

- ảnh có một biển;
- ảnh có nhiều biển;
- ảnh không có biển;
- bbox biên ảnh;
- confidence thấp;
- model path sai;
- checksum sai;
- inference exception.

### Mốc AI-2 — Kết nối OCR baseline

Đầu ra:

- crop từ bbox;
- OCR đọc candidate;
- raw/normalized plate;
- OCR confidence;
- quality flags;
- timeout/error riêng.

Test bắt buộc:

- biển rõ;
- biển nghiêng;
- biển hai dòng;
- biển mờ;
- ảnh tối;
- crop quá nhỏ;
- ký tự bị cắt;
- no-plate;
- OCR disabled;
- OCR dependency missing.

### Mốc AI-3 — Temporal và performance

Đầu ra:

- candidate buffer hoặc contract cho caller;
- consensus 2/3;
- cooldown;
- rate limit;
- không request chồng nhau;
- warmup và latency metrics.

Đo:

- số OCR call trên mỗi vehicle;
- thời gian từ frame đầu đến stable;
- detector p50/p95;
- OCR p50/p95;
- full provider p50/p95;
- cold-start latency;
- tỷ lệ candidate sai trước/sau consensus.

### Mốc AI-4 — Benchmark và handoff

Đầu ra:

- benchmark JSON/CSV;
- report Markdown;
- model card ngắn;
- README/runbook;
- evidence ảnh/video;
- checklist backend/frontend handoff.

## 8. Benchmark bắt buộc

### Dataset split

Tối thiểu:

- smoke: ít ảnh, chạy nhanh để kiểm tra wiring;
- validation: tập ảnh cố định để so sánh model/config;
- real-demo: ảnh/video đại diện môi trường demo;
- edge-cases: no-plate, blur, tối, nghiêng, nhiều xe.

Không commit dataset nhạy cảm vào repository. Benchmark phải ghi dataset version hoặc fingerprint.

### Chỉ số detector

- detection success rate;
- bbox IoU nếu có ground truth;
- false positive rate;
- no-plate false positive;
- detector confidence distribution;
- p50/p95 latency.

### Chỉ số OCR

- exact plate match;
- character-level accuracy;
- normalized plate accuracy;
- no-result rate;
- low-confidence rate;
- OCR p50/p95 latency.

### Chỉ số end-to-end

- full pipeline p50/p95;
- cold vs warm latency;
- time-to-stable;
- OCR calls per vehicle;
- candidate flip rate;
- false check-in prevention;
- provider error rate;
- model readiness time.

Mục tiêu ban đầu để xác nhận bằng máy demo:

- warm preview p95 dưới 1 giây;
- stable candidate trong 1–2 giây khi biển rõ;
- không quá 2 OCR call/giây/lane;
- consensus giảm candidate flip;
- mock mode không phụ thuộc model;
- real mode có error rõ ràng khi thiếu model/OCR.

Các mục tiêu này là target để benchmark, chưa phải cam kết accuracy trước khi có số liệu.

## 9. Test plan cho role AI

### Unit tests

- normalize plate;
- crop margin;
- bbox clamp;
- quality score;
- confidence aggregation;
- threshold;
- readiness state;
- manifest/checksum;
- temporal consensus;
- cooldown/rate limit.

### Contract tests

- success;
- no-plate;
- low-confidence;
- low-quality;
- model missing;
- manifest invalid;
- checksum mismatch;
- OCR disabled;
- OCR timeout;
- detector exception;
- malformed image.

### Integration tests

- provider real với fixture nhỏ;
- mock provider giữ API không đổi;
- backend gọi provider và nhận đúng schema;
- provider version xuất hiện trong response;
- processing time luôn có;
- CI chạy được không cần GPU/model thật.

### Performance tests

- cold start;
- warm inference;
- nhiều request tuần tự;
- request trùng cùng lane;
- timeout;
- crop/OCR rate limit;
- memory sau nhiều frame.

## 10. Handoff cho các role khác

### Handoff cho Backend

Role AI cung cấp response schema, error code, readiness shape, confidence semantics, model version, provider config, mock fixture và benchmark sample.

Backend chịu trách nhiệm parking transaction, confirm, idempotency nghiệp vụ, duplicate active plate, auth và audit.

### Handoff cho Station Frontend

Role AI cung cấp bbox coordinate convention, normalized plate, confidence fields, requires_confirmation, provider status, processing time và retryable/non-retryable errors.

Frontend chịu trách nhiệm frame sampling, overlay, temporal UI state, confirm/edit/manual fallback và chống double-submit.

### Handoff cho DevOps/CI

Role AI cung cấp Docker dependency, environment variables, model mount/path, manifest/checksum, real-mode smoke command, mock-mode CI command và model distribution policy.

## 11. Release gate của role AI

Role AI được xem là hoàn thành Phase 2 khi:

- detector thật chạy qua runtime boundary hiện tại;
- OCR baseline chạy được hoặc có quyết định rõ ràng về lý do tạm tắt;
- readiness phân biệt được model/OCR/dependency lỗi;
- response có detector/OCR/combined confidence;
- crop quality gate hoạt động;
- contract tests đạt;
- benchmark có dataset split và report;
- cold/warm latency đã đo;
- real mode và mock mode đều chạy;
- CI không cần model asset nhạy cảm;
- README/runbook đủ để thành viên khác chạy;
- backend/frontend nhận được contract và fixture;
- không còn Critical/High AI blocker.

## 12. Checklist cần review

- [ ] Role AI chỉ sở hữu provider, OCR, benchmark, asset và handoff?
- [ ] Dùng PaddleOCR pretrained trước, chưa train OCR ngay?
- [ ] Có cần giữ best.pt trong Git hay chuyển sang artifact?
- [ ] Chấp nhận preview 2 FPS và OCR tối đa 2 lần/giây/lane?
- [ ] Chấp nhận consensus 2/3 candidate?
- [ ] Dùng detector/OCR/combined confidence riêng?
- [ ] Preview không persist ảnh và không tạo transaction?
- [ ] Real provider bắt buộc có warmup/readiness?
- [ ] CI chỉ chạy mock/contract, real benchmark chạy riêng?
- [ ] Threshold sẽ chốt theo benchmark validation thay vì đoán trước?
- [ ] Phase 2 chỉ hỗ trợ một vehicle/lane active tại một thời điểm?
- [ ] Có bắt buộc manual confirmation khi low confidence?

## 13. Kết luận

Thứ tự đúng cho role AI là:

1. Ổn định detector provider và model asset.
2. Thêm OCR pretrained.
3. Thêm crop quality gate và normalization.
4. Thêm temporal consensus/rate limit.
5. Benchmark trên dữ liệu đại diện.
6. Bàn giao contract cho backend/frontend.
7. Chỉ sau khi benchmark không đạt mới quyết định fine-tune OCR hoặc detector.

