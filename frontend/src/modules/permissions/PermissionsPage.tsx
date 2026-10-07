import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

export function PermissionsPage() {
  const admin = PERMISSION_MATRIX.filter((r) => r.admin).length
  const operator = PERMISSION_MATRIX.filter((r) => r.operator).length

  return (
    <div className="utility-page permissions-page">
      <Breadcrumb items={[{ label: 'Phân quyền' }]} />

      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Danh mục quyền hạn · VisionPark</span>
          <h1>Ma trận phân quyền</h1>
          <p>Chế độ xem — hệ thống sử dụng quy tắc phân quyền để kiểm soát menu, giao diện và các hành động.</p>
        </div>
        <div className="utility-stat-row">
          <div className="utility-hero-stat"><strong>{PERMISSION_MATRIX.length}</strong><span>tổng quyền</span></div>
          <div className="utility-hero-stat"><strong>{admin}</strong><span>quản trị viên</span></div>
          <div className="utility-hero-stat"><strong>{operator}</strong><span>vận hành</span></div>
        </div>
      </section>

      <section className="utility-table-panel">
        <div className="utility-panel-head">
          <div>
            <span className="utility-section-kicker">ACCESS REGISTRY</span>
            <h3>Danh mục quyền chi tiết</h3>
            <p className="muted">Danh sách mã quyền áp dụng cho thanh điều hướng, tuyến đường và thao tác người dùng.</p>
          </div>
          <Badge variant="info">Chỉ xem</Badge>
        </div>
        <div className="utility-table-wrap">
          <table className="table utility-table">
            <thead><tr><th>Mã quyền</th><th>Mô tả chức năng</th><th>Quản trị viên</th><th>Vận hành</th></tr></thead>
            <tbody>{PERMISSION_MATRIX.map((r) => <tr key={r.perm}><td><code>{r.perm}</code></td><td style={{ fontWeight: 600 }}>{r.label}</td><td><Badge variant={r.admin ? 'success' : 'neutral'}>{r.admin ? '✓' : '—'}</Badge></td><td><Badge variant={r.operator ? 'info' : 'neutral'}>{r.operator ? '✓' : '—'}</Badge></td></tr>)}</tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
