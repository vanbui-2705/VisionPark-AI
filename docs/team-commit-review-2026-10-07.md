# Review commit và mức hoàn thành thành viên — 07/10/2026

## Phạm vi và cách đánh giá

Đánh giá nhiệm vụ theo `docs/phase-2-linear-backlog.md` và phân công Phase 1,
đối chiếu commit thực tế, code đã merge, contract và test. Không chấm theo số
commit/dòng code, không suy ra mức đóng góp cá nhân chỉ từ tên author của AI.

Trong lúc review, fetch phát hiện remote main mới `7fd7497` (merge nhánh Operations
Duy Anh), sau bản `b622ded` vừa được kéo trước đó. Review này xét **7fd7497** trong
checkout riêng `E:\BE_AI\VisionPark-review-main-7fd7497`; không merge bản mới này
vào worktree đang phát triển, không triển khai Docker hoặc thay database.

Các sửa real-only, metadata/persistence, profile/preferences/notifications và E2E
trong worktree VisionPark vẫn chưa commit: không tính chúng vào phần bàn giao đã
merge của thành viên. Stash/index/untracked backup commits không phải commit tính
năng. Merge commit thể hiện tích hợp, không tự chứng minh tác giả viết mọi module.

## Đánh giá theo người và nhiệm vụ

| Thành viên/role | Bằng chứng commit chính | Mức hoàn thành so với nhiệm vụ |
|---|---|---|
| Vân/Bùi Vân — Member 1, AI/PM/DevOps/QA | `4665bd4` OCR thật; `6a304eb` parking; `2e077a6` route; `1b4c4b5` video; `fa20b4e` benchmark; `bbe9140` CI | Có nền tảng AI, integration và công cụ QA; **chưa đóng nghiệm thu model/release**. Commit đặt tên hoàn thành M4 nhưng benchmark committed vẫn có mock/synthetic, chưa chứng minh chất lượng trên nhiều xe thật. |
| Đinh Quang Túy — Member 2, Backend Core | `09817cb`, `05f6a99`, `eba5e29`, `8240260`; nhánh dqt_core qua PR #16 có `c503223`, `93ee52a` author Codex | **Phần nền tảng/core đã bàn giao tốt**: auth/config/DB/migrations/idempotency/race protection có test/evidence. Thiếu xác nhận clean Docker full stack trong phạm vi evidence cũ. Không gán hai commit author Codex thành công sức trực tiếp của cá nhân. |
| Bá Nam — Member 3, Backend Domain | `7b487c3`, `2eb9ac4`, `41835b0`, `bf19a2b`, `87a09a8` | **Nghiệp vụ chính đã có, hardening chưa hoàn tất**: lanes, ALPR integration, check-in, history/audit, tests. Cần khóa provenance vào detection thật, mở rộng ca lỗi và rà soát contract sau merge. |
| Đồng Minh Hiếu — Member 4, Station | `f6f7f42`, `fc583e7`; hỗ trợ Operations bằng `4112b34`, `828a9ba`, `87665ab`, `f530ade`, `6870c2a` | **UI/components/tests đã có, tích hợp real trên main chưa đạt Done**: Station còn mock default, khác token key, sai field active và thiếu final capture. Ghi nhận đóng góp ngoài ownership cho Operations. |
| Duy Anh — Member 5, Operations/App Foundation | `b5ae0b1`, `7d6eb08`, `8bcd791`; loạt polish; mới `5dc5551`, `515a608`, merge `7fd7497` | **UI và pagination có tiến triển rõ, bàn giao sau merge chưa đồng bộ backend**. Có filter/history/audit/RBAC tests; endpoint parking/audit main chưa khớp envelope/pageSize, audit detail mới làm mất một phần thay đổi Hiếu. |

Đây là mức hoàn thành sản phẩm trong repo, không phải đánh giá năng lực/con người.
Chưa có dữ liệu Linear thực tế, PR review approvals hoặc timesheet để chấm phần trăm
chính thức. Nếu cần phần trăm, phải chốt task/acceptance và trọng số trước.

## Các điểm cần sửa trước khi công nhận Done

### 0. Chặn bàn giao — main 7fd7497 hiện không đạt startup/build/test gate

