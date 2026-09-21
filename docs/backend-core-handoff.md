# Bàn giao Backend Core — dqt_core

Ngày kiểm chứng: 21/09/2026. Nhánh làm việc: `dqt_core`.
Nhánh đã fast-forward từ `origin/dqt_core` (`09817cb`) tới `origin/main`
(`26a18c586dff8548dd6883dfcf98f8754e904fcc`) trước khi áp dụng bản sửa.
Bằng chứng dưới đây được thu thập trước khi gửi PR. Cần Người 3 và Lead review trước khi merge.

## Thay đổi

1. Khai báo OpenCV headless/NumPy để cài mới import app thành công; ONNX là extra
   tùy chọn. Mẫu .env được giữ trong Git, secret thực vẫn bị ignore.
2. Alembic đọc cùng Settings/.env với app; test truyền URL riêng rõ ràng.
   Thêm `python -m app.database.bootstrap`: migrate rồi seed khi AUTO_SEED=true.
3. Detection lane FK dùng UUID; sửa tạo/chuyển/drop PostgreSQL enum đúng cách.
   Khớp chiều dài cột Lane giữa model/migration.
4. Hai DB adapter nhận cùng request session; chuyển implementation vào
   `app/integrations/persistence`, giữ AI ports độc lập ORM. Không tạo SessionLocal.
   Ghi detection thất bại thì rollback session và xóa ảnh của lần ghi đó.
5. Lane read cho user đã xác thực; mutation ADMIN; detection ADMIN/OPERATOR.
   Upload nhận UUID từ Lane API và dùng UPLOAD_MAX_BYTES trong Settings.
6. Detection và health dùng cùng runtime. Mock xác định, có version mock rõ ràng;
   provider chưa nối trả not_ready. Health ALPR cũ dùng chung handler kiểm tra DB.
7. 404/405 cùng error contract; 500 có header correlation ID khớp body. CORS expose
   correlation header. Giữ Allow/WWW-Authenticate khi có.
8. Lint/format lại backend; các thay đổi ONNX ngoài wiring chỉ là style/type hint/
   exception chaining, không hoàn thiện hay tuyên bố thuật toán nhận diện thật.

## Migration cần Người 3 review

Revision `aa276e942822` cũ không thể chạy trên PostgreSQL vì FK varchar -> UUID và
chuyển varchar -> native enum thiếu bước tạo/cast. Bản này sửa phần PostgreSQL của
revision đó để clean install chạy được, giữ ID và chuỗi revision, không sửa schema
identity. Một revision chỉ thêm phía sau không thể chữa lỗi fresh install bị chặn
trước khi đến revision mới.

Database SQLite đã ở revision cũ dùng `20260921_0003` để đổi lane_id sang dạng lưu
UUID. Upgrade giữ dữ liệu detection, không xóa/reset hay stamp DB. Downgrade revision
mới khôi phục String(50) trên SQLite; trên PostgreSQL là no-op vì parent đã dùng UUID.
Rollback toàn chuỗi đã được kiểm chứng trên DB test riêng. Trước khi áp dụng vào DB
của nhóm, Người 3 cần xác nhận revision/schema thực tế và backup theo quy trình nhóm.

## Bằng chứng

Môi trường: Windows, Python 3.13, PostgreSQL 17.11; venv mới cài bằng
`python -m pip install -e "work/VisionPark-AI/backend[dev]"` từ thư mục workspace.
PostgreSQL chạy riêng ở 127.0.0.1:55432; không dùng dữ liệu staging/production.

| Kiểm tra | Kết quả |
| --- | --- |
| Cài dependency vào venv mới | Thành công |
| Pytest, SQLite + PostgreSQL thật | 105 passed; 2 deprecation warnings từ Starlette/httpx |
| Ruff check toàn backend | Pass |
| Ruff format --check | Pass |
| pip check | Không có dependency hỏng |
| Alembic upgrade/downgrade DB rỗng | Pass |
| Alembic check so với ORM | Không phát sinh migration mới |
| Upgrade giữ detection đã tồn tại | Pass |
| Seed lặp | 4 roles, 2 users, 2 lanes |
| Uvicorn HTTP: health/login/lane/detection | 200/200/200/200 |
| Operator sửa làn / thiếu token | 403 / 401 |
| Lưu detection qua HTTP | PostgreSQL có 1 detection và file ảnh |
| Rollback base rồi bootstrap lại | Pass |

Log kèm gói bàn giao: `clean-install.log`, `final-tests.log`, `lint.log`,
`http-smoke.log`, `uvicorn-smoke.log`. Smoke dùng runtime mock, không đo chất lượng AI.
Cách chạy lại nằm trong backend/README.md. Test PostgreSQL tự tạo DB riêng có tiền tố
vp_test_ và dọn sau ca kiểm tra, không migrate DB được chỉ định trong TEST_POSTGRES_URL.

## Ranh giới bàn giao

- Người 3: review migration UUID/enum, request session và cleanup khi DB lỗi.
- Người 1: review runtime/readiness mock; tiếp tục sở hữu ONNX thật, CI/Compose.
- Người 5: dùng token và UUID lane; kiểm tra frontend mapping theo API hiện có.
- Lead: duyệt riêng [Users API scope](users-api-scope-proposal.md).

Chưa thực hiện: CRUD Users, public registration, detection history/confirmation,
audit nghiệp vụ đầy đủ, model YOLO/OCR thật, E2E browser frontend, Docker Compose
full stack. Bản sửa giữ các tên field detection hiện có, chưa đổi sang contract
ALPR rộng hơn của tài liệu kế hoạch. Không đánh dấu toàn bộ Phase 1 hoàn tất.
