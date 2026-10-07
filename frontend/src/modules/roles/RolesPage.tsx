import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'

export function RolesPage() {
  const adminCount = PERMISSION_MATRIX.filter((p) => p.admin).length
  const operatorCount = PERMISSION_MATRIX.filter((p) => p.operator).length
  const accountantCount = PERMISSION_MATRIX.filter((p) => p.accountant).length
  const technicianCount = PERMISSION_MATRIX.filter((p) => p.technician).length

  return (
    <div className="utility-page roles-page">
      <Breadcrumb items={[{ label: 'Phân quyền' }, { label: 'Vai trò' }]} />

      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Phân quyền người dùng · VisionPark</span>
          <h1>Vai trò &amp; phân quyền</h1>
          <p>Hệ thống hỗ trợ 4 vai trò: ADMIN, OPERATOR, ACCOUNTANT (kế toán) và TECHNICIAN (kỹ thuật) — đồng bộ với backend RoleName.</p>
        </div>
        <div className="utility-stat-row">
          <div className="utility-hero-stat"><strong>{adminCount}</strong><span>ADMIN</span></div>
          <div className="utility-hero-stat"><strong>{operatorCount}</strong><span>OPERATOR</span></div>
          <div className="utility-hero-stat"><strong>{accountantCount}</strong><span>ACCOUNTANT</span></div>
          <div className="utility-hero-stat"><strong>{technicianCount}</strong><span>TECHNICIAN</span></div>
        </div>
      </section>

      <div className="role-card-grid" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))' }}>
        <section className="utility-panel role-panel role-panel--admin">
          <div className="role-panel-head">
            <div><span className="utility-section-kicker">FULL ACCESS</span><h3>ADMIN</h3></div>
            <Badge variant="success">Toàn quyền</Badge>
          </div>
          <p className="muted">Cấu hình hệ thống, quản lý làn xe, tài khoản, audit và ALPR.</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.filter((p) => p.admin).map((p) => (
              <div key={p.perm} className="role-permission-row"><span>{p.label}</span><code>{p.perm}</code></div>
            ))}
          </div>
        </section>
        <section className="utility-panel role-panel role-panel--operator">
          <div className="role-panel-head">
            <div><span className="utility-section-kicker">OPERATIONS</span><h3>OPERATOR</h3></div>
            <Badge variant="info">Vận hành</Badge>
          </div>
          <p className="muted">Quét biển số, xác nhận, lịch sử và hồ sơ cá nhân.</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.map((p) => (
              <div key={p.perm} className={`role-permission-row${p.operator ? '' : ' is-unavailable'}`}>
                <span>{p.label}</span><span className="role-permission-state">{p.operator ? '✓' : '—'}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="utility-panel role-panel">
          <div className="role-panel-head">
            <div><span className="utility-section-kicker">FINANCE</span><h3>ACCOUNTANT</h3></div>
            <Badge variant="success">Kế toán</Badge>
          </div>
          <p className="muted">Dashboard, lịch sử đỗ xe, audit logs, hồ sơ và thông báo.</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.map((p) => (
              <div key={p.perm} className={`role-permission-row${p.accountant ? '' : ' is-unavailable'}`}>
                <span>{p.label}</span><span className="role-permission-state">{p.accountant ? '✓' : '—'}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="utility-panel role-panel">
          <div className="role-panel-head">
            <div><span className="utility-section-kicker">TECH</span><h3>TECHNICIAN</h3></div>
            <Badge variant="info">Kỹ thuật</Badge>
          </div>
          <p className="muted">Station, làn, ALPR, system health và hồ sơ.</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.map((p) => (
              <div key={p.perm} className={`role-permission-row${p.technician ? '' : ' is-unavailable'}`}>
                <span>{p.label}</span><span className="role-permission-state">{p.technician ? '✓' : '—'}</span>
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
            <p className="muted">4 vai trò — đồng bộ backend RBAC.</p>
          </div>
          <Badge>{PERMISSION_MATRIX.length} chức năng</Badge>
        </div>
        <div className="utility-table-wrap">
          <table className="table utility-table">
            <thead><tr><th>Chức năng</th><th>Mã quyền</th><th>ADMIN</th><th>OPERATOR</th><th>ACCOUNTANT</th><th>TECHNICIAN</th></tr></thead>
            <tbody>
              {PERMISSION_MATRIX.map((p) => (
                <tr key={p.perm}>
                  <td style={{ fontWeight: 600 }}>{p.label}</td>
                  <td style={{ fontFamily: 'ui-monospace, monospace', fontSize: 11, color: 'var(--muted)' }}>{p.perm}</td>
                  <td><Badge variant={p.admin ? 'success' : 'neutral'}>{p.admin ? '✓' : '✗'}</Badge></td>
                  <td><Badge variant={p.operator ? 'info' : 'neutral'}>{p.operator ? '✓' : '✗'}</Badge></td>
                  <td><Badge variant={p.accountant ? 'success' : 'neutral'}>{p.accountant ? '✓' : '✗'}</Badge></td>
                  <td><Badge variant={p.technician ? 'info' : 'neutral'}>{p.technician ? '✓' : '✗'}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="role-note">Frontend dùng <code>can(user, permission)</code> + <code>AppShell</code> lọc menu theo role; backend enforce cuối cùng qua <code>require_roles</code>.</div>
      </section>
    </div>
  )
}
