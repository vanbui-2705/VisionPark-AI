import { useEffect, useState } from 'react'
import { auditApi } from '../../api/services.ts'
import type { AuditLog } from '../../api/domain.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'

function sanitize(obj: unknown): unknown {
  if (!obj || typeof obj !== 'object') return obj
  const o = obj as Record<string, unknown>
  const out: Record<string, unknown> = { ...o }
  for (const k of ['password', 'password_hash', 'hash', 'jwt', 'access_token', 'secret', 'token']) if (k in out) out[k] = '[REDACTED]'
  return out
}

export function AuditLogsPage() {
  const [data, setData] = useState<AuditLog[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  useEffect(() => { auditApi.list({ limit: 50 }).then(setData).catch((e) => setErr(e instanceof Error ? e.message : 'Không tải được audit logs')).finally(() => setLoading(false)) }, [])
  if (loading) return <Spinner />
  if (err) return <Alert variant="error">{err}</Alert>

  return (
    <div className="data-page audit-page">
      <section className="data-hero data-hero--cream">
        <div className="data-hero-copy">
          <span className="data-kicker">NHẬT KÝ HỆ THỐNG · VISIONPARK</span>
          <h2>Nhật ký kiểm tra</h2>
          <p>Theo dõi người thực hiện, hành động, tài nguyên và mã tương quan. Dữ liệu nhạy cảm được ẩn khi hiển thị.</p>
        </div>
        <div className="data-hero-stat"><strong>{data?.length ?? 0}</strong><span>bản ghi</span></div>
      </section>

      {!data || data.length === 0 ? <EmptyState title="Chưa có nhật ký kiểm tra" /> : <>
      <section className="data-table-card">
        <div className="data-table-head">
          <div><span className="data-section-kicker">LỊCH SỬ THAO TÁC</span><h3>Hoạt động quản trị</h3></div>
          <span className="data-table-meta">{data.length} bản ghi</span>
        </div>
        <div className="table-wrap data-table-wrap">
          <table className="table data-table audit-table">
            <thead><tr><th>Thời gian</th><th>Người thực hiện</th><th>Hành động</th><th>Tài nguyên</th><th>Mã tài nguyên</th><th>Mã tương quan</th><th></th></tr></thead>
            <tbody>{data.map((r) => (
              <tr key={r.id}>
                <td className="data-time">{new Date(r.time).toLocaleString('vi-VN')}</td>
                <td><strong>{r.actor}</strong></td><td><Badge>{r.action}</Badge></td><td>{r.resource}</td><td className="data-mono">{r.resource_id}</td><td className="data-mono">{r.correlation_id ?? '—'}</td>
                <td><button className="btn btn-ghost btn-sm" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>{expanded === r.id ? 'Thu gọn' : 'Chi tiết'}</button></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>
      {expanded ? (() => { const row = data.find((x) => x.id === expanded); if (!row) return null; return (
        <section className="data-table-card audit-detail">
          <div className="data-table-head"><div><span className="data-section-kicker">BẢN GHI {row.id}</span><h3>Chi tiết nhật ký</h3></div></div>
          <div className="audit-detail-grid">
            <div><div className="data-section-kicker">TRƯỚC</div><pre className="code-block">{JSON.stringify(sanitize(row.before), null, 2) ?? '—'}</pre></div>
            <div><div className="data-section-kicker">SAU</div><pre className="code-block">{JSON.stringify(sanitize(row.after), null, 2) ?? '—'}</pre></div>
          </div>
        </section>
      ) })() : null}
      </>}
    </div>
  )
}
