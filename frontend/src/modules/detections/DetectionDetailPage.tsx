import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { detectionsApi, auditApi } from '../../api/services.ts'
import type { Detection, AuditLog } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { ApiError } from '../../api/errors.ts'

const TABS = ['Overview', 'Media', 'Audit', 'Raw Data'] as const

export function DetectionDetailPage() {
  const { id } = useParams()
  const [d, setD] = useState<Detection | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [errStatus, setErrStatus] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<(typeof TABS)[number]>('Overview')
  const [audit, setAudit] = useState<AuditLog[]>([])
  useEffect(() => {
    if (!id) return
    let alive = true
    detectionsApi.get(id).then((v) => { if (alive) setD(v) }).catch((e: unknown) => {
      if (!alive) return
      setErr(e instanceof Error ? e.message : 'Không tải được chi tiết.')
      if (e instanceof ApiError) setErrStatus(e.status)
    }).finally(() => { if (alive) setLoading(false) })
    auditApi.list({ q: id, page: 0, pageSize: 100 }).then((res) => { if (alive) setAudit(res.items) }).catch(() => { if (alive) setAudit([]) })
    return () => { alive = false }
  }, [id])
  if (loading) return <Skeleton lines={6} />
  if (err) {
    if (errStatus === 404) return <Alert variant="error">Không tìm thấy detection.</Alert>
    if (errStatus === 403) return <Alert variant="error">Bạn không có quyền xem detection này.</Alert>
    if (errStatus === 401) return <Alert variant="error">Vui lòng đăng nhập.</Alert>
    return <Alert variant="error">{err}</Alert>
  }
  if (!d) return <Alert variant="info">Không tìm thấy detection.</Alert>
  const plate = d.final_plate ?? d.normalized_plate ?? d.ai_plate ?? '—'
  return (
    <div className="data-page detection-detail-page">
      <Breadcrumb items={[{ label: 'Lịch sử nhận diện', to: '/detections' }, { label: 'Chi tiết' }]} />
      <section className="data-hero data-hero--forest detection-detail-hero">
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 800, letterSpacing: '0.06em', background: '#fff', color: '#0f172a', borderRadius: 10, padding: '6px 12px', fontSize: 18 }}>{plate}</span>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}><Badge>{d.status}</Badge><span style={{ fontSize: 12, opacity: 0.75 }}>{new Date(d.created_at).toLocaleString('vi-VN')}</span></div>
            <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>{d.lane_name ?? d.lane_id} · {d.direction ?? '—'}</div>
          </div>
        </div>
        <Link to="/detections" className="btn btn-sm" style={{ textDecoration: 'none', background: '#fff', color: '#0f172a' }}>Quay lại</Link>
      </section>

      <div className="detail-tabs">
        {TABS.map((t) => <button type="button" className={t === tab ? 'is-active' : ''} key={t} onClick={() => setTab(t)}>{t}</button>)}
      </div>

      {tab === 'Overview' && (
        <div className="detail-overview-grid">
          <section className="data-table-card detail-card">
            <div style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Kết quả AI</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8, fontSize: 13 }}>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Raw Plate</span><strong style={{ fontFamily: 'ui-monospace, monospace' }}>{d.ai_plate ?? '—'}</strong></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Normalized</span><strong style={{ fontFamily: 'ui-monospace, monospace' }}>{d.normalized_plate ?? '—'}</strong></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Confidence</span><span>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Processing</span><span>{d.processing_ms ?? '—'} ms</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Model</span><span>{d.model_version ?? '—'}</span></li>
            </ul>
          </section>
          <section className="data-table-card detail-card">
            <div style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Kết quả cuối</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8, fontSize: 13 }}>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Final Plate</span><strong style={{ fontFamily: 'ui-monospace, monospace' }}>{d.final_plate ?? d.normalized_plate ?? '—'}</strong></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Status</span><Badge>{d.status}</Badge></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Confirmed by</span><span>{d.confirmed_by ?? '—'}</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Confirmed at</span><span>{d.confirmed_at ? new Date(d.confirmed_at).toLocaleString('vi-VN') : '—'}</span></li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--muted)' }}>Operator</span><span>{d.operator ?? '—'}</span></li>
            </ul>
          </section>
          <section className="data-table-card detail-card">
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
        <section className="data-table-card detail-card detail-media-card">
          <h3 style={{ marginTop: 0 }}>Ảnh / khung hình</h3>
          {d.image_url ? <div style={{ position: 'relative', display: 'inline-block' }}><img src={d.image_url} alt="detection" style={{ maxWidth: '100%', borderRadius: 8, display: 'block' }} />{d.bbox ? <span style={{ position: 'absolute', left: `${d.bbox.x}%`, top: `${d.bbox.y}%`, width: `${d.bbox.w}%`, height: `${d.bbox.h}%`, border: '2px solid #22c55e', borderRadius: 4 }} title="AI bounding box" /> : null}</div> : <p className="muted">Không có ảnh.</p>}
          {d.bbox ? <p className="muted">BBox: {JSON.stringify(d.bbox)}</p> : null}
        </section>
      )}
      {tab === 'Audit' && (
        <section className="data-table-card detail-card">
          <h3 style={{ marginTop: 0 }}>Lịch sử audit liên quan</h3>
          {audit.length === 0 ? <p className="muted">Chưa có bản ghi audit cho detection này.</p> : <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 }}>{audit.map((a) => <li key={a.id} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 10, background: '#f8fafc', flexWrap: 'wrap' }}><span style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date((a as unknown as { time?: string }).time ?? 0).toLocaleString('vi-VN')}</span><b>{a.actor}</b><span>{a.action}</span><code>{a.resource}</code></li>)}</ul>}
        </section>
      )}
      {tab === 'Raw Data' && <section className="data-table-card detail-card"><h3>API JSON</h3><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(d, null, 2)}</pre></section>}
      <div style={{ display: 'flex', gap: 8 }}><Link to="/detections" className="btn">Quay lại lịch sử</Link><Button onClick={() => window.history.back()}>Mở lại trang trước</Button></div>
    </div>
  )
}
