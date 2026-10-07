# Phase 2 evidence (2026-10-07)

Current evidence: [completion report](../real-data-completion-report-2026-10-07.md),
[real vehicle benchmark](completion-user-video-benchmark.json),
[Chrome image/video](completion-browser.json), [Docker lifecycle](completion-lifecycle-final.json).

## Historical mock/synthetic contract checks

Browser smoke uses a synthetic gray MP4 with backend mock ALPR and real PostgreSQL.
It does not demonstrate recognition accuracy on real vehicles. QA records/images
are removed after verification; screenshots contain only synthetic QA plates.

- [x] Operator login, lane IN selection and two preview captures with consensus.
- [x] Preview creates no persisted detections or parking transactions.
- [x] Corrected plate creates PARKED through canonical confirmation.
- [x] Idempotency replay returns the same transaction.
- [x] Duplicate PARKED returns HTTP 409.
- [x] Manual entry succeeds through parking API after an injected ALPR 503.
- [x] Admin users/roles và Operator RBAC; detection detail tải ảnh thật từ media endpoint.
- [x] No browser page errors; disposable QA records removed.
- [ ] Low-confidence and no-plate screenshot/video coverage.
- [ ] Real vehicle demo/benchmark on labelled images and CPU cold/warm measurements.

[Sanitized browser report](browser-smoke.json), [preview](mock-preview.png),
[corrected check-in](mock-corrected-checkin.png), [duplicate](mock-duplicate.png),
[manual fallback](manual-provider-failure.png).

The mock flow above is historical; the current application supports only real providers.
Use the [current runbook](../real-data-runbook.md) and real-data scripts.


## Real provider activation

Docker đã bật YOLO + PaddleOCR trên CPU qua `deployment/compose.real.yml`.
[API/OCR sanity report](real-provider-smoke.json): readiness real, blank frame trả
no-plate, OCR model đọc rendered text `30F12345`. [Video capture report](real-video-smoke.json)
và [Station screenshot](real-video-preview.png): frame từ gray MP4 gọi provider
ultralytics-paddleocr, không hiện MOCK ALPR, không persist, 0 browser errors.
Đây là synthetic sanity check, chưa phải benchmark/video xe thật.
