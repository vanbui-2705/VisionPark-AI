import { t as translate } from "../../lib/i18n"
import { DetectionImage } from '../../components/DetectionImage.tsx'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { detectionsApi, auditApi } from '../../api/services.ts'
import { can } from '../../lib/permissions.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import type { Detection, AuditLog } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Skeleton } from '../../components/ui/Skeleton.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'

const TABS = ['Overview', 'Media', 'Audit', 'Raw Data'] as const

export function DetectionDetailPage() {
  const { user } = useAuth()
  const mayReadAudit = can(user, 'audit.read')
  const { id } = useParams()
  const [d, setD] = useState<Detection | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<(typeof TABS)[number]>('Overview')
  const [audit, setAudit] = useState<AuditLog[]>([])
  useEffect(() => {
    if (!id) return
    detectionsApi.get(id).then(setD).catch((e: unknown) => setErr(e instanceof Error ? e.message : translate("Không tải được chi tiết."))).finally(() => setLoading(false))
    if (mayReadAudit) auditApi.list({ resource_id: id, limit: 100 }).then(setAudit).catch(() => setAudit([]))
  }, [id, mayReadAudit])
  if (loading) return <Skeleton lines={6} />
  if (err) return <Alert variant="error">{err}</Alert>
  if (!d) return <Alert variant="info">{translate("Không tìm thấy detection.")}</Alert>
  const plate = d.final_plate ?? d.normalized_plate ?? d.ai_plate ?? '—'
  return (
    <div className="data-page">
      <Breadcrumb items={[{ label: translate("Lịch sử nhận diện"), to: '/detections' }, { label: translate("Chi tiết") }]} />
      <section className="data-hero data-hero--forest">
        <div className="data-hero-copy">
          <span className="data-kicker">DETECTION RECORD · {d.lane_name ?? d.lane_id} · {d.direction ?? '—'}</span>
          <h2>{plate}</h2>
          <p>{new Date(d.created_at).toLocaleString('vi-VN')} · Status: {d.status}</p>
        </div>
        <div className="row-actions">
          <Badge>{d.status}</Badge>
          <Link to="/detections" className="btn btn-secondary">{translate("Quay lại")}</Link>
        </div>
      </section>

      <div className="detail-tabs">
        {TABS.filter((t) => t !== 'Audit' || mayReadAudit).map((t) => (
          <button type="button" key={t} className={t === tab ? 'is-active' : ''} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === 'Overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px,1fr))', gap: 16 }}>
          <section className="utility-panel">
            <span className="utility-section-kicker">{translate("Kết quả AI")}</span>
            <ul className="role-permission-list" style={{ marginTop: 12 }}>
              <li className="role-permission-row"><span>Raw Plate</span><strong className="data-mono">{d.ai_plate ?? '—'}</strong></li>
              <li className="role-permission-row"><span>Normalized</span><strong className="data-mono">{d.normalized_plate ?? '—'}</strong></li>
              <li className="role-permission-row"><span>Confidence</span><span>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</span></li>
              <li className="role-permission-row"><span>Processing</span><span>{d.processing_ms ?? '—'} ms</span></li>
              <li className="role-permission-row"><span>Model</span><span>{d.model_version ?? '—'}</span></li>
            </ul>
          </section>
          <section className="utility-panel">
            <span className="utility-section-kicker">{translate("Kết quả cuối")}</span>
            <ul className="role-permission-list" style={{ marginTop: 12 }}>
              <li className="role-permission-row"><span>Final Plate</span><strong className="data-mono">{d.final_plate ?? d.normalized_plate ?? '—'}</strong></li>
              <li className="role-permission-row"><span>Status</span><Badge>{d.status}</Badge></li>
              <li className="role-permission-row"><span>Confirmed by</span><span>{d.confirmed_by ?? '—'}</span></li>
              <li className="role-permission-row"><span>Confirmed at</span><span>{d.confirmed_at ? new Date(d.confirmed_at).toLocaleString('vi-VN') : '—'}</span></li>
              <li className="role-permission-row"><span>Operator</span><span>{d.operator ?? '—'}</span></li>
            </ul>
          </section>
          <section className="utility-panel">
            <span className="utility-section-kicker">Metadata</span>
            <ul className="role-permission-list" style={{ marginTop: 12 }}>
              <li className="role-permission-row"><span>ID</span><code style={{ fontSize: 11 }}>{d.id}</code></li>
              <li className="role-permission-row"><span>Lane</span><span>{d.lane_name ?? d.lane_id}</span></li>
              <li className="role-permission-row"><span>{translate("Hướng")}</span><span>{d.direction ?? '—'}</span></li>
              <li className="role-permission-row"><span>Created</span><span>{new Date(d.created_at).toLocaleString('vi-VN')}</span></li>
            </ul>
          </section>
        </div>
      )}
      {tab === 'Media' && (
        <section className="utility-panel">
          <div className="utility-panel-head"><div><span className="utility-section-kicker">CAPTURED FRAME</span><h3>{translate("Ảnh / khung hình")}</h3></div></div>
          {d.image_url ? <DetectionImage src={d.image_url} bbox={d.bbox} /> : <p className="muted">{translate("Không có ảnh.")}</p>}
          {d.bbox ? <p className="muted" style={{ marginTop: 10 }}>BBox: {JSON.stringify(d.bbox)}</p> : null}
        </section>
      )}
      {tab === 'Audit' && mayReadAudit && (
        <section className="utility-panel">
          <div className="utility-panel-head"><div><span className="utility-section-kicker">AUDIT TRAIL</span><h3>{translate("Lịch sử audit liên quan")}</h3></div></div>
          {audit.length === 0 ? <p className="muted">{translate("Chưa có bản ghi audit cho detection này.")}</p> : <ul className="role-permission-list" style={{ marginTop: 0 }}>{audit.map((a) => <li key={a.id} className="role-permission-row"><span className="data-time">{new Date((a as unknown as { time?: string }).time ?? 0).toLocaleString('vi-VN')}</span><b>{a.actor}</b><span>{a.action}</span><code>{a.resource}</code></li>)}</ul>}
        </section>
      )}
      {tab === 'Raw Data' && <section className="utility-panel"><div className="utility-panel-head"><div><span className="utility-section-kicker">RAW PAYLOAD</span><h3>API JSON</h3></div></div><pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(d, null, 2)}</pre></section>}
      <div className="row-actions"><Link to="/detections" className="btn">{translate("Quay lại lịch sử")}</Link><Button onClick={() => window.history.back()}>{translate("Mở lại trang trước")}</Button></div>
    </div>
  )
}
