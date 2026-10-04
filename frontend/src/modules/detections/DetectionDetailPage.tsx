import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { detectionsApi, auditApi } from '../../api/services.ts'
import type { Detection, AuditLog } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

const TABS = ['Overview', 'Media', 'Audit', 'Raw Data'] as const

export function DetectionDetailPage() {
  const { id } = useParams()
  const [d, setD] = useState<Detection | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<(typeof TABS)[number]>('Overview')
  const [audit, setAudit] = useState<AuditLog[]>([])
  useEffect(() => {
    if (!id) return
    detectionsApi.get(id).then(setD).catch((e: unknown) => setErr(e instanceof Error ? e.message : 'Không tải được chi tiết.')).finally(() => setLoading(false))
    auditApi.list({ limit: 100 }).then((rows) => setAudit(rows.filter((r) => r.resource_id === id))).catch(() => setAudit([]))
  }, [id])
  if (loading) return <Skeleton lines={6} />
  if (err) return <Alert variant="error">{err}</Alert>
  if (!d) return <Alert variant="info">Không tìm thấy detection.</Alert>
  const plate = d.final_plate ?? d.normalized_plate ?? d.ai_plate ?? '—'
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'Lịch sử nhận diện', to: '/detections' }, { label: 'Chi tiết' }]} />
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 800, letterSpacing: '0.06em', background: '#fff', color: '#0f172a', borderRadius: 10, padding: '6px 12px', fontSize: 18 }}>{plate}</span>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}><Badge>{d.status}</Badge><span style={{ fontSize: 12, opacity: 0.75 }}>{new Date(d.created_at).toLocaleString('vi-VN')}</span></div>
            <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>{d.lane_name ?? d.lane_id} · {d.direction ?? '—'}</div>
          </div>
        </div>
        <Link to="/detections" className="btn btn-sm" style={{ textDecoration: 'none', background: '#fff', color: '#0f172a' }}>Quay lại</Link>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {TABS.map((t) => <button type="button" key={t} onClick={() => setTab(t)} style={{ padding: '8px 14px', borderRadius: 999, border: '1px solid var(--border)', background: t === tab ? '#0f172a' : 'var(--surface)', color: t === tab ? '#fff' : 'var(--text)', fontWeight: 600, fontSize: 13 }}>{t}</button>)}
      </div>

      {tab === 'Overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px,1fr))', gap: 14 }}>
          <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
            <div style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Kết quả AI</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8, fontSize: 13 }}>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Raw Plate</span><strong style={{ fontFamily: 'ui-monospace, monospace' }}>{d.ai_plate ?? '—'}</strong></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Normalized</span><strong style={{ fontFamily: 'ui-monospace, monospace' }}>{d.normalized_plate ?? '—'}</strong></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Confidence</span><span>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Processing</span><span>{d.processing_ms ?? '—'} ms</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Model</span><span>{d.model_version ?? '—'}</span></li>
            </ul>
          </section>
          <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
            <div style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Kết quả cuối</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8, fontSize: 13 }}>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Final Plate</span><strong style={{ fontFamily: 'ui-monospace, monospace' }}>{d.final_plate ?? d.normalized_plate ?? '—'}</strong></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Status</span><Badge>{d.status}</Badge></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Confirmed by</span><span>{d.confirmed_by ?? '—'}</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Confirmed at</span><span>{d.confirmed_at ? new Date(d.confirmed_at).toLocaleString('vi-VN') : '—'}</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Operator</span><span>{d.operator ?? '—'}</span></li>
            </ul>
          </section>
          <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
            <div style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Metadata</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8, fontSize: 13 }}>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>ID</span><code style={{ fontSize: 11 }}>{d.id}</code></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Lane</span><span>{d.lane_name ?? d.lane_id}</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Hướng</span><span>{d.direction ?? '—'}</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Created</span><span>{new Date(d.created_at).toLocaleString('vi-VN')}</span></li>
            </ul>
          </section>
        </div>
      )}
      {tab === 'Media' && (
        <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
          <h3 style={{ marginTop: 0 }}>Ảnh / khung hình</h3>
          {d.image_url ? <div style={{ position: 'relative', display: 'inline-block' }}><img src={d.image_url} alt="detection" style={{ maxWidth: '100%', borderRadius: 8, display: 'block' }} />{d.bbox ? <span style={{ position: 'absolute', left: `${d.bbox.x}%`, top: `${d.bbox.y}%`, width: `${d.bbox.w}%`, height: `${d.bbox.h}%`, border: '2px solid #22c55e', borderRadius: 4 }} title="AI bounding box" /> : null}</div> : <p className="muted">Không có ảnh.</p>}
          {d.bbox ? <p className="muted">BBox: {JSON.stringify(d.bbox)}</p> : null}
        </section>
      )}
      {tab === 'Audit' && (
        <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
          <h3 style={{ marginTop: 0 }}>Lịch sử audit liên quan</h3>
          {audit.length === 0 ? <p className="muted">Chưa có bản ghi audit cho detection này.</p> : <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 }}>{audit.map((a) => <li key={a.id} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 10, background: '#f8fafc', flexWrap: 'wrap' }}><span style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date((a as unknown as { time?: string }).time ?? 0).toLocaleString('vi-VN')}</span><b>{a.actor}</b><span>{a.action}</span><code>{a.resource}</code></li>)}</ul>}
        </section>
      )}
      {tab === 'Raw Data' && <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}><h3 style={{ marginTop: 0 }}>API JSON</h3><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(d, null, 2)}</pre></section>}
      <div style={{ display: 'flex', gap: 8 }}><Link to="/detections" className="btn">Quay lại lịch sử</Link><Button onClick={() => window.history.back()}>Mở lại trang trước</Button></div>
    </div>
  )
}
