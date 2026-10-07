# Bàn giao hoàn thiện dữ liệu thật — 07/10/2026

Ứng dụng hiện chạy tại http://localhost:5174, backend http://localhost:8002.
YOLO và PaddleOCR thật đã sẵn sàng; không còn provider mock hoặc fixture fallback
trong ứng dụng. Test doubles chỉ nằm trong tests, không đóng gói vào backend runtime.
OpenSpec `complete-real-data-system` còn mở gate 7.8 về chất lượng tổng thể.

## Chức năng đã thực hiện và kiểm tra

| Chức năng | Hành vi hiện tại | Kiểm chứng |
|---|---|---|
| Station ảnh JPEG/PNG | Upload, nhận diện thật, xem bbox/confidence/quality, xác nhận hoặc sửa biển, check-in | Browser với ảnh xe thật; PNG/type/size/metadata integration tests |
| Station video MP4 local | Play/pause/capture, sampling giới hạn, consensus, xác nhận check-in | Chrome phát video người dùng; capture ở giây 90, đọc `30V4495` |
| Đổi ảnh/video/làn | Reset candidate, bỏ response cũ, giải phóng object URL | Browser đổi mode khi request pending; frontend tests |
| Preview và lưu kết quả | Preview không ghi từng frame; final lưu ảnh và detection, lưu riêng trên ALPR Test không tự check-in | Integration tests và database trên môi trường restore |
| Check-in và nhập tay | Transaction/audit nguyên tử, chống trùng xe đang PARKED, retry idempotent; nguồn AI/sửa tay/manual theo dữ liệu thật | SQLite/PostgreSQL integration tests; duplicate trên browser |
| Detection metadata | OCR gốc/chuẩn hóa, confidence thành phần, model/latency, actor, lane snapshot, loại ảnh/video và thời điểm frame | Migration additive và integration tests; bản ghi cũ giữ unknown |
| Lịch sử/audit/dashboard | Phân trang/lọc ở server, totals từ database, tìm qua trang đầu, context lịch sử giữ khi đổi tên làn | Kiểm tra DB riêng trên 200 bản ghi; migration và snapshot tests |
| Tài khoản/quyền | Quản trị users/roles/lanes, profile/email, đổi mật khẩu, thu hồi phiên/Force Logout, bốn role theo policy | Auth/RBAC và token revocation tests |
| Preferences | Theme sáng/tối, vi/en, database là nguồn lưu; localStorage chỉ cache | Backend/frontend tests; reload/persistence trên môi trường restore |
| Notifications/Error Center | Sự kiện thật lưu DB, quyền người nhận/read state, sanitize/rate limit/correlation, chống lặp và flood preview | Backend tests, smoke và lifecycle hashes |
| Docker/backup | Volumes cố định, seed mặc định tắt, backup DB+media, restore cô lập, kiểm tra checksum | Restore độc lập và lifecycle matrix |

Các trang ACCOUNTANT/TECHNICIAN giữ quyền hiện có; chưa bổ sung nghiệp vụ kế toán
hoặc thiết bị. Check-out, tính phí/thanh toán, vé tháng, camera RTSP, barrier và nhận
diện cháy chưa được xây dựng trong đợt này. Bộ lọc dropdown lịch sử hiện lấy các làn
active; API vẫn hỗ trợ lọc ID làn cũ. Không có retention tự xóa dữ liệu.

## Thay đổi xử lý các vấn đề thực tế

- Xóa FakeALPRRuntime, ONNX placeholder, mock API frontend và endpoint/repository cũ.
- Warmup có chạy inference thật trước readiness; inference chạy trong thread để
  không chặn health endpoint. Model thiếu/hỏng trả lỗi, không tạo kết quả giả.
- Tăng timeout riêng ALPR lên 60 giây sau khi thấy request inference vượt 15 giây;
  timeout API thông thường vẫn là 15 giây. UI hiển thị lỗi codec video rõ ràng.
- Ghi ảnh nguyên tử, cleanup khi DB lỗi; lưu content type/bytes, actor và capture
  metadata; chống retry tạo detection trùng. Manual không thể giả nguồn AI/confidence.
- Migration 0007–0010 bổ sung confirmation/email/workflows/context; không reset
  tài khoản hay gán nguồn tùy ý cho dữ liệu lịch sử.
