import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'

export function AlprPage() {
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
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'AI' }, { label: 'ALPR' }]} />

      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>License Plate Recognition · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>ALPR</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>{translate("Trạng thái provider/threshold, readonly khi backend chưa có API cấu hình.")}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><Badge variant={alpr?.ready ? 'success' : 'warning'}>{alpr?.ready ? 'Ready' : 'Not ready'}</Badge><Badge>{alpr?.provider ?? '—'}</Badge></div>
      </div>


      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 700, marginBottom: 10 }}>Runtime</div>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 }}>
          {[
            ['Provider', alpr?.provider ?? '—'],
            ['Ready', String(alpr?.ready ?? '—')],
            ['Model version', alpr?.model_version ?? '—'],
            ['Runtime', alpr?.runtime ?? '—'],
            ['Confidence threshold', String(alpr?.confidence_threshold ?? '0.85')],
          ].map(([k, v]) => (
            <li key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface)', fontSize: 13 }}><span style={{ color: 'var(--muted)' }}>{k}</span><strong style={{ fontFamily: 'ui-monospace, monospace' }}>{v}</strong></li>
          ))}
        </ul>
        <pre className="code-block" style={{ marginTop: 12 }}>{JSON.stringify(data, null, 2)}</pre>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}><Link to="/admin/alpr/test" className="btn btn-sm btn-primary" style={{ textDecoration: 'none' }}>ALPR Test Lab</Link><Link to="/detections" className="btn btn-sm" style={{ textDecoration: 'none' }}>{translate("Lịch sử nhận diện")}</Link></div>
      </section>
    </div>
  )
}