Kiểm tra độc lập, không dùng code đã sửa trong worktree:

- Import `app.api.v1.endpoints.alpr` thất bại với `NameError: Optional is not defined`
  tại dòng 236. File mới dùng Optional nhưng không import; backend app không thể
  khởi động qua router này. Ruff riêng file này báo 13 lỗi, gồm undefined Optional.
- Frontend `npm run build` thất bại: `src/api/mocks/fixtures.ts:80:53`, TS18047,
  `a.actor` có thể null.
- Full frontend tests: **58 passed, 5 failed / 63**. AuditDetails mất nội dung
  trường riêng; ba ca history filter (lane/status/time) và một ca inactive lane
  thất bại sau thay đổi giao diện/contract nhưng test cũ chưa đồng bộ.
- Backend domain/idempotency unit tests: **11 passed**. Kết quả này không chứng
  minh startup/backend integration pass; import API bên trên vẫn thất bại.

Ưu tiên Duy Anh sửa phần mới và phối hợp reviewer Vân/Core. Chưa nên công nhận
Operations release Done hoặc triển khai main mới trước khi gate chạy lại xanh.
Không phủ nhận những phần UI đã làm; lỗi merge/integration cần đánh giá riêng.

### 1. Cao — Station chưa thực sự nối đúng hệ thống thật trên main

`frontend/src/modules/station/api.ts`:

- Mock bật khi `VITE_USE_MOCK_ALPR` không bằng `false`.
- Đọc `access_token`, trong khi client/auth chung dùng `visionpark.access_token`:
  bật real có thể gửi request không có Bearer và nhận 401.
- Lọc `lane.active`, backend trả `is_active`: real lane list bị lọc hết.
- Chỉ gửi preview/persist=false; backend trả detection_id=null. Confirm gọi parking
  trực tiếp, không final-persist ảnh/detection trước: không có provenance/link ảnh
  nhận diện thật trong transaction.
- Key `station-null-accepted` bị dùng lại khi preview không có detection_id, gây
  conflict/replay không đúng sau khi xử lý xe khác.

Owner xử lý: Hiếu phối hợp Bá Nam và Vân. Cần E2E đăng nhập bình thường → lane thật →
video thật → final detection → confirm → ảnh/history/audit, không set token riêng
hoặc bật mock để ép pass. Các điểm này đã được sửa trong worktree chưa commit;
cần đưa phần sửa vào PR có review thay vì ghi task main đã Done.

### 2. Cao — Pagination Operations mới chưa đồng bộ trong merge 7fd7497

`5dc5551`/`515a608` đưa frontend sang `page/pageSize` và envelope
`items/total/totalPages`, nhưng main vẫn dùng endpoint parking cũ:
`backend/app/api/v1/endpoints/parking.py` nhận `limit` và trả list; `pageSize` bị
bỏ qua, limit mặc định 100. Client fallback coi độ dài trang là tổng toàn DB.
Trang 20 dòng có thể nhận 100 dòng và total sai.

Audit endpoint main còn nhận actor/action/from/to/limit, không nhận page/pageSize,
resource/q; chuyển trang có thể tải lại cùng danh sách, filter resource/q không có
hiệu lực. Các router/repository/modules parking và audit mới xuất hiện trong
commit `515a608` trên nhánh, **không có trong tree main 7fd7497**. Do đó không thể
chấm hoàn thành từ commit message hoặc trạng thái ancestor alone.

Owner: Duy Anh phối hợp Bá Nam/Core, chọn một bộ API/model canonical, tránh thêm
module ORM/route trùng để vá contract. Test DB >200 bản ghi, tổng số, trang 2,
filter kết hợp và ngày; phải gọi backend thực, không chỉ mock envelope mong muốn.

### 3. Cao — Provenance AI còn cho client tự cung cấp

Main `backend/app/modules/checkin/service.py` ưu tiên `request.original_ai_plate`,
`request.confidence`; `_resolve_source` trả requested source khi được cung cấp.
Client có thể tạo manual transaction nhưng gắn nguồn AI_ACCEPTED/confidence tự đặt.
Làm sai audit và báo cáo tỷ lệ AI. Owner Bá Nam: lấy AI plate/confidence từ detection
đã lưu, không có detection thì MANUAL_ENTRY; khác AI plate thì corrected.
Worktree hiện có phần sửa, chưa phải commit của bản main.