- Điều chỉnh Dockerfile cache dependency để thay code không cài lại bộ AI nặng.
- Bootstrap admin chỉ khi được bật và có mật khẩu ít nhất tám ký tự; không seed
  làn/operator/giao dịch mẫu, không đổi mật khẩu tài khoản đang tồn tại.

## Kết quả kiểm tra

- Backend regression: **151 passed, 3 skipped**; các test race dành cho PostgreSQL
  bỏ qua khi chạy SQLite. Có chạy nhóm kiểm tra PostgreSQL trên DB restore riêng.
- Sau các sửa cuối: **26 passed** cho ALPR/Station/complete workflows; **16 passed**
  cho cấu hình; ruff pass. Các nhóm này có test trùng regression, không cộng dồn.
- Frontend: **43 passed / 14 files**, build pass, lint không có error; còn cảnh báo
  React của lint. OpenSpec strict validation và `git diff --check` pass.
- E2E Chrome: ảnh xe thật → nhận diện → confirm → lịch sử; video MP4 thật →
  capture → nhận diện → confirm → lịch sử; đổi mode bỏ response pending, duplicate
  ảnh được từ chối. Chạy trên database cô lập, không đưa giao dịch QA vào DB vận hành.
- Persistence matrix so toàn bộ row hashes và media hashes: restart, down/up
  không xóa volume, rebuild + force-recreate đều pass, gồm bản ghi từ ảnh/video thật,
  preferences, trạng thái đọc notification và error events.

## Nhận diện trên video người dùng

Nguồn là file `YTSave_YouTube_Media_dxJC4GXu4mc_Mì-AI-Demo-hệ-thống-nhận-diện-biển-số-xe-miLPR_001_1080p.mp4`
trong Downloads, dài 139,17 giây, 1728×1080, 30 fps. Ground truth đối chiếu biển
vật lý trên xe: `29A90101` và `30V4495`, không dùng chữ kết quả overlay làm nhãn.
Dữ liệu dùng đánh giá nội bộ; không train hay đổi weights.

| Chỉ số lần đo gần nhất | Kết quả |
|---|---:|
| Ảnh có biển đọc đúng toàn bộ | 8/10 (80%) |
| Character accuracy | 97,5% |
| Negative title frame | 1/1 không tạo biển giả |
| Provider errors | 0/11 |
| Warm full pipeline p50 / p95 | 1,30 / 3,03 giây |
| Cold inference | 36,86 giây |
| Processing time tới candidate stable | Khoảng 2,05 giây |
| Candidate flip rate | 25% |

Hai lỗi Toyota là `29A9001` và `29490101`. Chỉ có hai xe trong một video demo có
overlay; các frame gần nhau không độc lập. Một negative không đủ để suy ra tỷ lệ
false positive tổng quát. Đây chưa phải validation set đa cảnh; kết quả đo CPU có
tải dịch vụ chung và chưa đạt warm p95 dưới một giây. Gate 7.8 và Phase 2 release
chất lượng vẫn mở; operator tiếp tục kiểm tra/xác nhận, không tự động thông xe.
Cần thêm ảnh/video nhiều xe, ban đêm, mờ/chói và negative có nhãn, chia theo xe/video,
cùng ngưỡng accuracy được chốt trước khi đóng gate.

## Bảo toàn dữ liệu và backup

- Volumes vận hành vẫn là `visionpark_postgres_data`, `visionpark_media_data`.
- Sáu bảng nghiệp vụ gốc và bốn ảnh giữ nguyên hashes; migration head hiện tại
  `20261007_0010`. Không xóa hay phân loại lại các bản ghi cũ chưa rõ provenance.
- Backup trước nâng cấp: `E:\BE_AI\VisionPark-backups\20261007-verified`,
  restore độc lập đối chiếu đủ 7 bảng/4 ảnh.
- Backup sau nâng cấp: `E:\BE_AI\VisionPark-backups\20261007-after-real-completion`,
  restore vào `visionpark-restore-postupgrade`, đủ 10 bảng/4 ảnh khớp hashes.
