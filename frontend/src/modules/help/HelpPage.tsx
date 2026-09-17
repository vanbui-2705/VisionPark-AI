import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
export function HelpPage() {
  return (
    <div>
      <Breadcrumb items={[{ label: 'Trợ giúp' }]} />
      <h2>Trợ giúp</h2>
      <section className="help-section card">
        <h3>Vai trò</h3>
        <ul>
          <li><b>ADMIN:</b> Dashboard, Làn xe (CRUD không xóa), Người dùng, Vai trò/Phân quyền, ALPR Test Lab, Audit Logs, Error Center, System Health.</li>
          <li><b>OPERATOR:</b> Quét biển số, Lịch sử nhận diện, Xem làn xe, Xác nhận/sửa biển số, Hồ sơ/Cài đặt/Thông báo/Trợ giúp.</li>
          <li>Sidebar dùng <code>can(user, permission)</code> — backend là authority.</li>
        </ul>
      </section>
      <section className="help-section card">
        <h3>Trạm quét</h3>
        <ul>
          <li>Màn hình quét: chọn lane, chọn video MP4 local, trạng thái demo (?demoState=...). Bấm <b>Toàn màn hình</b> để mở fullscreen.</li>
          <li>Fullscreen: video chiếm 70–80%, biển số/confidence/HƯỚNG lớn; phím tắt Enter (Xác nhận) · E (Sửa) · R (Thử lại) · Space (Play/Pause) · Esc (Thoát).</li>
        </ul>
      </section>
      <section className="help-section card">
        <h3>ALPR Test Lab (dev only)</h3>
        <p>Gửi header <code>X-Mock-Scenario</code>: success / low_confidence / no_plate / error. Bên dev trả mock; backend thật trả kết quả model.</p>
      </section>
      <section className="help-section card">
        <h3>Sự cố</h3>
        <p>Gặp lỗi API → mở Error Center; copy <b>Mã hỗ trợ</b> (correlationId) gửi quản trị viên.</p>
      </section>
    </div>
  )
}
