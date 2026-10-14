import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { can } from '../../lib/permissions.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'

export function AlprPage() {
  const { user } = useAuth()
  const [data, setData] = useState<unknown>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    healthApi.ready().then(setData).catch((e) => setErr(e instanceof Error ? e.message : translate("Không tải được ALPR status"))).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />
  if (err) return <Alert variant="error">{err}</Alert>

  const alpr = (data as { alpr?: { provider?: string; ready?: boolean; model_version?: string; runtime?: string; confidence_threshold?: number } })?.alpr

  return (
    <div className="utility-page">
      <Breadcrumb items={[{ label: 'AI' }, { label: 'ALPR' }]} />

      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">License Plate Recognition · Duy Anh</span>
          <h1>ALPR</h1>
          <p>{translate("Trạng thái provider/threshold, readonly khi backend chưa có API cấu hình.")}</p>
        </div>
        <div className="utility-stat-row">
          <Badge variant={alpr?.ready ? 'success' : 'warning'}>{alpr?.ready ? 'Ready' : 'Not ready'}</Badge>
          <Badge>{alpr?.provider ?? '—'}</Badge>
        </div>
      </section>

      <section className="utility-panel">
        <div className="utility-panel-head">
          <div>
            <span className="utility-section-kicker">RUNTIME TELEMETRY</span>
            <h3>Runtime</h3>
          </div>
        </div>
        <ul className="role-permission-list" style={{ marginTop: 0 }}>
          {[
            ['Provider', alpr?.provider ?? '—'],
            ['Ready', String(alpr?.ready ?? '—')],
            ['Model version', alpr?.model_version ?? '—'],
            ['Runtime', alpr?.runtime ?? '—'],
            ['Confidence threshold', String(alpr?.confidence_threshold ?? '0.85')],
          ].map(([k, v]) => (
            <li key={k} className="role-permission-row">
              <span>{k}</span>
              <strong className="data-mono">{v}</strong>
            </li>
          ))}
        </ul>
        <pre className="code-block" style={{ marginTop: 16 }}>{JSON.stringify(data, null, 2)}</pre>
        <div className="row-actions" style={{ marginTop: 16 }}>
          {can(user, 'alpr.test') && <Link to="/admin/alpr/test" className="btn btn-sm btn-primary" style={{ textDecoration: 'none' }}>ALPR Test Lab</Link>}
          <Link to="/detections" className="btn btn-sm" style={{ textDecoration: 'none' }}>{translate("Lịch sử nhận diện")}</Link>
        </div>
      </section>
    </div>
  )
}
