# Testing

Nguồn: `vitest`, `tests/`, `vite.config.ts`.

- Chạy: `npm test` (Vitest 4 + RTL + jsdom, 25 tests).
- Setup: `tests/setup.ts` (polyfill `HTMLDialogElement.showModal`).
- Phạm vi: Login, AuthProvider, Role Guard, Sidebar visibility, Lane List/Form, User List/Form, Detection History/Detail, Station states, Mock Banner, Health, 403/404.

Không tạo test fake pass khi API chưa sẵn.
