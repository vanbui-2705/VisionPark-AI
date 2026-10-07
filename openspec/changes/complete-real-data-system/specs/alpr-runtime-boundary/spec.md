## REMOVED Requirements

### Requirement: Mock runtime tất định
**Reason**: Ứng dụng chuyển sang model thật hoàn toàn; giữ mock runtime trong ứng dụng có thể tạo dữ liệu nghiệp vụ giả và trái yêu cầu vận hành mới.
**Migration**: Xóa mock provider và cấu hình scenario khỏi mã ứng dụng. Cấu hình provider=mock phải báo lỗi; unit/contract test chuyển sang test doubles trong thư mục test riêng, còn smoke/E2E nghiệm thu chạy model thật với database riêng.
