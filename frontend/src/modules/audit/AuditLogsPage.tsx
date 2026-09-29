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
  if (!data || data.length === 0) return <EmptyState title="Chưa có audit logs" />

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Audit Trail · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>Audit Logs</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>Theo dõi actor, action, resource và correlationId. Dữ liệu nhạy cảm được redact khi hiển thị.</p>
        </div>
        <Badge variant="info">{data.length} bản ghi</Badge>
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden', boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
        <div style={{ overflow: 'auto' }}>
          <table className="table" style={{ margin: 0 }}>
            <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Resource</th><th>ID</th><th>Correlation</th><th></th></tr></thead>
            <tbody>{data.map((r) => (
              <tr key={r.id}>
                <td style={{ whiteSpace: 'nowrap', fontSize: 12 }}>{new Date(r.time).toLocaleString('vi-VN')}</td>
                <td><strong>{r.actor}</strong></td><td><Badge>{r.action}</Badge></td><td>{r.resource}</td><td style={{ fontFamily: 'ui-monospace, monospace', fontSize: 11 }}>{r.resource_id}</td><td>{r.correlation_id ?? '—'}</td>
                <td><button className="btn btn-ghost btn-sm" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>{expanded === r.id ? 'Thu gọn' : 'Chi tiết'}</button></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
      {expanded ? (() => { const row = data.find((x) => x.id === expanded); if (!row) return null; return (
        <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
          <h3 style={{ marginTop: 0 }}>Audit detail</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px,1fr))', gap: 12 }}>
            <div><div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 6 }}>Before</div><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(sanitize(row.before), null, 2) ?? '—'}</pre></div>
            <div><div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: 6 }}>After</div><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(sanitize(row.after), null, 2) ?? '—'}</pre></div>
          </div>
        </section>
      ) })() : null}
    </div>
  )
}