### 4. Trung bình — Audit detail bị regression khi merge Operations mới

`f530ade` của Hiếu thêm AI plate/final plate/source/actor/time và test
`AuditDetails.test.tsx`. Main mới thay AuditLogsPage bằng trang pagination, phần
detail còn JSON Before/After nhưng không còn các trường hiển thị riêng như test
kỳ vọng. Cần giữ cả pagination/filter và detail thay vì ghi đè một phía. Owner
Duy Anh + Hiếu; chạy regression cả test cũ lẫn mới.

### 5. Trung bình — Role frontend và chức năng nền tảng chưa khớp backend

`authApi.ts` main map mọi role khác ADMIN thành OPERATOR, không bảo toàn
ACCOUNTANT/TECHNICIAN; active lấy `active` trong khi backend dùng `is_active`.
Frontend có trang users nhưng main chưa có `backend/app/modules/users/router.py`;
cần đối chiếu API route thực, không coi UI/fixture fallback là chức năng hoàn tất.
Owner Duy Anh + Core. Profile/preferences/notification/error database là phạm vi
bổ sung mới, không tự quy thành thiếu sót của backlog Phase 2 cũ.

### 6. Trung bình — Claim release gate/benchmark cần dựa trên evidence thật

`fa20b4e` có công cụ benchmark tốt nhưng dataset committed không có ảnh xe thật;
image_bytes fallback synthetic và release_gate chạy mock. Không đủ đóng chất lượng
AI. Benchmark thật mới ở worktree chỉ 2 xe/11 frame, 8/10 positive exact match,
warm p95 3,03 giây CPU; chưa đạt dưới một giây, chưa đủ validation đa cảnh.
Owner Vân: chia theo xe/video, nhiều điều kiện ánh sáng/negative, provenance/model/
hardware reproducible và acceptance threshold rõ ràng. Không đóng gate bằng readiness.

Regex trong `87a09a8` là kiểm tra ký tự cho phép, **không phải kiểm tra định dạng
biển Việt Nam đầy đủ**: thử trực tiếp pattern từ main chấp nhận `AAA`, `123`.
Nếu cần regex nghiệp vụ chặt hơn phải chốt các loại biển hợp lệ, không tự áp một
mẫu làm loại nhầm biển; đây là feedback về claim, không khẳng định mọi biển ấy phải
bị từ chối theo contract hiện tại.

## Feedback giao việc

- Vân: quản lý release checklist, đưa các sửa real-only vào PR, không nhận nghiệm
  thu theo tên commit; chốt benchmark thật và kiểm tra sau merge.
- Core: giữ migration/data/race regression, review thay đổi ORM/router Operations;
  có evidence clean setup Docker đầy đủ trước bàn giao release.
- Bá Nam: bổ sung tests chống giả provenance, lane/detection mismatch, manual,
  duplicate/race/idempotency và audit atomic; giữ domain contract canonical.
- Hiếu: dùng shared client/auth/lane mapping và final-capture confirmation; bổ sung
  browser E2E thật, lỗi provider/no-plate, đổi xe/làn khi request pending.
- Duy Anh: sửa hợp đồng pagination/filter trong main, giữ audit detail của Hiếu,
  role mapping và các test contract gọi API thật; không tính UI chưa có API là Done.

## Giới hạn kiểm chứng

Review code tại immutable revision 7fd7497; lịch sử test ở báo cáo Core là evidence
đã ghi, không tự nhận là lần chạy lại hiện tại. Test/build mới cho checkout main
được ghi ở phần kết quả bên dưới. Không suy đoán CI GitHub hoặc phê duyệt PR từ
local git. Không sửa code của thành viên trong lượt review này.

Log chạy riêng main: `backend/var/review-main-7fd7497-frontend-test.txt` và
`backend/var/review-main-7fd7497-frontend-build.txt` (file tạm local, không commit).
Backend import và ruff chạy trực tiếp trên checkout cô lập, chỉ dùng SQLite/test
signing key; không kết nối database vận hành. Dependencies frontend dùng chung
node_modules local qua junction; chưa làm npm clean install hoặc kiểm tra CI remote.
