# Bàn giao Backend Core Phase 2

Phạm vi là phần Member 2 trong `docs/phase-2-linear-backlog.md`: P2-BC-001 tới P2-BC-005.
Nhánh `dqt_core` được đồng bộ với `main` tại `3f7f851` trước khi bổ sung backend core.
Schema/check-in đã có trên main được tái sử dụng, giữ contract của frontend và backend domain.

| Task | Đầu ra |
| --- | --- |
| P2-BC-001 | ParkingTransaction giữ PARKED, lane, detection, plate, actor và timestamps; bổ sung DB checks cho status/confidence/key/fingerprint |
| P2-BC-002 | Revision additive 20261006_0006; upgrade/downgrade giữ detection, user/role và transaction hiện có |
| P2-BC-003 | Policy dùng chung ở app/database/idempotency.py; key/fingerprint được lưu bền vững trên parking_transactions |
| P2-BC-004 | Endpoint /api/v1/parking/check-in dùng auth/RBAC/get_db/error/correlation chung; không tạo engine/session riêng |
| P2-BC-005 | Bootstrap/seed lặp từ DB rỗng; bốn role, hai user demo, hai lane; fixture LANE_IN_01 active |

## Idempotency và đồng thời

- Key tối đa 255 ký tự, không rỗng. Nếu header và body cùng có key, hai giá trị phải bằng nhau.
- Fingerprint của request mới gồm actor, lane, normalized plate, detection, original AI plate,
  requested source, confidence và notes. Thứ tự thuộc tính JSON không ảnh hưởng fingerprint.
- Retry thành công trả transaction đã commit trước khi kiểm tra trạng thái làn hiện tại.
  Request mới vẫn kiểm tra làn IN active.
- Cùng key khác payload hoặc actor trả 409 IDEMPOTENCY_KEY_REUSED.
- Cùng key và payload gửi đồng thời chỉ tạo một transaction và một CREATE_CHECKIN audit.
- Hai key khác nhau cho một plate PARKED chỉ có một request thành công; request còn lại trả
  409 PLATE_ALREADY_PARKED nhờ partial unique index ở database.
- Transaction có fingerprint cũ vẫn replay được nếu actor, payload và notes không đổi.
- Transaction và audit cùng commit hoặc rollback bằng request session.

## Sửa nền tảng Phase 1

- DATABASE_URL/JWT_SECRET_KEY bắt buộc; key mẫu và key development bị từ chối.
- Swagger sử dụng HTTP Bearer; login vẫn nhận JSON.
- CORS bao phủ lỗi 500; preflight vẫn có correlation ID.
- Operator đọc được lane list/active/detail cho Station; các mutation vẫn chỉ dành cho Admin.
- Compose yêu cầu JWT_SECRET_KEY từ môi trường. CI sinh signing key riêng cho từng run, không
  lưu key thật trong Git.

## Kiểm chứng

Kiểm chứng ngày 06/10/2026 trên Windows, Python 3.12 và PostgreSQL 17.11:

| Kiểm tra | Kết quả |
| --- | --- |
| Full suite SQLite và PostgreSQL | 224 passed, 3 skipped, 2 deprecation warnings |
| Ba race test PostgreSQL | Pass: cùng key, khác key/cùng plate, cùng key/khác payload |
| Migration/rollback và giữ dữ liệu cũ | Pass trên SQLite/PostgreSQL |
| Bootstrap hai lần từ DB rỗng | Pass trên SQLite/PostgreSQL |
| Ruff check / format | Pass, 112 Python files |
| pip check | Không có dependency hỏng |
| Mock scenario/manifest gate và synthetic benchmark | Pass |
| Uvicorn HTTP trên SQLite riêng | Health/login 200; check-in/retry 201; payload conflict 409; thiếu token 401; preflight 200 |
| Compose/workflow YAML | Parse và cấu hình signing key pass |

Ba ca skipped là bản SQLite của race tests; các bản PostgreSQL đều được chạy và đạt.
PostgreSQL được chạy trên loopback trong cluster riêng, tự dừng sau kiểm thử.
Docker Compose full stack chưa chạy trong môi trường này vì không có Docker.
Mock benchmark không được dùng làm bằng chứng chất lượng model thật.
Evidence tóm tắt: `docs/backend-core-phase-2-evidence-2026-10-06.json`.

Lệnh kiểm tra từ backend:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

Để kiểm chứng PostgreSQL, dùng TEST_POSTGRES_URL trỏ tới server test với quyền CREATEDB.
Fixture tự tạo/drop database vp_test_<uuid>, không migrate database có trong URL đầu vào.
Các race tests chỉ chạy trên PostgreSQL; SQLite không được dùng làm bằng chứng concurrent writes.
Các test migration kiểm tra dữ liệu trước/sau upgrade và downgrade của revision mới, không xóa
hay stamp dữ liệu để ép test đạt.

## Ranh giới bàn giao

Phần này hoàn thiện nền tảng DB và idempotency của Member 2. Check-out, pricing/payment,
train model, real-provider benchmark và giao diện của thành viên khác giữ scope riêng.
Migration sẽ từ chối dữ liệu cũ vi phạm constraint thay vì tự sửa hoặc xóa chúng.
Owner domain/Lead cần review migration và policy replay trước khi merge vào main.
