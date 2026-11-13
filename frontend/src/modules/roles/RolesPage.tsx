import { t as translate } from "../../lib/i18n"
import { PERMISSION_MATRIX } from '../../lib/permissions.ts'
import { useEffect, useState } from 'react'
import { rolesApi } from '../../api/services.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'

export function RolesPage() {
  const [roles, setRoles] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    rolesApi
      .list()
      .then((rows) => setRoles(rows.map((row) => row.name)))
      .catch((error) =>
        setError(error instanceof Error ? error.message : translate("Không tải được vai trò."))
      )
  }, [])
  const adminCount = PERMISSION_MATRIX.filter((p) => p.admin).length
  const buildingAdminCount = PERMISSION_MATRIX.filter((p) => p.buildingAdmin).length
  const operatorCount = PERMISSION_MATRIX.filter((p) => p.operator).length
  const accountantCount = PERMISSION_MATRIX.filter((p) => p.accountant).length

  return (
    <div className="utility-page">
      <Breadcrumb items={[{ label: translate("Phân quyền") }, { label: translate("Vai trò") }]} />
      {error && <Alert variant="error">{error}</Alert>}

      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">RBAC · VisionPark</span>
          <h1>{translate("Vai trò & phân quyền")}</h1>
          <p>
            {translate("Vai trò trong hệ thống:")}{" "}
            {roles.join(', ') || translate("Đang tải…")}
            . SYSTEM_ADMIN quản trị toàn hệ thống; BUILDING_ADMIN quản lý tòa nhà; OPERATOR vận hành cổng; ACCOUNTANT đối soát.
          </p>
        </div>
        <div className="utility-stat-row">
          <div className="utility-hero-stat"><strong>{adminCount}</strong><span>ADMIN · {translate("quyền")}</span></div>
          <div className="utility-hero-stat"><strong>{buildingAdminCount}</strong><span>BUILDING_ADMIN · {translate("quyền")}</span></div>
          <div className="utility-hero-stat"><strong>{operatorCount}</strong><span>OPERATOR · {translate("quyền")}</span></div>
          <div className="utility-hero-stat"><strong>{accountantCount}</strong><span>ACCOUNTANT · {translate("quyền")}</span></div>
        </div>
      </section>

      <div className="role-card-grid">
        <section className="utility-panel role-panel role-panel--admin">
          <div className="role-panel-head">
            <div>
              <span className="utility-section-kicker">SYSTEM AUTHORITY</span>
              <h3>SYSTEM_ADMIN</h3>
            </div>
            <Badge variant="success">{translate("Toàn quyền")}</Badge>
          </div>
          <p className="muted">Quản trị tòa nhà, người dùng hệ thống, audit, ALPR và tài liệu vận hành.</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.filter((p) => p.admin).map((p) => (
              <div key={p.perm} className="role-permission-row">
                <span>{translate(p.label)}</span>
                <code>{p.perm}</code>
              </div>
            ))}
          </div>
        </section>

        <section className="utility-panel role-panel role-panel--admin">
          <div className="role-panel-head">
            <div><span className="utility-section-kicker">BUILDING AUTHORITY</span><h3>BUILDING_ADMIN</h3></div>
            <Badge variant="info">Quản trị tòa nhà</Badge>
          </div>
          <p className="muted">Quản lý làn, nhân sự, cấu hình và vận hành trong đúng tòa nhà được gán.</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.map((p) => (
              <div key={p.perm} className={`role-permission-row ${p.buildingAdmin ? '' : 'is-unavailable'}`}>
                <span>{translate(p.label)}</span><span className="role-permission-state">{p.buildingAdmin ? '✓' : '✗'}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="utility-panel role-panel role-panel--operator">
          <div className="role-panel-head">
            <div>
              <span className="utility-section-kicker">GATE OPERATIONS</span>
              <h3>OPERATOR</h3>
            </div>
            <Badge variant="info">{translate("Vận hành")}</Badge>
          </div>
          <p className="muted">{translate("Quét biển số, xác nhận, xem lịch sử, cấu hình cá nhân.")}</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.map((p) => (
              <div key={p.perm} className={`role-permission-row ${p.operator ? '' : 'is-unavailable'}`}>
                <span>{translate(p.label)}</span>
                <span className="role-permission-state">{p.operator ? '✓' : '✗'}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="utility-panel role-panel">
          <div className="role-panel-head">
            <div>
              <span className="utility-section-kicker">FINANCE & AUDIT</span>
              <h3>ACCOUNTANT</h3>
            </div>
            <Badge variant="success">{translate("Kế toán")}</Badge>
          </div>
          <p className="muted">{translate("Dashboard, lịch sử đỗ xe, audit logs, hồ sơ và thông báo.")}</p>
          <div className="role-permission-list">
            {PERMISSION_MATRIX.map((p) => (
              <div key={p.perm} className={`role-permission-row ${p.accountant ? '' : 'is-unavailable'}`}>
                <span>{translate(p.label)}</span>
                <span className="role-permission-state">{p.accountant ? '✓' : '✗'}</span>
              </div>
            ))}
          </div>
        </section>

      </div>

      <section className="utility-table-panel">
        <div className="utility-panel-head">
          <div>
            <span className="utility-section-kicker">ACCESS COMPARISON</span>
            <h3>{translate("Ma trận phân quyền chi tiết")}</h3>
            <p className="muted">{translate("So sánh quyền của bốn vai trò hiện có.")}</p>
          </div>
          <Badge>{PERMISSION_MATRIX.length} {translate("chức năng")}</Badge>
        </div>
        <div className="utility-table-wrap">
          <table className="table utility-table">
            <thead>
              <tr>
                <th>{translate("Chức năng")}</th>
                <th>Permission</th>
                <th>SYSTEM_ADMIN</th>
                <th>BUILDING_ADMIN</th>
                <th>OPERATOR</th>
                <th>ACCOUNTANT</th>
              </tr>
            </thead>
            <tbody>
              {PERMISSION_MATRIX.map((p) => (
                <tr key={p.perm}>
                  <td style={{ fontWeight: 500 }}>{translate(p.label)}</td>
                  <td className="data-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>{p.perm}</td>
                  <td><Badge variant={p.admin ? 'success' : 'neutral'}>{p.admin ? '✓' : '✗'}</Badge></td>
                  <td><Badge variant={p.buildingAdmin ? 'info' : 'neutral'}>{p.buildingAdmin ? '✓' : '✗'}</Badge></td>
                  <td><Badge variant={p.operator ? 'info' : 'neutral'}>{p.operator ? '✓' : '✗'}</Badge></td>
                  <td><Badge variant={p.accountant ? 'success' : 'neutral'}>{p.accountant ? '✓' : '✗'}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="role-note">
          {translate("Frontend dùng helper ")}
          <code>can(user, permission)</code>
          {translate(" để ẩn/hiện UI. Backend vẫn enforce cuối cùng trên mọi API.")}
        </div>
      </section>
    </div>
  )
}
