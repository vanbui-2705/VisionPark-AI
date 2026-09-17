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
    detectionsApi
      .get(id)
      .then(setD)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : 'Không tải được chi tiết.'))
      .finally(() => setLoading(false))
    auditApi.list({ limit: 100 }).then((rows) => setAudit(rows.filter((r) => r.resource_id === id))).catch(() => setAudit([]))
  }, [id])

  if (loading) return <Skeleton lines={6} />
  if (err) return <Alert variant="error">{err}</Alert>
  if (!d) return <Alert variant="info">Không tìm thấy detection.</Alert>

  return (
    <div>
      <Breadcrumb items={[{ label: 'Lịch sử nhận diện', to: '/detections' }, { label: 'Chi tiết' }]} />
      <div className="page-head">
        <h2>Detection <span className="plate" style={{ fontSize: 20 }}>{d.final_plate ?? d.normalized_plate ?? d.ai_plate ?? '—'}</span></h2>
        <p className="muted"><Badge>{d.status}</Badge> · {new Date(d.created_at).toLocaleString('vi-VN')}</p>
      </div>
      <div className="tabs">
        {TABS.map((t) => (
          <button type="button" key={t} className={t === tab ? 'active' : undefined} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === 'Overview' && (
        <div className="grid-2">
          <section className="card">
            <h3>Kết quả AI</h3>
            <ul className="kv">
              <li><b>Raw Plate:</b> {d.ai_plate ?? '—'}</li>
              <li><b>Normalized:</b> {d.normalized_plate ?? '—'}</li>
              <li><b>Confidence:</b> {d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</li>
              <li><b>Processing:</b> {d.processing_ms ?? '—'} ms</li>
              <li><b>Model:</b> {d.model_version ?? '—'}</li>
            </ul>
          </section>
          <section className="card">
            <h3>Kết quả cuối</h3>
            <ul className="kv">
              <li><b>Final Plate:</b> {d.final_plate ?? d.normalized_plate ?? '—'}</li>
              <li><b>Status:</b> {d.status}</li>
              <li><b>Confirmed by:</b> {d.confirmed_by ?? '—'}</li>
              <li><b>Confirmed at:</b> {d.confirmed_at ? new Date(d.confirmed_at).toLocaleString('vi-VN') : '—'}</li>
              <li><b>Operator:</b> {d.operator ?? '—'}</li>
            </ul>
          </section>
          <section className="card">
            <h3>Metadata</h3>
            <ul className="kv">
              <li><b>ID:</b> {d.id}</li>
              <li><b>Lane:</b> {d.lane_name ?? d.lane_id}</li>
              <li><b>Hướng:</b> {d.direction ?? '—'}</li>
              <li><b>Created:</b> {new Date(d.created_at).toLocaleString('vi-VN')}</li>
            </ul>
          </section>
        </div>
      )}

      {tab === 'Media' && (
        <section className="card">
          <h3>Ảnh / khung hình</h3>
          {d.image_url ? (
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <img src={d.image_url} alt="detection" style={{ maxWidth: '100%', borderRadius: 8, display: 'block' }} />
              {d.bbox ? (
                <span style={{ position: 'absolute', left: `${d.bbox.x}%`, top: `${d.bbox.y}%`, width: `${d.bbox.w}%`, height: `${d.bbox.h}%`, border: '2px solid #22c55e', borderRadius: 4 }} title="AI bounding box" />
              ) : null}
            </div>
          ) : (
            <p className="muted">Không có ảnh (backend chưa cung cấp image_url — placeholder).</p>
          )}
          {d.bbox ? <p className="muted">BBox: {JSON.stringify(d.bbox)}</p> : null}
        </section>
      )}

      {tab === 'Audit' && (
        <section className="card">
          <h3>Lịch sử audit liên quan</h3>
          {audit.length === 0 ? <p className="muted">Chưa có bản ghi audit cho detection này.</p> : (
            <ul className="list">
              {audit.map((a) => (
                <li key={a.id} className="list-row">
                  <span>{new Date(a.time ?? (a as { created_at?: string }).created_at ?? 0).toLocaleString('vi-VN')}</span>
                  <b>{a.actor}</b>
                  <span>{a.action}</span>
                  <code>{a.resource}</code>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === 'Raw Data' && (
        <section className="card">
          <h3>API JSON</h3>
          <pre className="code-block">{JSON.stringify(d, null, 2)}</pre>
          {d.bbox ? <p className="muted">BBox overlay được suy ra từ API JSON — không phải pixel thật từ ảnh.</p> : null}
        </section>
      )}

      <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
        <Link to="/detections" className="btn">Quay lại lịch sử</Link>
        <Button onClick={() => window.history.back()}>Mở lại trang trước</Button>
      </div>
    </div>
  )
}
