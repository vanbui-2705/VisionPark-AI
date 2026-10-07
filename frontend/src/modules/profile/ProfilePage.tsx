import { useAuth } from '../auth/AuthContext.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { useNavigate } from 'react-router-dom'

export function ProfilePage() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const initial = user ? (user.display_name?.[0] ?? user.username[0]).toUpperCase() : '?'
  return (
    <div className="data-page profile-page">
      <section className="data-hero data-hero--forest profile-hero">
        <div className="profile-hero-main">
          <div className="profile-avatar">{initial}</div>
          <div>
            <span className="data-kicker">Tài khoản · VisionPark</span>
            <h2>Hồ sơ cá nhân</h2>
            <p>{user?.display_name ?? user?.username ?? '—'}</p>
          </div>
        </div>
        <Badge variant={user?.active ? 'success' : 'danger'}>{user?.active ? 'Đang hoạt động' : 'Tạm khóa'}</Badge>
      </section>

      <section className="data-table-card profile-card">
        <div className="profile-card-head">
          <div>
            <span className="data-section-kicker">ACCOUNT DETAILS</span>
            <h3>Thông tin tài khoản</h3>
            <p className="profile-card-lede">Thông tin định danh và quyền truy cập hiện tại.</p>
          </div>
          <span className="profile-account-mark" aria-hidden="true">VP</span>
        </div>
        <div className="profile-details">
          <div className="profile-detail-row"><span>Tên hiển thị</span><strong className="profile-detail-value">{user?.display_name ?? '—'}</strong></div>
          <div className="profile-detail-row"><span>Tên đăng nhập</span><code className="profile-detail-value">{user?.username ?? '—'}</code></div>
          <div className="profile-detail-row"><span>Vai trò</span><Badge>{user?.role === 'ADMIN' ? 'Quản trị viên' : user?.role === 'OPERATOR' ? 'Nhân viên vận hành' : (user?.role ?? '—')}</Badge></div>
          <div className="profile-detail-row"><span>Trạng thái</span><span className={`profile-status ${user?.active ? 'is-active' : 'is-inactive'}`}><span className="profile-status-dot" aria-hidden="true" />{user?.active ? 'Đang hoạt động' : 'Tạm khóa'}</span></div>
        </div>
        <div className="profile-actions">
          <div className="profile-actions-copy"><span className="data-section-kicker">SECURITY</span><p>Quản lý phiên đăng nhập và thông tin bảo mật.</p></div>
          <div className="profile-action-buttons"><Button variant="secondary" disabled title="Chờ Backend API">Đổi mật khẩu — Chờ Backend</Button><Button variant="secondary" onClick={() => { logout(); nav('/login') }}>Đăng xuất</Button></div>
        </div>
      </section>
    </div>
  )
}
