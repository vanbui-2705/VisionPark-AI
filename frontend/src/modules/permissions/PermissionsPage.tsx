import { t as translate } from "../../lib/i18n"
import { can, PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

export function PermissionsPage() {
  const admin = PERMISSION_MATRIX.filter((r) => r.admin).length
  const operator = PERMISSION_MATRIX.filter((r) => r.operator).length

  return (
    <div className="utility-page">
      <Breadcrumb items={[{ label: translate("Phân quyền") }]} />

      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Access Matrix · Duy Anh</span>
          <h1>{translate("Ma trận phân quyền")}</h1>
          <p>{translate("Chỉ đọc — frontend dùng helper can(user, perm), backend vẫn là authority cuối cùng.")}</p>
        </div>
        <div className="utility-stat-row">
          <div className="utility-hero-stat"><strong>{PERMISSION_MATRIX.length}</strong><span>Permissions</span></div>
          <div className="utility-hero-stat"><strong>{admin}</strong><span>ADMIN</span></div>
          <div className="utility-hero-stat"><strong>{operator}</strong><span>OPERATOR</span></div>
        </div>
      </section>

      <section className="utility-table-panel">
        <div className="utility-panel-head">
          <div>
            <span className="utility-section-kicker">RBAC REGISTRY</span>
            <h3>Permission registry</h3>
            <p className="muted">{translate("Danh sách quyền dùng chung cho menu, route guard và UI action.")}</p>
          </div>
          <Badge variant="info">Readonly</Badge>
        </div>
        <div className="utility-table-wrap">
          <table className="table utility-table">
            <thead><tr><th>Permission</th><th>{translate("Mô tả")}</th><th>ADMIN</th><th>OPERATOR</th><th>ACCOUNTANT</th><th>TECHNICIAN</th></tr></thead>
            <tbody>{PERMISSION_MATRIX.map((r) => <tr key={r.perm}><td><code>{r.perm}</code></td><td style={{ fontWeight: 500 }}>{translate(r.label)}</td><td><Badge variant={r.admin ? 'success' : 'neutral'}>{r.admin ? '✓' : '—'}</Badge></td><td><Badge variant={r.operator ? 'info' : 'neutral'}>{r.operator ? '✓' : '—'}</Badge></td>{(["ACCOUNTANT", "TECHNICIAN"] as const).map(role => <td key={role}>{can({ id: "", username: "", display_name: "", active: true, role }, r.perm) ? "yes" : "-"}</td>)}</tr>)}</tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
