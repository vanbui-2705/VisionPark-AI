# VisionPark — Phase 2 Linear Backlog

> Phạm vi: Real ALPR tùy chọn + luồng check-in xe vào bãi cho team 5 người.
>
> Thời lượng đề xuất: 3 tuần / 15 ngày làm việc.
>
> Quy ước: `P0` = bắt buộc để chạy phase, `P1` = bắt buộc để demo, `P2` = hoàn thiện sau demo.

## 1. Mục tiêu Phase 2

```text
Frame từ Station
    -> ALPR provider
    -> Operator xem và xác nhận/sửa biển số
    -> Check-in API
    -> Transaction PARKED
    -> History và audit
```

### Trong phạm vi

- Real ALPR provider chạy qua runtime boundary hiện có.
- Model manifest, readiness và benchmark.
- Check-in cho lane `IN` đang active.
- Manual confirmation khi confidence thấp hoặc không có biển số.
- Chống transaction trùng và idempotency.
- Lịch sử check-in và audit.
- Station UI, Operations UI, CI và E2E test.

### Ngoài phạm vi

- Check-out, tính phí, vé tháng, payment, VietQR.
- Barrier thật, camera RTSP và thiết bị I/O.
- CRM, vehicle CRM, slot map.
- Redis, WebSocket và production MLOps.
- Commit model weight hoặc dữ liệu biển số thật vào Git.

## 2. Team và ownership

| Linear owner | Vai trò | Ownership chính |
|---|---|---|
| Member 1 | AI Lead / PM / DevOps / QA | ALPR provider, benchmark, CI, integration, release gate |
| Member 2 | Backend Core | Database, migration, transaction model, idempotency infrastructure |
| Member 3 | Backend Domain | Check-in service/API, business rules, duplicate, audit, history |
| Member 4 | Station Frontend | Capture, ALPR result, confirm/edit, manual fallback, check-in state |
| Member 5 | Operations Frontend | API types/client, history/filter, permissions, audit UI |

Mỗi issue nên có:

- Assignee đúng owner bên trên.
- Label `phase-2` và label theo nhóm: `ai`, `backend-core`, `backend-domain`, `station`, `operations`, `qa`.
- Link tới issue dependency nếu có.
- Test/evidence trong phần mô tả trước khi chuyển `Done`.

## 3. Milestones / Sprints

| Milestone | Thời gian | Kết quả cần đạt |
|---|---:|---|
| M0 — Contract & Gate | Ngày 1–2 | Phase 1 gate pass, contract check-in chốt |
| M1 — Backend & AI foundation | Ngày 3–5 | Migration, API skeleton, provider skeleton, fixtures |
| M2 — Vertical slice | Ngày 6–10 | Station → API → `PARKED` → history chạy bằng mock |
| M3 — Real provider & hardening | Ngày 11–15 | Benchmark, real provider test, CI/E2E, demo pass |

## 4. Backlog tổng hợp

### M0 — Contract và Phase 1 gate

| ID | Task | Owner | Priority | Est. | Dependency | Acceptance criteria |
|---|---|---|---|---:|---|---|
| P2-001 | Chạy Phase 1 clean-install/CI gate | Member 1 | P0 | 1d | — | CI xanh; có danh sách blocker Critical/High |
| P2-002 | Chốt check-in API contract và error contract | Member 1 | P0 | 0.5d | P2-001 | OpenAPI/schema có request, response, duplicate, idempotency, manual confirmation |
| P2-003 | Review contract backend/domain/frontend | Members 2–5 | P0 | 0.5d | P2-002 | Cả 5 người xác nhận schema; không còn field chưa rõ |
| P2-004 | Chốt dataset/model/benchmark policy | Member 1 | P0 | 0.5d | P2-001 | Có manifest format, model path, version, checksum và quy tắc không commit weight |
| P2-005 | Tạo fixtures chung | Members 2–5 | P1 | 0.5d | P2-002 | Có fixture plate hợp lệ, no-plate, confidence thấp, lane IN |

### M1 — Real ALPR provider — Member 1

