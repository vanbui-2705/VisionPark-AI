import { PERMISSION_MATRIX } from '../../lib/permissions.ts'

export function RolesPage() {
  return (
    <div>
      <h2>Vai trò & phân quyền</h2>
      <div className="grid-2" style={{marginTop:12}}>
        <section className="card">
          <h3>ADMIN — Toàn quyền quản trị</h3>
          <ul>{PERMISSION_MATRIX.filter(p=>p.admin).map(p=> <li key={p.perm}>✓ {p.label}</li>)}</ul>
        </section>
        <section className="card">
          <h3>OPERATOR — Nhân viên vận hành</h3>
          <ul>{PERMISSION_MATRIX.map(p=> <li key={p.perm}>{(p.operator?'✓ ':'✗ ') + p.label} {p.perm==='lanes.read'?' (Read Only)':''}</li>)}</ul>
        </section>
      </div>
      <section className="card" style={{marginTop:12}}>
        <h3>Permission matrix</h3>
        <table className="table"><thead><tr><th>Chức năng</th><th>ADMIN</th><th>OPERATOR</th></tr></thead><tbody>{PERMISSION_MATRIX.map(p=> <tr key={p.perm}><td>{p.label}</td><td>{p.admin?'✓':'✗'}</td><td>{p.operator?'✓':'✗'}</td></tr>)}</tbody></table>
        <p className="muted">RBAC Phase 1 chỉ 2 role. Frontend dùng helper can(user, permission) — derive từ CurrentUser.role, backend là authority.</p>
      </section>
    </div>
  )
}
