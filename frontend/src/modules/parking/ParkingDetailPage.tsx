import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { auditApi, parkingTransactionsApi } from '../../api/services.ts'
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

export function ParkingDetailPage() {
  const { id } = useParams()
  const [tx, setTx] = useState<ParkingTransaction | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [audit, setAudit] = useState<AuditLog[]>([])

  useEffect(() => {
    if (!id) return
    parkingTransactionsApi.get(id).then(setTx).catch((e: unknown) => setErr(e instanceof Error ? e.message : 'Không tải được chi tiết.')).finally(() => setLoading(false))
    auditApi.list({ limit: 100 }).then((rows) => setAudit(rows.filter((r) => r.resource_id === id))).catch(() => setAudit([]))
  }, [id])

  if (loading) return <Skeleton lines={6} />
  if (err) return <Alert variant="error">{err}</Alert>
  if (!tx) return <Alert variant="info">Không tìm thấy giao dịch.</Alert>

  return (
    <div>
      <Breadcrumb items={[{ label: 'Lịch sử đỗ xe', to: '/parking' }, { label: 'Chi tiết' }]} />
      <div className="page-head">
        <h2>Giao dịch <span className="plate" style={{ fontSize: 20 }}>{tx.license_plate}</span> <Badge>{tx.status}</Badge></h2>
        <p className="muted">{new Date(tx.check_in_time).toLocaleString('vi-VN')} — Duy Anh</p>
      </div>
      <section className="card">
        <h3>Thông tin check-in</h3>
        <ul className="kv">
          <li><b>Biển số:</b> {tx.license_plate}</li>
          <li><b>AI plate:</b> {tx.original_ai_plate ?? '—'}</li>
          <li><b>Normalized:</b> {tx.normalized_plate}</li>
          <li><b>Sửa tay:</b> {tx.is_manual_override ? 'Có' : 'Không'}</li>
          <li><b>Nguồn:</b> {tx.source}</li>
          <li><b>Làn:</b> {tx.lane_name ?? tx.lane_id}</li>
          <li><b>Nhân viên:</b> {tx.check_in_operator_name ?? '—'}</li>
          <li><b>Ghi chú:</b> {tx.notes ?? '—'}</li>
          <li><b>Confidence:</b> {tx.confidence != null ? `${Math.round(tx.confidence * 100)}%` : '—'}</li>
          <li><b>Detection:</b> {tx.detection_id ? <Link to={`/detections/${tx.detection_id}`}>{tx.detection_id}</Link> : '—'}</li>
        </ul>
      </section>
      <section className="card" style={{ marginTop: 12 }}>
        <h3>Audit — AI plate / Final plate / Actor / Source / Timestamp</h3>
        {audit.length === 0 ? <p className="muted">Chưa có audit cho giao dịch này.</p> : (
          <table className="table">
            <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Source</th><th>Correlation</th></tr></thead>
            <tbody>{audit.map((r) => (
              <tr key={r.id}>
                <td>{new Date(r.time).toLocaleString('vi-VN')}</td>
                <td>{r.actor}</td><td>{r.action}</td><td>{r.source ?? '—'}</td><td>{r.correlation_id ?? '—'}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
        {audit.map((r) => (
          <div key={r.id} style={{ marginTop: 8 }}>
            <h4>Before</h4><pre className="code-block">{JSON.stringify(sanitize(r.before), null, 2) ?? '—'}</pre>
            <h4>After</h4><pre className="code-block">{JSON.stringify(sanitize(r.after), null, 2) ?? '—'}</pre>
          </div>
        ))}
      </section>
    </div>
  )
}
