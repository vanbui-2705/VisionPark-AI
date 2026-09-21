# Đề xuất phạm vi Users API — chờ Lead duyệt

Ngày: 21/09/2026. Owner đề xuất: Người 2, nhánh `dqt_core`.
Đây là đề xuất bàn giao, chưa phải quyết định được Lead phê duyệt.

## Quyết định đề xuất

Tách Users API thành task/PR tiếp theo. Đợt hiện tại hoàn thiện Backend Core,
PostgreSQL, auth/RBAC và tích hợp detection. Checklist Người 2 hiện tại không
quy định rõ CRUD user, trong khi giao diện Người 5 đang chờ backend.

## Phạm vi cụ thể để duyệt

| API | Quyền | Kết quả |
| --- | --- | --- |
| GET /api/v1/users | ADMIN | Danh sách, lọc q/role/active, giới hạn tối đa 100 |
| GET /api/v1/users/{id} | ADMIN | Chi tiết public; không password/hash/token |
| POST /api/v1/users | ADMIN | Tạo ADMIN/OPERATOR, hash Argon2id, 409 nếu trùng username |
| PATCH /api/v1/users/{id} | ADMIN | Đổi display_name, email, role, trạng thái |
| GET /api/v1/roles | ADMIN | Hai role dùng cho UI Phase 1: ADMIN/OPERATOR |

Giữ username bất biến sau tạo. Bổ sung email nullable bằng migration nếu Lead
chấp nhận trường đang có trên UI. Các role ACCOUNTANT/TECHNICIAN vẫn là role dự
phòng, không mở thêm chức năng chỉ vì chúng đã được seed.

Đề xuất response dùng `is_active` và `last_login_at` theo identity backend;
Người 5 map sang `active`/`last_login` tại API adapter. List trả mảng để tương thích
UI hiện tại; pagination envelope nếu cần sẽ là thay đổi contract riêng.

Không đưa public registration, reset password, đổi mật khẩu tự phục vụ, refresh
token hay quản trị permission động vào PR này. Khóa tài khoản qua PATCH trạng thái;
chặn tự khóa hoặc hạ quyền Admin cuối cùng. User đã inactive phải bị từ chối ngay
khi dùng lại token, theo current-user dependency hiện có.

## Điều kiện nghiệm thu

- Test ADMIN được CRUD; OPERATOR bị 403; thiếu token 401.
- Test username trùng, role không hợp lệ, user không tồn tại và trạng thái inactive.
- Không trả/log password hoặc hash; password chỉ nhận khi tạo.
- Test giới hạn list và Admin cuối cùng.
- Migration email lên/xuống trên PostgreSQL; không mất user hiện có.
- Người 5 nối màn hình users và thống nhất mapping field.
- Thống nhất audit với Người 3 trước khi triển khai ghi nhận thay đổi user.

## Nội dung gửi Lead

“Backend Core đã có bản sửa trên dqt_core. Đề nghị xác nhận Users API là task mở
rộng riêng: 5 endpoint trong bảng, chỉ ADMIN quản lý, giữ public registration và
reset password ngoài scope. Người 2 làm backend, Người 5 nối UI, Người 3 phối hợp
audit. Xin xác nhận scope, contract field và deadline.”

Chưa gửi tin nhắn tới Lead và chưa triển khai CRUD user trong đợt này.
