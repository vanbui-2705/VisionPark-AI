import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { healthApi } from '../../api/healthApi.ts'
import { getApiBaseUrl } from '../../api/client.ts'
import { Breadcrumb } from '../../components/ui/Breadcrumb.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'

export function SystemPage() {
  const [data, setData] = useState<unknown>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const load = async () => { setLoading(true); setErr(null); try { const r = await healthApi.ready(); setData(r) } catch (e) { setErr(e instanceof Error ? e.message : translate("Không kết nối được backend")) } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  const alpr = (data as { alpr?: { provider?: string; ready?: boolean } })?.alpr
  return (
    <div className="utility-page">
      <Breadcrumb items={[{ label: 'System Health' }]} />
      <section className="utility-hero utility-hero--forest">
        <div className="utility-hero-copy">
          <span className="utility-kicker">Runtime · Duy Anh</span>
          <h1>{translate("Trạng thái hệ thống")}</h1>
          <p>{translate("Backend / ALPR / Frontend — kiểm tra nhanh trước khi vận hành.")}</p>
        </div>
        <Badge variant={err ? 'danger' : 'success'}>{err ? 'Error' : 'Healthy'}</Badge>
      </section>

      <div className="stat-grid stat-grid-v2" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
        <div className="stat-card stat-card-v2">
          <div>
            <div className="stat-label">BACKEND</div>
            <div className="stat-value" style={{ fontSize: 22 }}>{err ? '● Error' : '● Healthy'}</div>
          </div>
        </div>
        <div className="stat-card stat-card-v2">
          <div>
            <div className="stat-label">ALPR</div>
            <div className="stat-value" style={{ fontSize: 22 }}>{alpr?.provider ?? '—'} {alpr?.ready ? '●' : ''}</div>
          </div>
        </div>
        <div className="stat-card stat-card-v2">
          <div>
            <div className="stat-label">FRONTEND</div>
            <div className="stat-value" style={{ fontSize: 22 }}>● Running</div>
          </div>
        </div>
      </div>

      <section className="utility-panel utility-health-panel">
        <div className="utility-panel-head">
          <div>
            <span className="utility-section-kicker">READINESS PAYLOAD</span>
            <h3>Environment & Probe</h3>
          </div>
          <Button onClick={load}>{translate("Kiểm tra lại")}</Button>
        </div>
        <ul className="role-permission-list" style={{ marginTop: 0, marginBottom: 14 }}>
          <li className="role-permission-row"><span>API Base URL</span><code>{getApiBaseUrl()}</code></li>
          <li className="role-permission-row"><span>Environment</span><code>{import.meta.env.MODE}</code></li>
        </ul>
        {loading ? <Spinner /> : err ? <Alert variant="error">{err}</Alert> : <pre className="code-block">{JSON.stringify(data, null, 2) ?? '—'}</pre>}
      </section>
    </div>
  )
}
