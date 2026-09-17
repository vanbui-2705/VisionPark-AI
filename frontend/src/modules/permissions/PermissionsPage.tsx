import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
export function PermissionsPage() {
  return (
    <div>
      <Breadcrumb items={[{ label: 'Phân quyền' }]} />
      <h2>Ma trận phân quyền</h2>
      <p className="muted">Chỉ đọc — quyền suy ra từ role, backend là authority. Dùng helper can(user, perm).</p>
      <div className="table-wrap"><table className="table"><thead><tr><th>Permission</th><th>Mô tả</th><th>ADMIN</th><th>OPERATOR</th></tr></thead><tbody>{PERMISSION_MATRIX.map((r) => <tr key={r.perm}><td><code>{r.perm}</code></td><td>{r.label}</td><td>{r.admin ? '✓' : '—'}</td><td>{r.operator ? '✓' : '—'}</td></tr>)}</tbody></table></div>
    </div>
  )
}
