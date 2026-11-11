# Phase 2 ALPR release report — 2026-10-09

## Decision

- **Functional acceptance: PASS.** Luồng real-provider từ image/video preview đến
  correction/manual entry, persistence, duplicate protection, idempotency và audit đã chạy
  được, có evidence truy vết và gate chạy lại độc lập.
- **Recognition-quality release: HOLD.** Validation exact match 25% và demo exact match 0%,
  thấp hơn release floor 80%. Trạng thái này không chặn nghiệm thu chức năng, nhưng chặn phát
  hành model như một hệ thống nhận dạng tự động đạt chất lượng.

## Traceability

- Base commit: `58a82a997bb383c7f1bfeefcb03ff4cc07060ea3` (working tree chưa commit).
- Model artifact: `ultralytics-8.4.165-yolo26n-plate-v1`.
- Detector SHA-256: `C7DBC04262278ED3A422A891E8003DFEA7935C90B8A749DF29539C9FBBA2B999`.
- Dataset manifest: `backend/datasets/phase2-release.json`.
- Dataset fingerprint: `437bb9dd3e7fb7db0acaff414d151117ac5b14067c3511c9298b02c6db266be6`.
- Evidence index: `docs/phase-2-evidence/evidence-index.json`.
- Benchmark runtime: Windows CPU, Ultralytics 8.4.47, PaddleOCR 3.7.0,
  PaddlePaddle 3.3.1. Docker image inspection reports Ultralytics 8.4.174.

## Checks

| Check | Result |
|---|---|
| `py -3 -m pytest tests -q` | PASS — 177 collected, 174 passed, 3 skipped |
| `py -3 -m ruff check app scripts tests` | PASS |
| `npm test -- --run` | PASS — 19 files, 72 tests |
| `npm run lint` | PASS — exit 0, existing React warnings only |
| `npm run build` | PASS |
| Dataset provision/hash verification | PASS — 12 Commons assets |
| Release manifest validation | PASS — 4 splits, 15 cases, 8 required scenarios |
| Docker real-provider startup/readiness/inference/persistence | PASS — `completion-lifecycle-final.json` |
| Image/video vertical slice and duplicate | PASS — `completion-browser.json` |
| Real low-confidence correction and no-plate manual fallback | PASS — `real-ai-edge-browser.json` |
| Retry/idempotency | PASS — `completion-persistence.json` |
| `py -3 scripts/release_gate.py --functional-only --skip-tests` | PASS — functional acceptance |
| `py -3 scripts/release_gate.py --skip-tests` | FAIL — recognition quality gate |

No Critical/High code or evidence-integrity defect was found. The recognition quality result
blocks the model-quality release only; the implemented operator workflow is functionally
accepted.

## Dataset and benchmark

The tracked manifest contains one frame per vehicle from the user video and twelve distinct,
licensed Wikimedia Commons photographs. Cases are grouped by source video/vehicle, hashes are
verified before inference, and no generated blur/dark/rotation is used.

| Split | Cases | Exact match | Character accuracy | False positive | Full p95 |
|---|---:|---:|---:|---:|---:|
| smoke | 3 | 50% | 93.75% | 0% | 198.778 ms |
| validation | 4 | 25% | 83.93% | 0% | 326.419 ms |
| demo | 4 | 0% | 38.54% | 0% | 337.212 ms |
| edge_cases | 4 | N/A (all null labels) | 100% null handling | 0% | 306.022 ms |

The working tree now accepts near-square two-row crops and runs recognition on the top and
bottom rows separately. This raised validation character accuracy from 62.05% to 83.93% and
demo character accuracy from 0% to 38.54%, while exact-match rates remained 25% and 0%.

The four natural edge cases cover dark, motion blur, small/partial plate and a negative side
view. All returned no result, which is the expected safe behavior. On positive independent
vehicle scenes, the detector/OCR pipeline missed or rejected most plates. Operator correction
works, but it cannot compensate for a demo split with zero automatic reads.

## Remaining AI work

1. Diagnose remaining detector misses on full-vehicle inputs and OCR character errors after
   the two-row crop/OCR fix included in this working tree.
2. Improve or replace the detector/OCR artifact without weakening the safe confirmation path.
3. Re-run all four reports with the same dataset fingerprint and achieve at least 80% exact
   match on both validation and demo, zero provider errors, zero edge-case false positives,
   and full-pipeline p95 at or below 1 second.
4. Re-run Docker/browser evidence if the model artifact or preprocessing changes, then run
   `py -3 scripts/release_gate.py --skip-tests` and the full quality suite.

Public evaluation assets can be restored with
`py -3 scripts/provision_phase2_release_dataset.py`; user-provided smoke frames stay local and
are verified by SHA-256. Functional Phase 2 is PASS; recognition-quality release moves from
HOLD to PASS only after the strict gate passes.
