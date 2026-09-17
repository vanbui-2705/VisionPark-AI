import { useEffect, useState } from 'react'
import { auditApi } from '../../api/services.ts'
import type { AuditLog } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'

function sanitize(obj: unknown): unknown {
  if (!obj || typeof obj !== 'object') return obj
  const o = obj as Record<string, unknown>
  const out: Record<string, unknown> = {...o}
  for (const k of ['password','password_hash','hash','jwt','access_token','secret','token']) if (k in out) out[k]='[REDACTED]'
  return out
}

export function AuditLogsPage() {
  const [data,setData]=useState<AuditLog[]|null>(null)
  const [err,setErr]=useState<string|null>(null)
  const [loading,setLoading]=useState(true)
  const [expanded,setExpanded]=useState<string|null>(null)
  useEffect(()=>{ auditApi.list({limit:50}).then(setData).catch(e=> setErr(e instanceof Error?e.message:'Không tải được audit logs')).finally(()=> setLoading(false)) },[])
  if (loading) return <Spinner />
  if (err) return <Alert variant="error">{err}</Alert>
  if (!data || data.length===0) return <EmptyState title="Chưa có audit logs" />
  return (
    <div>
      <h2>Audit Logs</h2>
      <table className="table">
        <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Resource</th><th>ID</th><th>Correlation</th><th></th></tr></thead>
        <tbody>{data.map(r=> (
          <tr key={r.id}>
            <td>{new Date(r.time).toLocaleString('vi-VN')}</td>
            <td>{r.actor}</td><td>{r.action}</td><td>{r.resource}</td><td>{r.resource_id}</td><td>{r.correlation_id??'—'}</td>
            <td><button className="btn btn-ghost btn-sm" onClick={()=> setExpanded(expanded===r.id?null:r.id)}>{expanded===r.id?'Thu gọn':'Chi tiết'}</button></td>
          </tr>
        ))}</tbody>
      </table>
      {expanded ? (()=>{ const row=data.find(x=>x.id===expanded); if (!row) return null; return (
        <section className="card" style={{marginTop:12}}>
          <h3>Before</h3><pre className="code-block">{JSON.stringify(sanitize(row.before),null,2)??'—'}</pre>
          <h3>After</h3><pre className="code-block">{JSON.stringify(sanitize(row.after),null,2)??'—'}</pre>
        </section>
      )})():null}
    </div>
  )
}
