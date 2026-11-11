# Testing

Nguồn: `vitest`, `tests/`, `vite.config.ts`.

- Chạy: `npm test` (Vitest 4 + RTL + jsdom).
- Setup: `tests/setup.ts` (polyfill `HTMLDialogElement.showModal`).
- Phạm vi: Login, AuthProvider, Role Guard, Sidebar visibility, Lane List/Form, User List/Form, Detection History/Detail, Station states, Mock Banner, Health, 403/404.

Không tạo test fake pass khi API chưa sẵn.

Phase 4: tests/station/ExitFlow.test.tsx kiểm tra OUT → CASH + mở cổng → xe tiếp theo → IN,
thời gian/ảnh/phí, lỗi mạng, thao tác lặp, phí thay đổi và phím tắt. ApiContract.test.ts
kiểm tra final OUT không tạo check-in, payload và khóa retry checkout thực tế.
Backend tests/integration/test_station_phase4.py kiểm tra timestamp server, ranh giới
phí, xác nhận lại phí mới và retry không giảm counter hai lần. Test checkout, barrier
và pricing hiện có kiểm tra backend mô phỏng; không chứng minh phần cứng thật.

## Functional acceptance

`npm run lint:operations` rejects Station/settings warnings. ExitFlow tests assert preview/CASH payloads and identical retry keys/bodies. Backend test_system_functional_e2e verifies the migrated ledger, counters, report and PostgreSQL concurrent checkout. Follow docs/System-Functional-Runbook.md at repository root for real-stack acceptance; frontend tests use mocked HTTP and do not prove ALPR accuracy.
