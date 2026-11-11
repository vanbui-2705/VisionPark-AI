# Bàn giao BUILD-06/07 và IMPROVE-06/07

Ngày: 2026-11-11. Nguồn: ZIP VisionPark-AI-main do người dùng cung cấp.
Commit nguồn trong ZIP: `315a3863223ec0b9c084770c0a6373932bceb451`.
Bản sửa này chưa được commit lên Git; không dùng SHA nguồn để tuyên bố đây là một
commit mới đã chạy CI.

## Phần đã triển khai

- **BUILD-06:** Viết lại system_gate.py để kiểm tra trực tiếp hệ thống đang chạy,
  thay cho lấy kết quả pytest cục bộ làm bằng chứng hệ thống thật. Kiểm tra PostgreSQL,
  API, frontend, ảnh/MP4 hợp lệ, final/preview, check-in, duplicate, CASH, replay,
  invoice/payment, counter, dashboard/cash-shift report và audit. Manual fallback
  được kiểm tra riêng, không gọi inference. Lỗi trả 1, thiếu điều kiện trả 2, chỉ
  mọi kiểm tra đạt mới trả 0. JSON có commit/environment, run ID, ID/key để truy vết.
  Không chứa token/password, luôn ghi ALPR accuracy NOT_EVALUATED.
- **BUILD-07:** Thêm test_system_functional_e2e.py cho FILE_UPLOAD và manual khi
  ALPR không sẵn sàng; kiểm tra database cuối luồng, daily aggregation và API report.
  Thêm test PostgreSQL hai checkout đồng thời với cùng key và khác key. Bổ sung
  khóa bản ghi phiên trước quyết định checkout để tuần tự hóa ghi ledger/counter.
  Frontend ExitFlow kiểm tra IN → OUT → CASH, nút/phím tắt, payload và retry giữ
  nguyên body/idempotency key.
- **IMPROVE-06:** Backend ruff lint/format qua, pin ruff 0.17.4 để đồng nhất formatter.
  CI có PostgreSQL 17 riêng, credentials sinh ngẫu nhiên, TEST_POSTGRES_URL cho test.
  Settings dùng callback ổn định, functional state update, bỏ kết quả fetch sau
  unmount. Hai cảnh báo set-state-in-effect bị suy luận nhầm qua hàm async được
  chú thích/suppress đúng dòng; không tắt rule toàn dự án. Lint Station/settings
  với --deny-warnings được thêm vào Docker CI. Không tối ưu bundle trong thay đổi này.
- **IMPROVE-07:** Cập nhật README, UAT A–E, env.example, frontend testing docs và
  System-Functional-Runbook.md. Thêm dry_run.py chạy cả functional và ALPR quality,
  giữ kết quả riêng ngay cả khi gate đầu thất bại.

## Kết quả đã kiểm tra tại workspace

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend ở lượt regression | 358 passed, 5 skipped; exit 0 |
| Các test mới/cập nhật sau regression | Chạy lại test gate, E2E và health; không có failure |
| Frontend toàn bộ | 21 test files, 83 tests passed |
| Frontend ExitFlow sau chỉnh luồng IN → OUT | 6 tests passed |
| Backend ruff check | PASS |
| Backend ruff format --check | PASS, 213 files |
| Frontend lint toàn bộ | Exit 0; còn warning ngoài Station/settings |
| npm run lint:operations | PASS, không warning |
| Frontend production build | PASS |
| Workflow/Compose YAML parse | PASS; không thay thế docker compose config |
| system_gate không có stack/media | HOLD, exit 2; không ghi PASS giả |

Môi trường local: Python 3.12.14, Node 24.22.1, ruff 0.17.4. Dockerfile CI dùng
Python 3.12 và Node 24. Workspace chưa có Docker/PostgreSQL nên **chưa thực thi
Docker CI, test race PostgreSQL hoặc functional acceptance trên stack thật**.
Hai test race mới bị skip có lý do khi không có TEST_POSTGRES_URL. CI đã cấu hình
để chạy chúng, nhưng chưa có kết quả CI để tuyên bố PASS.

Các cảnh báo còn lại: Starlette TestClient deprecation; jsdom navigation chưa hỗ
trợ; một số React warnings ở module ngoài phạm vi; bundle lớn hơn 500 kB và import
động không tách chunk. Không che các warning này hoặc nhận là đã tối ưu bundle.

## Cách dùng bản bàn giao

1. Giữ backup code, database và media hiện tại. Giải nén thành thư mục mới.
2. Cài dependencies theo README; không copy đè `.env` thật bằng env.example.
3. Đọc `docs/System-Functional-Runbook.md`, đặt GATE_* và dùng building acceptance
   riêng, giá CASH có free_minutes=0/initial_fee>0.
4. Chạy Docker CI profile để kiểm tra PostgreSQL race; sau đó chạy dry_run.py với
   media thật và điền evidence A–E trong UAT-Demo-Script.md.
5. Báo cáo riêng functional PASS/FAIL/HOLD và ALPR quality PASS/FAIL/HOLD. Phiên
   bản này vẫn FILE_UPLOAD; LIVE_CAMERA/RTSP chưa tích hợp, barrier là SIMULATED.

Gate tạo dữ liệu acceptance thật và không tự xóa dữ liệu sau chạy. Khi lỗi, dùng
session ID/idempotency keys trong report để kiểm tra, rồi xử lý qua workflow bình
thường. Không xóa ledger/audit hoặc chỉnh counter để làm test qua.