- Baseline riêng: `E:\BE_AI\VisionPark-backups\20261007-operational-upgrade.json`.
- Không dùng `docker compose down -v` hoặc prune volumes. Các lần rebuild/restart
  giữ volume đã được kiểm chứng; thao tác chủ động xóa volume vẫn xóa dữ liệu.

Hướng dẫn thao tác: [real-data-runbook.md](real-data-runbook.md).

## Evidence

- [Benchmark thật](phase-2-evidence/completion-user-video-benchmark.json)
- [Browser E2E](phase-2-evidence/completion-browser.json),
  [ảnh Station](phase-2-evidence/completion-image-station.png),
  [video Station](phase-2-evidence/completion-video-station.png)
- [Lifecycle hashes](phase-2-evidence/completion-lifecycle-final.json)
- [Upgrade preservation](phase-2-evidence/completion-operational-upgrade.json)
- [Migration preservation](phase-2-evidence/completion-migration-preservation.json)

Evidence mock/synthetic cũ chỉ lưu lịch sử kiểm tra contract, không dùng để chứng
minh nhận diện xe thật. Các môi trường `visionpark-restore-*`/`visionpark-completion`
và volumes test tách biệt còn được giữ để xem lại bằng chứng.

## File thay đổi

Danh sách dưới là toàn bộ worktree tích lũy của đợt hoàn thiện, gồm sửa từ trước
lần tiếp tục này. `M` sửa, `A` mới, `D` xóa; không bao gồm secrets, model cache,
file tạm hoặc dữ liệu QA. Các file trọng tâm: provider/config/main, ALPR recorder/
storage, operations/auth/check-in, migrations, Station/API/history/profile/settings,
Compose/Dockerfile và scripts backup/benchmark/persistence.

### Root

```text
M README.md
M docker-compose.yml
M env.example
```

### backend

```text
M backend/.dockerignore
M backend/.env.example
M backend/Dockerfile
M backend/README.md
D backend/app/alpr/onnx_provider.py
M backend/app/alpr/ports/detection_recorder.py
M backend/app/alpr/pt_provider.py
M backend/app/alpr/runtime_adapter.py
M backend/app/alpr/schema.py
M backend/app/alpr/service.py
D backend/app/api/endpoints/alpr.py
M backend/app/api/router.py
M backend/app/api/v1/endpoints/alpr.py
M backend/app/api/v1/endpoints/audit_logs.py
D backend/app/api/v1/endpoints/checkin.py
M backend/app/api/v1/endpoints/parking.py
M backend/app/api/v1/router.py
M backend/app/core/config.py
M backend/app/core/errors.py
M backend/app/core/security.py
M backend/app/database/bootstrap.py
M backend/app/database/models.py
M backend/app/database/seed.py
M backend/app/integrations/persistence/detection_recorder_impl.py
M backend/app/integrations/storage/local_storage.py
M backend/app/main.py
M backend/app/modules/alpr/models.py
M backend/app/modules/alpr/schemas.py
M backend/app/modules/audit_logs/service.py
M backend/app/modules/auth/dependencies.py
M backend/app/modules/auth/router.py
M backend/app/modules/auth/service.py
M backend/app/modules/checkin/models.py
M backend/app/modules/checkin/repository.py
M backend/app/modules/checkin/service.py
M backend/app/modules/users/models.py
M backend/app/modules/users/repository.py
M backend/app/modules/users/schemas.py
M backend/app/modules/users/service.py
M backend/pyproject.toml
M backend/scripts/benchmark_alpr.py
M backend/tests/conftest.py
M backend/tests/integration/test_backend_core_phase2.py
M backend/tests/integration/test_health.py
M backend/tests/integration/test_migrations.py
M backend/tests/test_alpr.py
D backend/tests/unit/alpr/test_api.py
D backend/tests/unit/alpr/test_onnx_provider.py
M backend/tests/unit/alpr/test_runtime_adapter.py
M backend/tests/unit/core/test_config.py
A backend/alembic/versions/20261007_0007_detection_confirmation_metadata.py
A backend/alembic/versions/20261007_0008_user_email.py
A backend/alembic/versions/20261007_0009_complete_real_workflows.py
A backend/alembic/versions/20261007_0010_transaction_context.py
A backend/app/modules/alpr/confirmation.py
A backend/app/modules/operations/__init__.py
A backend/app/modules/operations/models.py
A backend/app/modules/operations/router.py
A backend/app/modules/operations/service.py
A backend/app/modules/users/router.py
A backend/scripts/audit_media.py
A backend/scripts/browser_completion.py
A backend/scripts/data_backup.py
A backend/scripts/provision_real_docker.py
A backend/scripts/smoke_completion.py
A backend/scripts/smoke_real_alpr.py
A backend/scripts/smoke_station_e2e.py
A backend/scripts/verify_lifecycle.py
A backend/scripts/verify_upgrade.py
A backend/tests/alpr_double.py
A backend/tests/integration/test_complete_workflows.py
A backend/tests/integration/test_station_contract.py
A backend/tests/integration/test_users_api.py
```

