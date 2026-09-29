import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

export function PermissionsPage() {
  const admin = PERMISSION_MATRIX.filter((r) => r.admin).length
  const operator = PERMISSION_MATRIX.filter((r) => r.operator).length

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Phân quyền' }]} />

      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Access Matrix · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Ma trận phân quyền</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Chỉ đọc — frontend dùng helper can(user, perm), backend vẫn là authority cuối cùng.</p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, padding: '10px 14px', minWidth: 110 }}><div style={{ fontSize: 11, opacity: 0.75 }}>Permissions</div><div style={{ fontSize: 22, fontWeight: 800 }}>{PERMISSION_MATRIX.length}</div></div>
          <div style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, padding: '10px 14px', minWidth: 110 }}><div style={{ fontSize: 11, opacity: 0.75 }}>ADMIN</div><div style={{ fontSize: 22, fontWeight: 800 }}>{admin}</div></div>
          <div style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, padding: '10px 14px', minWidth: 110 }}><div style={{ fontSize: 11, opacity: 0.75 }}>OPERATOR</div><div style={{ fontSize: 22, fontWeight: 800 }}>{operator}</div></div>
        </div>
      </div>

      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden', boxShadow: '0 6px 18px rgba(15,23,42,0.06)' }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0 }}>Permission registry</h3>
            <p className="muted" style={{ margin: '4px 0 0', fontSize: 12 }}>Danh sách quyền dùng chung cho menu, route guard và UI action.</p>
          </div>
          <Badge variant="info">Readonly</Badge>
        </div>
        <div style={{ overflow: 'auto' }}>
          <table className="table" style={{ margin: 0 }}>
            <thead><tr><th>Permission</th><th>Mô tả</th><th>ADMIN</th><th>OPERATOR</th></tr></thead>
            <tbody>{PERMISSION_MATRIX.map((r) => <tr key={r.perm}><td><code>{r.perm}</code></td><td style={{ fontWeight: 600 }}>{r.label}</td><td><Badge variant={r.admin ? 'success' : 'neutral'}>{r.admin ? '✓' : '—'}</Badge></td><td><Badge variant={r.operator ? 'info' : 'neutral'}>{r.operator ? '✓' : '—'}</Badge></td></tr>)}</tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
