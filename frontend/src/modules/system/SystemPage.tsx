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
    <div style={{ display: 'grid', gap: 16 }}>
      <Breadcrumb items={[{ label: 'System Health' }]} />
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%)', borderRadius: 16, padding: '18px 20px', color: '#fff', display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', opacity: 0.7, textTransform: 'uppercase' }}>Runtime · Duy Anh</div>
          <h2 style={{ margin: '6px 0 6px', fontSize: 22, fontWeight: 800 }}>{translate("Trạng thái hệ thống")}</h2>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75 }}>{translate("Backend / ALPR / Frontend — kiểm tra nhanh trước khi vận hành.")}</p>
        </div>
        <Badge variant={err ? 'danger' : 'success'}>{err ? 'Error' : 'Healthy'}</Badge>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px,1fr))', gap: 12 }}>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 14 }}><div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Backend</div><div style={{ fontWeight: 800, marginTop: 6 }}>{err ? '● Error' : '● Healthy'}</div></div>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 14 }}><div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' }}>ALPR</div><div style={{ fontWeight: 800, marginTop: 6 }}>{alpr?.provider ?? '—'} {alpr?.ready ? '●' : ''}</div></div>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 14 }}><div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Frontend</div><div style={{ fontWeight: 800, marginTop: 6 }}>● Running</div></div>
      </div>

      <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 16, boxShadow: '0 4px 16px rgba(15,23,42,0.06)' }}>
        <div style={{ display: 'grid', gap: 6, fontSize: 13, marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)' }}>API Base URL</span><code>{getApiBaseUrl()}</code></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><span style={{ color: 'var(--muted)' }}>Environment</span><code>{import.meta.env.MODE}</code></div>
        </div>
        {loading ? <Spinner /> : err ? <Alert variant="error">{err}</Alert> : <pre className="code-block" style={{ margin: 0 }}>{JSON.stringify(data, null, 2) ?? '—'}</pre>}
        <Button onClick={load} style={{ marginTop: 12 }}>{translate("Kiểm tra lại")}</Button>
      </section>
    </div>
  )
}
