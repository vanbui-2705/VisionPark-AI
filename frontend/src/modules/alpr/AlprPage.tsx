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
    healthApi.ready().then(setData).catch((e) => setErr(e instanceof Error ? e.message : 'Không tải được ALPR status')).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />
  if (err) return <Alert variant="error">{err}</Alert>

  const alpr = (data as { alpr?: { provider?: string; ready?: boolean; model_version?: string; runtime?: string; confidence_threshold?: number } })?.alpr
  const isMock = (alpr?.provider ?? '').toLowerCase().includes('mock')

  return (
    <div className="data-page alpr-page">
      <Breadcrumb items={[{ label: 'AI' }, { label: 'ALPR' }]} />

      <section className="data-hero alpr-hero">
        <div className="data-hero-copy">
          <span className="data-kicker">Hệ thống nhận dạng biển số · VisionPark</span>
          <h2>ALPR</h2>
          <p>Thông số mô hình AI, nhà cung cấp và ngưỡng tin cậy phục vụ nhận dạng.</p>
        </div>
        <div className="data-hero-stat alpr-hero-status"><Badge variant={alpr?.ready ? 'success' : 'warning'}>{alpr?.ready ? 'Sẵn sàng' : 'Chưa sẵn sàng'}</Badge><Badge>{alpr?.provider ?? '—'}</Badge></div>
      </section>

      {isMock ? <Alert variant="warning">Hệ thống đang chạy MOCK provider — kết quả không từ model AI thực tế.</Alert> : null}

      <section className="data-table-card alpr-config-card">
        <div className="data-table-head"><div><span className="data-section-kicker">CẤU HÌNH ĐANG CHẠY</span><h3>Thông số môi trường thực thi</h3></div></div>
        <ul className="alpr-spec-list">
          {[
            ['Nhà cung cấp (Provider)', alpr?.provider ?? '—'],
            ['Trạng thái sẵn sàng', alpr?.ready ? 'Sẵn sàng' : 'Chưa sẵn sàng'],
            ['Phiên bản mô hình', alpr?.model_version ?? '—'],
            ['Môi trường thực thi', alpr?.runtime ?? '—'],
            ['Ngưỡng độ tin cậy', String(alpr?.confidence_threshold ?? '0.85')],
          ].map(([k, v]) => (
            <li key={k} className="alpr-spec-row"><span>{k}</span><strong>{v}</strong></li>
          ))}
        </ul>
        <div className="alpr-config-body">
          <pre className="code-block alpr-json">{JSON.stringify(data, null, 2)}</pre>
          <div className="data-pager-actions"><Link to="/admin/alpr/test" className="btn btn-sm btn-primary">Phòng thử nghiệm ALPR</Link><Link to="/detections" className="btn btn-sm">Lịch sử nhận diện</Link></div>
        </div>
      </section>
    </div>
  )
}