### docs

```text
M docs/phase-2-evidence/README.md
M docs/phase-2-runbook.md
A docs/integration-verification-2026-10-07.md
A docs/phase-2-evidence/browser-smoke.json
A docs/phase-2-evidence/completion-browser.json
A docs/phase-2-evidence/completion-image-station.png
A docs/phase-2-evidence/completion-lifecycle-final.json
A docs/phase-2-evidence/completion-migration-preservation.json
A docs/phase-2-evidence/completion-operational-upgrade.json
A docs/phase-2-evidence/completion-persistence.json
A docs/phase-2-evidence/completion-user-video-benchmark.json
A docs/phase-2-evidence/completion-video-station.png
A docs/phase-2-evidence/manual-provider-failure.png
A docs/phase-2-evidence/mock-corrected-checkin.png
A docs/phase-2-evidence/mock-duplicate.png
A docs/phase-2-evidence/mock-preview.png
A docs/phase-2-evidence/real-provider-smoke.json
A docs/phase-2-evidence/real-video-preview.png
A docs/phase-2-evidence/real-video-smoke.json
A docs/real-data-completion-report-2026-10-07.md
A docs/real-data-runbook.md
```

### frontend

```text
M frontend/.env.example
M frontend/AGENTS.md
M frontend/Dockerfile
D frontend/dev/mock-api.mjs
M frontend/docs/AI_CONTEXT.md
M frontend/docs/ALPR.md
M frontend/docs/API.md
M frontend/docs/ARCHITECTURE.md
M frontend/docs/AUTH.md
M frontend/docs/BACKEND.md
M frontend/docs/CONFIGURATION.md
M frontend/docs/DATABASE.md
M frontend/docs/DECISIONS.md
M frontend/docs/DEPLOYMENT.md
M frontend/docs/KNOWN_ISSUES.md
M frontend/docs/LANES.md
M frontend/docs/OVERVIEW.md
M frontend/docs/RBAC.md
M frontend/docs/ROUTES.md
M frontend/docs/STATION.md
M frontend/docs/USERS.md
M frontend/package.json
M frontend/src/App.tsx
M frontend/src/api/authApi.ts
M frontend/src/api/client.ts
M frontend/src/api/domain.ts
M frontend/src/api/healthApi.ts
M frontend/src/api/lanesApi.ts
D frontend/src/api/mocks/fixtures.ts
M frontend/src/api/services.ts
M frontend/src/api/types.ts
M frontend/src/app/router.tsx
M frontend/src/components/AppErrorBoundary.tsx
D frontend/src/components/MockProviderBanner.tsx
M frontend/src/components/Unauthorized.tsx
M frontend/src/components/ui/Breadcrumb.tsx
M frontend/src/components/ui/Button.tsx
M frontend/src/components/ui/Dialog.tsx
M frontend/src/components/ui/Drawer.tsx
M frontend/src/components/ui/Spinner.tsx
M frontend/src/components/ui/Toast.tsx
M frontend/src/index.css
M frontend/src/layouts/AdminLayout.tsx
M frontend/src/layouts/AppShell.tsx
M frontend/src/lib/errorLog.ts
M frontend/src/lib/notifications.ts
M frontend/src/lib/permissions.ts
M frontend/src/modules/alpr/AlprPage.tsx
M frontend/src/modules/alpr/AlprTestPage.tsx
M frontend/src/modules/audit/AuditLogsPage.tsx
M frontend/src/modules/auth/AuthContext.tsx
M frontend/src/modules/auth/LoginPage.tsx
M frontend/src/modules/auth/RegisterPage.tsx
M frontend/src/modules/auth/guards.tsx
M frontend/src/modules/dashboard/DashboardPage.tsx
M frontend/src/modules/detections/DetectionDetailPage.tsx
M frontend/src/modules/detections/DetectionHistoryPage.tsx
M frontend/src/modules/docs/DocsArticlePage.tsx
M frontend/src/modules/docs/DocsHomePage.tsx
M frontend/src/modules/docs/DocsLayout.tsx
M frontend/src/modules/error/ErrorPages.tsx
M frontend/src/modules/errors/ErrorCenterPage.tsx
M frontend/src/modules/help/HelpPage.tsx
M frontend/src/modules/lanes/LaneForm.tsx
M frontend/src/modules/lanes/LaneListPage.tsx
M frontend/src/modules/lanes/LanePages.tsx
M frontend/src/modules/notifications/NotificationsPage.tsx
M frontend/src/modules/parking/ParkingDetailPage.tsx
M frontend/src/modules/parking/ParkingHistoryPage.tsx
M frontend/src/modules/permissions/PermissionsPage.tsx
M frontend/src/modules/profile/ProfilePage.tsx
M frontend/src/modules/roles/RolesPage.tsx
M frontend/src/modules/settings/SettingsPage.tsx
M frontend/src/modules/station/StationPage.tsx
M frontend/src/modules/station/api.ts
M frontend/src/modules/station/components/ConfirmationPanel.tsx
M frontend/src/modules/station/components/ErrorPanel.tsx
M frontend/src/modules/station/components/LaneSelector.tsx
M frontend/src/modules/station/components/RecentHistory.tsx
M frontend/src/modules/station/components/ResultPanel.tsx
M frontend/src/modules/station/components/VideoPlayer.tsx
M frontend/src/modules/station/components/VideoSelector.tsx
M frontend/src/modules/station/hooks/useAlprDetection.ts
M frontend/src/modules/station/types.ts
M frontend/src/modules/system/SystemPage.tsx
M frontend/src/modules/uikit/UiKitPage.tsx
M frontend/src/modules/users/CreateUserPage.tsx
M frontend/src/modules/users/README.md
M frontend/src/modules/users/UserDetailPage.tsx
M frontend/src/modules/users/UserEditPage.tsx
M frontend/src/modules/users/UserListPage.tsx
M frontend/tests/auth/guards.test.tsx
M frontend/tests/lanes/LaneListPage.test.tsx
D frontend/tests/lanes/MockBanner.test.tsx
M frontend/tests/parking/ParkingHistory.test.tsx
M frontend/tests/station/Consensus.test.tsx
A frontend/dev/collect-locales.mjs
A frontend/src/components/DetectionImage.tsx
A frontend/src/components/HistoryBrowser.tsx
A frontend/src/lib/i18n.ts
A frontend/src/lib/preferences.ts
A frontend/src/lib/translations.ts
A frontend/src/modules/profile/ProfileEditor.tsx
A frontend/src/modules/settings/PreferencesEditor.tsx
A frontend/tests/auth/preferences.test.ts
A frontend/tests/station/ApiContract.test.ts
A frontend/tests/station/Timeout.test.ts
```

### openspec

```text
M openspec/changes/phase-2-alpr-checkin/design.md
M openspec/changes/phase-2-alpr-checkin/proposal.md
M openspec/changes/phase-2-alpr-checkin/specs/check-in-operations-ui/spec.md
M openspec/changes/phase-2-alpr-checkin/tasks.md
A openspec/changes/complete-real-data-system/.openspec.yaml
A openspec/changes/complete-real-data-system/design.md
A openspec/changes/complete-real-data-system/proposal.md
A openspec/changes/complete-real-data-system/specs/alpr-runtime-boundary/spec.md
A openspec/changes/complete-real-data-system/specs/complete-existing-workflows/spec.md
A openspec/changes/complete-real-data-system/specs/durable-operational-data/spec.md
A openspec/changes/complete-real-data-system/specs/real-alpr-acceptance/spec.md
A openspec/changes/complete-real-data-system/tasks.md
```

### deployment

```text
A deployment/compose.persistence-test.yml
A deployment/compose.real.yml
```