| ID | Task | Owner | Priority | Est. | Dependency | Acceptance criteria |
|---|---|---|---|---:|---|---|
| P2-AI-001 | Tạo config chọn `mock` hoặc `real` provider | Member 1 | P0 | 0.5d | P2-002 | Caller không đổi; mock vẫn là default |
| P2-AI-002 | Tạo model manifest và readiness check | Member 1 | P0 | 1d | P2-AI-001 | Thiếu/sai model trả `not_ready`; model hợp lệ trả đúng version |
| P2-AI-003 | Kết nối detector/OCR baseline thật | Member 1 | P1 | 2d | P2-AI-002 | Real provider trả plate, bbox, confidence, latency, model version |
| P2-AI-004 | Viết provider contract tests | Member 1 | P0 | 1d | P2-AI-001 | Test success, no-plate, low-confidence, missing model, inference error |
| P2-AI-005 | Tạo benchmark script/report | Member 1 | P1 | 1d | P2-AI-003 | Report có dataset/model version, sample count, detection/OCR và latency |

### M1 — Backend Core — Member 2

| ID | Task | Owner | Priority | Est. | Dependency | Acceptance criteria |
|---|---|---|---|---:|---|---|
| P2-BC-001 | Thiết kế parking transaction schema | Member 2 | P0 | 1d | P2-002 | Có trạng thái `PARKED`, lane, plate, timestamps, detection link |
| P2-BC-002 | Tạo Alembic migration additive | Member 2 | P0 | 1d | P2-BC-001 | Upgrade/downgrade pass; không mất dữ liệu Phase 1 |
| P2-BC-003 | Tạo idempotency key/fingerprint storage | Member 2 | P0 | 1d | P2-BC-001 | Cùng key/payload trả cùng result; payload khác trả conflict |
| P2-BC-004 | Gắn auth, DB session, error/correlation contract | Member 2 | P0 | 0.5d | P2-BC-001 | Endpoint dùng dependency chung, không tạo engine/session riêng |
| P2-BC-005 | Seed lane IN và DB test fixtures | Member 2 | P1 | 0.5d | P2-BC-002 | DB rỗng bootstrap được và có lane IN test |

### M1/M2 — Backend Domain — Member 3

| ID | Task | Owner | Priority | Est. | Dependency | Acceptance criteria |
|---|---|---|---|---:|---|---|
| P2-BD-001 | Tạo check-in request/response schema | Member 3 | P0 | 0.5d | P2-002 | Schema hỗ trợ ALPR result, manual plate, confirmation và idempotency |
| P2-BD-002 | Implement check-in application service | Member 3 | P0 | 1.5d | P2-BC-001, P2-BD-001 | Request hợp lệ tạo transaction `PARKED` |
| P2-BD-003 | Validate auth, lane IN active và plate | Member 3 | P0 | 1d | P2-BD-002 | Unauthorized/inactive lane/empty plate bị từ chối đúng contract |
| P2-BD-004 | Implement duplicate protection | Member 3 | P0 | 1d | P2-BC-003, P2-BD-002 | Plate đang `PARKED` không tạo transaction thứ hai |
| P2-BD-005 | Implement audit và history endpoint | Member 3 | P1 | 1d | P2-BD-002 | Lưu actor, AI plate, final plate, source, lane, timestamp; có filter |
| P2-BD-006 | Viết unit/integration tests domain | Member 3 | P0 | 1d | P2-BD-002–005 | Pass happy path, manual fallback, duplicate, retry, role và lane errors |

### M2 — Station Frontend — Member 4

| ID | Task | Owner | Priority | Est. | Dependency | Acceptance criteria |
|---|---|---|---|---:|---|---|
| P2-ST-001 | Tích hợp Station với check-in contract | Member 4 | P0 | 1d | P2-002 | Station gọi đúng API client hiện có |
| P2-ST-002 | Hiển thị ALPR result và confidence state | Member 4 | P1 | 1d | P2-ST-001 | Hiển thị plate, bbox, confidence, latency, model version |
| P2-ST-003 | Implement confirm/edit/manual fallback | Member 4 | P0 | 1.5d | P2-ST-002 | Low-confidence/no-plate bắt buộc nhập hoặc sửa trước khi submit |
| P2-ST-004 | Implement loading/success/error/retry states | Member 4 | P1 | 1d | P2-ST-001 | Xử lý 503, duplicate, timeout, network error không mất session |
| P2-ST-005 | Viết Station integration tests | Member 4 | P1 | 1d | P2-ST-003, P2-ST-004 | Test success, no-plate, edit plate và check-in failure |

### M2 — Operations Frontend — Member 5

