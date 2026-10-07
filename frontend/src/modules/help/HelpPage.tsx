import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
export function HelpPage() {
  return (
    <div className="utility-page help-page">
      <Breadcrumb items={[{ label: 'Trợ giúp' }]} />
      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Hướng dẫn sử dụng · VisionPark</span>
          <h1>Trợ giúp</h1>
          <p>Hướng dẫn chức năng theo vai trò, vận hành trạm quét và xử lý khi phát sinh sự cố.</p>
        </div>
      </section>
      {[
        { title: 'Phân quyền vai trò', body: <ul style={{ margin: 0, paddingLeft: 18, display: 'grid', gap: 6 }}><li><b>Quản trị viên (ADMIN):</b> Tổng quan, Quản lý làn xe, Người dùng, Vai trò & Phân quyền, Kiểm thử ALPR, Nhật ký kiểm tra, Trung tâm lỗi, Tình trạng hệ thống.</li><li><b>Nhân viên vận hành (OPERATOR):</b> Quét biển số, Lịch sử nhận diện, Lịch sử đỗ xe, Xác nhận/sửa biển số, Hồ sơ, Cài đặt và Trợ giúp.</li><li>Menu tự động ẩn/hiện theo quyền của tài khoản; hệ thống kiểm tra bảo mật ở từng yêu cầu.</li></ul> },
        { title: 'Trạm quét biển số', body: <ul style={{ margin: 0, paddingLeft: 18 }}><li>Màn hình quét: chọn làn xe, chọn video mẫu hoặc luồng camera trực tiếp. Bấm <b>Toàn màn hình</b> để vào chế độ vận hành chuyên dụng.</li><li>Chế độ toàn màn hình: video tối ưu kích thước, biển số và độ tin cậy hiển thị to rõ; hỗ trợ phím tắt: Enter (Xác nhận) · E (Sửa) · R (Thử lại) · Space (Phát/Tạm dừng) · Esc (Thoát).</li></ul> },
        { title: 'Phòng thử nghiệm ALPR', body: <p style={{ margin: 0 }}>Cho phép kiểm thử các kịch bản nhận diện mẫu: thành công, độ tin cậy thấp, không thấy biển số hoặc mô phỏng lỗi kết nối.</p> },
        { title: 'Xử lý khi phát sinh sự cố', body: <p style={{ margin: 0 }}>Khi gặp lỗi kết nối hoặc thao tác thất bại → truy cập <b>Trung tâm lỗi</b>; sao chép <b>Mã đối soát</b> (correlationId) gửi đội ngũ kỹ thuật để tra cứu log server. <Badge>Mẹo</Badge></p> },
      ].map((s) => (
        <section key={s.title} className="utility-panel help-panel">
          <div className="utility-panel-head"><span className="utility-section-kicker">HƯỚNG DẪN {String(s.title).toUpperCase()}</span></div>
          <h3>{s.title}</h3>
          <div className="help-panel-body">{s.body}</div>
        </section>
      ))}
    </div>
  )
}
