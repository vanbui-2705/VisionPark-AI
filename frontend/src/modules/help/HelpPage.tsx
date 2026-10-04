import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
export function HelpPage() {
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Trợ giúp' }]} />
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Guide · Duy Anh</div>
        <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Trợ giúp</h2>
        <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Vai trò, trạm quét, ALPR Test Lab và cách gửi mã hỗ trợ khi gặp lỗi.</p>
      </div>
      {[
        { title: 'Vai trò', body: <ul style={{ margin: 0, paddingLeft: 18, display: 'grid', gap: 6 }}><li><b>ADMIN:</b> Dashboard, Làn xe (CRUD không xóa), Người dùng, Vai trò/Phân quyền, ALPR Test Lab, Audit Logs, Error Center, System Health.</li><li><b>OPERATOR:</b> Quét biển số, Lịch sử nhận diện, Xem làn xe, Xác nhận/sửa biển số, Hồ sơ/Cài đặt/Thông báo/Trợ giúp.</li><li>Sidebar dùng <code>can(user, permission)</code> — backend là authority.</li></ul> },
        { title: 'Trạm quét', body: <ul style={{ margin: 0, paddingLeft: 18 }}><li>Màn hình quét: chọn lane, chọn video MP4 local, trạng thái demo (?demoState=...). Bấm <b>Toàn màn hình</b> để mở fullscreen.</li><li>Fullscreen: video chiếm 70–80%, biển số/confidence/HƯỚNG lớn; phím tắt Enter (Xác nhận) · E (Sửa) · R (Thử lại) · Space (Play/Pause) · Esc (Thoát).</li></ul> },
        { title: 'ALPR Test Lab (dev only)', body: <p style={{ margin: 0 }}>Gửi header <code>X-Mock-Scenario</code>: success / low_confidence / no_plate / error. Bên dev trả mock; backend thật trả kết quả model.</p> },
        { title: 'Sự cố', body: <p style={{ margin: 0 }}>Gặp lỗi API → mở Error Center; copy <b>Mã hỗ trợ</b> (correlationId) gửi quản trị viên. <Badge>Tip</Badge></p> },
      ].map((s) => (
        <section key={s.title} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
          <h3 style={{ margin: '0 0 10px' }}>{s.title}</h3>
          <div style={{ fontSize: 13, color: 'var(--text)' }}>{s.body}</div>
        </section>
      ))}
    </div>
  )
}
