import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { auditApi, parkingTransactionsApi } from '../../api/services.ts'
import type { AuditLog, ParkingTransaction } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { ApiError } from '../../api/errors.ts'

function sanitize(obj: unknown): unknown {
  if (!obj || typeof obj !== 'object') return obj
  const o = obj as Record<string, unknown>
  const out: Record<string, unknown> = { ...o }
  for (const k of ['password', 'password_hash', 'hash', 'jwt', 'access_token', 'secret', 'token']) if (k in out) out[k] = '[REDACTED]'
  return out
}

const SOURCE_LABEL: Record<string, string> = { STATION_AUTO: 'Tự động (Station)', OPERATOR_MANUAL: 'Thủ công (Operator)' }

export function ParkingDetailPage() {
  const { id } = useParams()
  const [tx, setTx] = useState<ParkingTransaction | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [errStatus, setErrStatus] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [audit, setAudit] = useState<AuditLog[]>([])

  useEffect(() => {
    if (!id) return
    let alive = true
    parkingTransactionsApi.get(id).then((v) => { if (alive) setTx(v) }).catch((e: unknown) => {
      if (!alive) return
      setErr(e instanceof Error ? e.message : 'Không tải được chi tiết.')
      if (e instanceof ApiError) setErrStatus(e.status)
    }).finally(() => { if (alive) setLoading(false) })
    auditApi.list({ q: id, page: 0, pageSize: 100 }).then((res) => { if (alive) setAudit(res.items) }).catch(() => { if (alive) setAudit([]) })
    return () => { alive = false }
  }, [id])

  if (loading) return <Skeleton lines={6} />
  if (err) {
    if (errStatus === 404) return <Alert variant="error">Không tìm thấy giao dịch.</Alert>
    if (errStatus === 403) return <Alert variant="error">Bạn không có quyền xem giao dịch này.</Alert>
    if (errStatus === 401) return <Alert variant="error">Vui lòng đăng nhập lại.</Alert>
    return <Alert variant="error">{err}</Alert>
  }
  if (!tx) return <Alert variant="info">Không tìm thấy giao dịch.</Alert>

  const statusVariant = tx.status === 'PARKED' ? 'success' : tx.status === 'COMPLETED' ? 'neutral' : 'danger'

  return (
    <div className="data-page parking-detail-page">
      <Breadcrumb items={[{ label: 'Lịch sử đỗ xe', to: '/parking' }, { label: tx.license_plate }]} />

      <section className="data-hero data-hero--forest parking-detail-hero">
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <div style={{ width: 56, height: 56, borderRadius: 14, background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)', display: 'grid', placeItems: 'center', fontSize: 22 }}>P</div>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 800, letterSpacing: '0.08em', fontSize: 22, background: '#fff', color: '#0f172a', borderRadius: 10, padding: '4px 10px' }}>{tx.license_plate}</span>
              <Badge variant={statusVariant as never}>{tx.status}</Badge>
              {tx.is_manual_override ? <Badge variant="warning">sửa tay</Badge> : <Badge variant="info">AI</Badge>}
            </div>
            <div style={{ fontSize: 12, opacity: 0.75, marginTop: 6 }}>{new Date(tx.check_in_time).toLocaleString('vi-VN')} · Duy Anh · {SOURCE_LABEL[tx.source] ?? tx.source}</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {tx.detection_id ? <Link to={`/detections/${tx.detection_id}`} className="btn btn-sm" style={{ textDecoration: 'none', background: '#fff', color: '#0f172a', borderColor: '#fff' }}>Xem detection</Link> : null}
          <Link to="/parking" className="btn btn-sm" style={{ textDecoration: 'none', background: 'transparent', color: '#fff', borderColor: 'rgba(255,255,255,0.35)' }}>Quay lại</Link>
        </div>
      </section>

      <div className="parking-detail-grid">
        <section className="data-table-card parking-detail-card">
          <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Biển số & nguồn</div>
          <div style={{ display: 'grid', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)', fontSize: 13 }}>Final plate</span><strong style={{ fontFamily: 'ui-monospace, monospace' }}>{tx.license_plate}</strong></div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)', fontSize: 13 }}>AI plate</span><span style={{ fontFamily: 'ui-monospace, monospace', color: tx.original_ai_plate ? 'var(--text)' : 'var(--muted)' }}>{tx.original_ai_plate ?? '—'}</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)', fontSize: 13 }}>Normalized</span><span style={{ fontFamily: 'ui-monospace, monospace' }}>{tx.normalized_plate}</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)', fontSize: 13 }}>Confidence</span><span>{tx.confidence != null ? `${Math.round(tx.confidence * 100)}%` : '—'}</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)', fontSize: 13 }}>Sửa tay</span>{tx.is_manual_override ? <Badge variant="warning">Có</Badge> : <Badge>Không</Badge>}</div>
          </div>
        </section>

        <section className="data-table-card parking-detail-card">
          <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Vận hành</div>
          <div style={{ display: 'grid', gap: 10, fontSize: 13 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Làn</span><strong>{tx.lane_name ?? tx.lane_id}</strong></div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Lane ID</span><span style={{ fontFamily: 'ui-monospace, monospace', fontSize: 12 }}>{tx.lane_id}</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Nhân viên</span><span>{tx.check_in_operator_name ?? '—'}</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>ID giao dịch</span><span style={{ fontFamily: 'ui-monospace, monospace', fontSize: 11 }}>{tx.id.slice(0, 8)}…</span></div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Detection</span>{tx.detection_id ? <Link to={`/detections/${tx.detection_id}`} style={{ fontSize: 12 }}>{tx.detection_id.slice(0, 8)}…</Link> : <span>—</span>}</div>
            {tx.notes ? <div style={{ background: '#f8fafc', border: '1px solid var(--border)', borderRadius: 10, padding: 10 }}><div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Ghi chú</div><div>{tx.notes}</div></div> : null}
          </div>
        </section>
      </div>

      <section className="data-table-card parking-audit-card">
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontWeight: 800 }}>Audit — AI plate / Final plate / Actor / Source / Timestamp</div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>Vết kiểm toán liên kết theo resource_id = {tx.id}</div>
          </div>
          <Badge variant={audit.length ? 'info' : 'neutral'}>{audit.length} bản ghi</Badge>
        </div>

        {audit.length === 0 ? <div style={{ padding: 18 }}><p className="muted" style={{ margin: 0 }}>Chưa có audit cho giao dịch này.</p></div> : (
          <div style={{ padding: 14, display: 'grid', gap: 12 }}>
            <div style={{ overflow: 'auto', border: '1px solid var(--border)', borderRadius: 10 }}>
              <table className="table" style={{ margin: 0 }}>
                <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Source</th><th>Correlation</th></tr></thead>
                <tbody>{audit.map((r) => (
                  <tr key={r.id}>
                    <td style={{ whiteSpace: 'nowrap', fontSize: 12 }}>{new Date(r.time).toLocaleString('vi-VN')}</td>
                    <td><strong>{r.actor}</strong></td><td><Badge>{r.action}</Badge></td><td>{r.source ?? '—'}</td><td style={{ fontFamily: 'ui-monospace, monospace', fontSize: 11 }}>{r.correlation_id ?? '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            {audit.map((r) => (
              <div key={r.id} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div><div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 6 }}>Before</div><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(sanitize(r.before), null, 2) ?? '—'}</pre></div>
                <div><div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 6 }}>After</div><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(sanitize(r.after), null, 2) ?? '—'}</pre></div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
