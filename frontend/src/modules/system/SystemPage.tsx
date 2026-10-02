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
  const load = async () => { setLoading(true); setErr(null); try { const r = await healthApi.ready(); setData(r) } catch (e) { setErr(e instanceof Error ? e.message : 'Không kết nối được backend') } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  const alpr = (data as { alpr?: { provider?: string; ready?: boolean } })?.alpr
  return (
    <div className="data-page system-page">
      <Breadcrumb items={[{ label: 'Tình trạng hệ thống' }]} />
      <section className="data-hero data-hero--forest">
        <div className="data-hero-copy">
          <span className="data-kicker">VẬN HÀNH HỆ THỐNG · VISIONPARK</span>
          <h2>Tình trạng hệ thống</h2>
          <p>Kiểm tra trạng thái Backend / ALPR / Frontend trước và trong quá trình vận hành.</p>
        </div>
        <div className="data-hero-stat"><Badge variant={err ? 'danger' : 'success'}>{err ? 'Có sự cố' : 'Hoạt động tốt'}</Badge></div>
      </section>

      <div className="system-status-grid">
        <div className="system-status-card"><span>Backend API</span><strong>{err ? 'Gián đoạn' : 'Hoạt động tốt'}</strong></div>
        <div className="system-status-card"><span>Module ALPR</span><strong>{alpr?.provider ?? '—'} · {alpr?.ready ? 'Sẵn sàng' : 'Chưa sẵn sàng'}</strong></div>
        <div className="system-status-card"><span>Frontend Web</span><strong>Đang hoạt động</strong></div>
      </div>

      <section className="data-table-card system-details">
        <div className="data-table-head"><div><span className="data-section-kicker">RUNTIME DETAILS</span><h3>Thông tin kết nối</h3></div></div>
        <div className="system-meta">
          <div><span>Đường dẫn API (Base URL)</span><code>{getApiBaseUrl()}</code></div>
          <div><span>Môi trường triển khai</span><code>{import.meta.env.MODE}</code></div>
        </div>
        {loading ? <Spinner /> : err ? <Alert variant="error">{err}</Alert> : <pre className="code-block system-json">{JSON.stringify(data, null, 2) ?? '—'}</pre>}
        <Button className="system-refresh" onClick={load}>Kiểm tra lại</Button>
      </section>
    </div>
  )
}
