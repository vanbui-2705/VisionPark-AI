import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { auditApi, parkingTransactionsApi } from '../../api/services.ts'
import { can } from '../../lib/permissions.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import type { AuditLog, ParkingTransaction } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

function sanitize(obj: unknown): unknown {
  if (!obj || typeof obj !== 'object') return obj
  const o = obj as Record<string, unknown>
  const out: Record<string, unknown> = { ...o }
  for (const k of ['password', 'password_hash', 'hash', 'jwt', 'access_token', 'secret', 'token']) if (k in out) out[k] = '[REDACTED]'
  return out
}

const SOURCE_LABEL: Record<string, string> = { AI_ACCEPTED: 'AI được xác nhận', OPERATOR_CORRECTED: 'Sửa biển số', MANUAL_ENTRY: 'Nhập tay', STATION_AUTO: 'Tự động (Station)', OPERATOR_MANUAL: 'Thủ công (Operator)' }

export function ParkingDetailPage() {
  const { user } = useAuth()
  const { id } = useParams()
  const [tx, setTx] = useState<ParkingTransaction | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [audit, setAudit] = useState<AuditLog[]>([])

  useEffect(() => {
    if (!id) return
    parkingTransactionsApi.get(id).then(setTx).catch((e: unknown) => setErr(e instanceof Error ? e.message : translate("Không tải được chi tiết."))).finally(() => setLoading(false))
    auditApi.list({ resource_id: id, limit: 100 }).then(setAudit).catch(() => setAudit([]))
  }, [id])

  if (loading) return <Skeleton lines={6} />
  if (err) return <Alert variant="error">{err}</Alert>
  if (!tx) return <Alert variant="info">{translate("Không tìm thấy giao dịch.")}</Alert>

  const statusVariant = tx.status === 'PARKED' ? 'success' : tx.status === 'COMPLETED' ? 'neutral' : 'danger'

  return (
    <div className="data-page">
      <Breadcrumb items={[{ label: translate("Lịch sử đỗ xe"), to: '/parking' }, { label: tx.license_plate }]} />

      <section className="data-hero data-hero--forest">
        <div className="data-hero-copy">
          <span className="data-kicker">PARKING SESSION · {SOURCE_LABEL[tx.source] ?? tx.source}</span>
          <h2>{tx.license_plate}</h2>
          <p>{new Date(tx.check_in_time).toLocaleString('vi-VN')} · {tx.lane_name ?? tx.lane_id}</p>
        </div>
        <div className="row-actions">
          <Badge variant={statusVariant as never}>{tx.status}</Badge>
          {tx.is_manual_override ? <Badge variant="warning">{translate("sửa tay")}</Badge> : <Badge variant="info">AI</Badge>}
          {tx.detection_id && can(user, 'detections.read') ? <Link to={`/detections/${tx.detection_id}`} className="btn btn-secondary">Xem detection</Link> : null}
          <Link to="/parking" className="btn btn-secondary">{translate("Quay lại")}</Link>
        </div>
      </section>

      <div className="grid-2">
        <section className="utility-panel">
          <span className="utility-section-kicker">{translate("Biển số & nguồn")}</span>
          <ul className="role-permission-list" style={{ marginTop: 12 }}>
            <li className="role-permission-row"><span>Final plate</span><strong className="data-mono">{tx.license_plate}</strong></li>
            <li className="role-permission-row"><span>AI plate</span><span className="data-mono">{tx.original_ai_plate ?? '—'}</span></li>
            <li className="role-permission-row"><span>Normalized</span><span className="data-mono">{tx.normalized_plate}</span></li>
            <li className="role-permission-row"><span>Confidence</span><span>{tx.confidence != null ? `${Math.round(tx.confidence * 100)}%` : '—'}</span></li>
            <li className="role-permission-row"><span>{translate("Sửa tay")}</span>{tx.is_manual_override ? <Badge variant="warning">{translate("Có")}</Badge> : <Badge>{translate("Không")}</Badge>}</li>
          </ul>
        </section>

        <section className="utility-panel">
          <span className="utility-section-kicker">{translate("Vận hành")}</span>
          <ul className="role-permission-list" style={{ marginTop: 12 }}>
            <li className="role-permission-row"><span>{translate("Làn")}</span><strong>{tx.lane_name ?? tx.lane_id}</strong></li>
            <li className="role-permission-row"><span>Lane ID</span><span className="data-mono" style={{ fontSize: 12 }}>{tx.lane_id}</span></li>
            <li className="role-permission-row"><span>{translate("Nhân viên")}</span><span>{tx.check_in_operator_name ?? '—'}</span></li>
            <li className="role-permission-row"><span>{translate("ID giao dịch")}</span><span className="data-mono" style={{ fontSize: 11 }}>{tx.id.slice(0, 8)}…</span></li>
            <li className="role-permission-row"><span>Detection</span>{tx.detection_id && can(user, 'detections.read') ? <Link to={`/detections/${tx.detection_id}`} className="data-inline-action" style={{ fontSize: 12 }}>{tx.detection_id.slice(0, 8)}…</Link> : <span>{tx.detection_id ? `${tx.detection_id.slice(0, 8)}…` : '—'}</span>}</li>
          </ul>
          {tx.notes ? <div className="utility-callout" style={{ marginTop: 12 }}><div style={{ fontSize: 11, marginBottom: 4 }}>{translate("Ghi chú")}</div><div>{tx.notes}</div></div> : null}
        </section>
      </div>

      <section className="utility-table-panel">
        <div className="utility-panel-head">
          <div>
            <span className="utility-section-kicker">AUDIT TRAIL · {tx.id}</span>
            <h3>Audit — AI plate / Final plate / Actor / Source / Timestamp</h3>
            <p className="muted">{translate("Vết kiểm toán liên kết theo resource_id =")}{tx.id}</p>
          </div>
          <Badge variant={audit.length ? 'info' : 'neutral'}>{audit.length} {translate("bản ghi")}</Badge>
        </div>

        {audit.length === 0 ? <div style={{ padding: 24 }}><p className="muted" style={{ margin: 0 }}>{translate("Chưa có audit cho giao dịch này.")}</p></div> : (
          <div style={{ padding: 24, display: 'grid', gap: 16 }}>
            <div className="utility-table-wrap">
              <table className="table utility-table">
                <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Source</th><th>Correlation</th></tr></thead>
                <tbody>{audit.map((r) => (
                  <tr key={r.id}>
                    <td className="data-time">{new Date(r.time).toLocaleString('vi-VN')}</td>
                    <td><strong>{r.actor}</strong></td><td><Badge>{r.action}</Badge></td><td>{r.source ?? '—'}</td><td className="data-mono" style={{ fontSize: 11 }}>{r.correlation_id ?? '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            {audit.map((r) => (
              <div key={r.id} className="grid-2">
                <div><div className="utility-section-kicker" style={{ marginBottom: 6 }}>Before</div><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(sanitize(r.before), null, 2) ?? '—'}</pre></div>
                <div><div className="utility-section-kicker" style={{ marginBottom: 6 }}>After</div><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(sanitize(r.after), null, 2) ?? '—'}</pre></div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
