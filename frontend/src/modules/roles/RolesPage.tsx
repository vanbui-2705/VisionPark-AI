import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'

export function RolesPage() {
  const adminCount = PERMISSION_MATRIX.filter((p) => p.admin).length
  const operatorCount = PERMISSION_MATRIX.filter((p) => p.operator).length

  return (
    <div className="utility-page roles-page">
      <Breadcrumb items={[{ label: 'Phân quyền' }, { label: 'Vai trò' }]} />

      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Phân quyền người dùng · VisionPark</span>
          <h1>Vai trò &amp; phân quyền</h1>
          <p>Hệ thống hỗ trợ 2 nhóm vai trò: Quản trị viên (ADMIN) và Nhân viên vận hành (OPERATOR).</p>
        </div>
        <div className="utility-stat-row">
          <div className="utility-hero-stat"><strong>{adminCount}</strong><span>quyền quản trị</span></div>
          <div className="utility-hero-stat"><strong>{operatorCount}</strong><span>quyền vận hành</span></div>
        </div>
      </section>

      <div className="role-card-grid">
        <section className="utility-panel role-panel role-panel--admin">
          <div className="role-panel-head">
            <div><span className="utility-section-kicker">FULL ACCESS</span><h3>Quản trị viên (ADMIN)</h3></div>
            <Badge variant="success">Toàn quyền</Badge>
          </div>
          <p className="muted">Cấu hình hệ thống, quản lý làn xe, tài khoản người dùng, nhật ký và thông số ALPR.</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.filter((p) => p.admin).map((p) => (
              <div key={p.perm} className="role-permission-row">
                <span>{p.label}</span>
                <code>{p.perm}</code>
              </div>
            ))}
          </div>
        </section>

        <section className="utility-panel role-panel role-panel--operator">
          <div className="role-panel-head">
            <div><span className="utility-section-kicker">OPERATIONS</span><h3>Nhân viên vận hành (OPERATOR)</h3></div>
            <Badge variant="info">Vận hành</Badge>
          </div>
          <p className="muted">Quét biển số, xác nhận xe vào/ra, tra cứu lịch sử và chỉnh sửa cài đặt cá nhân.</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.map((p) => (
              <div key={p.perm} className={`role-permission-row${p.operator ? '' : ' is-unavailable'}`}>
                <span>{p.label}</span>
                <span className="role-permission-state" aria-label={p.operator ? 'Có quyền' : 'Không có quyền'}>{p.operator ? '✓' : '—'}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="utility-table-panel">
        <div className="utility-panel-head">
          <div>
            <span className="utility-section-kicker">ROLE COMPARISON</span>
            <h3>Ma trận phân quyền chi tiết</h3>
            <p className="muted">So sánh nhanh quyền giữa hai vai trò trong hệ thống.</p>
          </div>
          <Badge>{PERMISSION_MATRIX.length} chức năng</Badge>
        </div>
        <div className="utility-table-wrap">
          <table className="table utility-table">
            <thead><tr><th>Chức năng</th><th>Mã quyền</th><th>Quản trị viên</th><th>Vận hành</th></tr></thead>
            <tbody>
              {PERMISSION_MATRIX.map((p) => (
                <tr key={p.perm}>
                  <td style={{ fontWeight: 600 }}>{p.label}</td>
                  <td style={{ fontFamily: 'ui-monospace, monospace', fontSize: 11, color: 'var(--muted)' }}>{p.perm}</td>
                  <td><Badge variant={p.admin ? 'success' : 'neutral'}>{p.admin ? '✓' : '✗'}</Badge></td>
                  <td><Badge variant={p.operator ? 'info' : 'neutral'}>{p.operator ? '✓' : '✗'}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="role-note">
          Frontend dùng helper <code>can(user, permission)</code> để ẩn/hiện UI. Backend vẫn enforce cuối cùng trên mọi API.
        </div>
      </section>
    </div>
  )
}
