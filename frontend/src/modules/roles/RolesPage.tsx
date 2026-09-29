import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'

export function RolesPage() {
  const adminCount = PERMISSION_MATRIX.filter((p) => p.admin).length
  const operatorCount = PERMISSION_MATRIX.filter((p) => p.operator).length

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Phân quyền' }, { label: 'Vai trò' }]} />

      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>RBAC · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Vai trò & phân quyền</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Phase 1: ADMIN / OPERATOR. Frontend suy ra từ CurrentUser.role, backend là authority cuối cùng.</p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, padding: '10px 14px', minWidth: 110 }}>
            <div style={{ fontSize: 11, opacity: 0.75 }}>ADMIN</div>
            <div style={{ fontSize: 20, fontWeight: 800 }}>{adminCount} quyền</div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, padding: '10px 14px', minWidth: 110 }}>
            <div style={{ fontSize: 11, opacity: 0.75 }}>OPERATOR</div>
            <div style={{ fontSize: 20, fontWeight: 800 }}>{operatorCount} quyền</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px,1fr))', gap: 14 }}>
        <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 6px 18px rgba(15,23,42,0.06)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h3 style={{ margin: 0 }}>ADMIN</h3>
            <Badge variant="success">Toàn quyền</Badge>
          </div>
          <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>Cấu hình hệ thống, quản lý làn, người dùng, audit, ALPR.</p>
          <div style={{ display: 'grid', gap: 6, marginTop: 12 }}>
            {PERMISSION_MATRIX.filter((p) => p.admin).map((p) => (
              <div key={p.perm} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 10, background: '#f8fafc' }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{p.label}</span>
                <span style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'ui-monospace, monospace' }}>{p.perm}</span>
              </div>
            ))}
          </div>
        </section>

        <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 6px 18px rgba(15,23,42,0.06)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h3 style={{ margin: 0 }}>OPERATOR</h3>
            <Badge variant="info">Vận hành</Badge>
          </div>
          <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>Quét biển số, xác nhận, xem lịch sử, cấu hình cá nhân.</p>
          <div style={{ display: 'grid', gap: 6, marginTop: 12 }}>
            {PERMISSION_MATRIX.map((p) => (
              <div key={p.perm} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 10, background: p.operator ? '#fff' : '#f1f5f9', opacity: p.operator ? 1 : 0.9 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{p.label}</span>
                <span style={{ fontSize: 12 }}>{p.operator ? '✓' : '✗'}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden', boxShadow: '0 6px 18px rgba(15,23,42,0.06)' }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0 }}>Permission matrix</h3>
            <p className="muted" style={{ margin: '4px 0 0', fontSize: 12 }}>So sánh nhanh quyền giữa hai vai trò hiện có.</p>
          </div>
          <Badge>{PERMISSION_MATRIX.length} chức năng</Badge>
        </div>
        <div style={{ overflow: 'auto' }}>
          <table className="table" style={{ margin: 0 }}>
            <thead><tr><th>Chức năng</th><th>Permission</th><th>ADMIN</th><th>OPERATOR</th></tr></thead>
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
        <div style={{ padding: '10px 16px', background: '#f8fafc', borderTop: '1px solid var(--border)', fontSize: 12, color: 'var(--muted)' }}>
          Frontend dùng helper <code>can(user, permission)</code> để ẩn/hiện UI. Backend vẫn enforce cuối cùng trên mọi API.
        </div>
      </section>
    </div>
  )
}