| ID | Task | Owner | Priority | Est. | Dependency | Acceptance criteria |
|---|---|---|---|---:|---|---|
| P2-OP-001 | Cập nhật API client/types | Member 5 | P0 | 1d | P2-002 | Có types cho check-in, history, audit, typed errors |
| P2-OP-002 | Tạo history list và filters | Member 5 | P1 | 1.5d | P2-BD-005, P2-OP-001 | Filter được plate, lane, time range, status |
| P2-OP-003 | Áp dụng quyền Operator/Admin | Member 5 | P0 | 0.5d | P2-OP-001 | UI không hiển thị thao tác trái quyền; backend vẫn enforce |
| P2-OP-004 | Hiển thị audit details | Member 5 | P1 | 0.5d | P2-BD-005, P2-OP-002 | Hiển thị AI plate/final plate, actor, source, timestamp |
| P2-OP-005 | Viết Operations UI tests | Member 5 | P1 | 1d | P2-OP-002–004 | Test filter, permission, empty state và error state |

### M3 — Integration, CI và release

| ID | Task | Owner | Priority | Est. | Dependency | Acceptance criteria |
|---|---|---|---|---:|---|---|
| P2-QA-001 | Ghép mock vertical slice end-to-end | Member 1 + cả đội | P0 | 1d | P2-BD-006, P2-ST-005, P2-OP-005 | Station frame → ALPR → confirm/edit → `PARKED` → history/audit |
| P2-QA-002 | Test real provider trên môi trường có model | Member 1 + Members 2–3 | P1 | 1d | P2-AI-003, P2-QA-001 | Readiness, inference, benchmark và rollback về mock đều pass |
| P2-QA-003 | Cập nhật CI checks | Member 1 | P0 | 0.5d | P2-QA-001 | Backend/frontend tests, migration checks, mock E2E pass không cần GPU |
| P2-QA-004 | Regression và security/role checks | Cả đội | P0 | 1d | P2-QA-001 | Không còn lỗi Critical/High; role, duplicate race, idempotency pass |
| P2-QA-005 | Clean setup trên DB rỗng | Member 2 + Member 1 | P0 | 0.5d | P2-BC-002, P2-BC-005 | Bootstrap/migration/seed chạy thành công từ clean checkout |
| P2-QA-006 | QA report, benchmark report và demo evidence | Member 1 | P1 | 1d | P2-QA-002–005 | Có report, screenshot/video, README và acceptance checklist |

## 5. Dependency chính

```text
P2-001 Phase 1 gate
    -> P2-002 Contract
        -> P2-BC-001/002/003 Backend persistence
            -> P2-BD-002/003/004/005 Check-in API
                -> P2-ST-001/002/003 Station UI
                -> P2-OP-001/002/003 Operations UI
                    -> P2-QA-001 Mock E2E
                        -> P2-QA-003/004/005/006 Release gate

P2-004 Model policy
    -> P2-AI-001/002/003 Real provider
        -> P2-AI-004/005 Tests and benchmark
            -> P2-QA-002 Real-provider verification
```

## 6. Definition of Done cho mỗi issue

- Code nằm đúng ownership/module.
- Có test cho happy path và lỗi chính.
- Lint, test và build pass.
- Có migration nếu thay đổi schema.
- Không commit secret, model weight hoặc dữ liệu thật.
- PR có link Linear issue, dependency và evidence.
- Ít nhất một thành viên khác review trước khi merge.

## 7. Phase 2 Exit Criteria

- [ ] CI backend/frontend xanh.
- [ ] Clean checkout chạy được migration, seed và test.
- [ ] Real provider chạy được ngoài CI với manifest hợp lệ.
- [ ] Mock provider vẫn là default cho CI/local không có model.
- [ ] Operator tạo được check-in `PARKED` qua Station.
- [ ] Low-confidence/no-plate có manual fallback.
- [ ] Duplicate plate bị từ chối.
- [ ] Retry cùng idempotency key không tạo transaction thứ hai.
- [ ] History và audit hiển thị đúng.
- [ ] Không còn lỗi Critical/High.
- [ ] Có benchmark report và demo evidence.

## 8. Suggested Linear setup

- **Project:** `VisionPark Phase 2 — ALPR & Check-in`
- **Milestones:** `M0 Contract`, `M1 Foundation`, `M2 Vertical Slice`, `M3 Release`
- **Labels:** `phase-2`, `ai`, `backend-core`, `backend-domain`, `station`, `operations`, `qa`
- **Statuses:** `Backlog → Todo → In Progress → In Review → QA → Done`
- **Priority:** Dùng `P0/P1/P2` theo bảng backlog.
- **Issue title format:** `[P2-AI-001] Tạo config chọn mock/real provider`
