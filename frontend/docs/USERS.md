# Users

ADMIN quản lý qua `/admin/users`, `/new`, `/:id`, `/:id/edit`.
API thật: GET/POST `/api/v1/users`, GET/PATCH `/api/v1/users/{id}`.

Username readonly khi edit; display_name/email/role/active có thể sửa.
Backend normalize username/email, hash mật khẩu, chặn trùng username/email,
không trả hash/mật khẩu và audit không ghi secret. Admin không tự khóa/hạ quyền
chính mình. Active=false vô hiệu hóa login và bearer token hiện tại.

Bốn role tồn tại: ADMIN, OPERATOR, ACCOUNTANT, TECHNICIAN. Hai role đầu có
nghiệp vụ Station; hai role sau hiện chỉ có trang tài khoản. Frontend không
chuyển role khác thành OPERATOR. API roles trả danh sách được provision trong DB.
Đăng ký công khai tắt mặc định; nếu bật, backend gán OPERATOR và từ chối role
trong payload. Password reset của Admin dùng PATCH password; chưa có API đổi
mật khẩu cá nhân từ Profile.

Trang edit cho đổi mật khẩu bằng trường optional (8–128 ký tự), giữ trống để giữ nguyên; checkbox active khóa/mở tài khoản qua cùng PATCH.
