import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { lanesApi } from '../../api/lanesApi.ts'
import { detectionsApi } from '../../api/services.ts'
import type { Detection } from '../../api/domain.ts'
import type { Lane, HealthStatus } from '../../api/types.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'

export function DashboardPage() {
  const { user } = useAuth()
  const [lanes, setLanes] = useState<Lane[] | null>(null)
  const [detections, setDetections] = useState<Detection[] | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    Promise.allSettled([lanesApi.getLanes(), detectionsApi.list({ limit: 5 }), healthApi.ready()]).then((r) => {
      if (!alive) return
      if (r[0].status === 'fulfilled') setLanes(r[0].value)
      if (r[1].status === 'fulfilled') setDetections(r[1].value)
      if (r[2].status === 'fulfilled') setHealth(r[2].value)
      if (r.some((x) => x.status === 'rejected')) setErr('Một số dữ liệu chưa tải được (backend pending).')
      setLoading(false)
    })
    return () => { alive = false }
  }, [])

  if (loading) return <Spinner />
  const activeLanes = lanes?.filter((l) => l.active).length ?? 0
  const needConfirm = detections?.filter((d) => d.status === 'NEEDS_CONFIRMATION').length ?? 0
  const alprProvider = health?.alpr?.provider ?? '—'

  return (
    <div>
      <div className="page-head">
        <h2>Xin chào, {user?.display_name}</h2>
        <p className="muted">Tổng quan hoạt động VisionPark — {new Date().toLocaleDateString('vi-VN')}</p>
      </div>
      {err ? <Alert variant="warning">{err}</Alert> : null}
      <div className="stat-grid">
        <div className="stat-card"><div className="stat-label">Làn hoạt động</div><div className="stat-value">{lanes ? activeLanes : '—'}</div></div>
        <div className="stat-card"><div className="stat-label">Nhận diện gần đây</div><div className="stat-value">{detections ? detections.length : '—'}</div></div>
        <div className="stat-card"><div className="stat-label">Cần xác nhận</div><div className="stat-value">{detections ? needConfirm : '—'}</div></div>
        <div className="stat-card"><div className="stat-label">ALPR</div><div className="stat-value" style={{ fontSize: 16 }}>{alprProvider}</div></div>
      </div>

      <div className="grid-2" style={{ marginTop: 16 }}>
        <section className="card">
          <h3>Nhận diện gần đây</h3>
          {!detections || detections.length === 0 ? <EmptyState title="Chưa có dữ liệu" /> : (
            <ul className="list">
              {detections.slice(0, 5).map((d) => (
                <li key={d.id} className="list-row">
                  <span>{d.normalized_plate ?? d.ai_plate ?? '—'}</span>
                  <span className="badge">{d.status}</span>
                  <span className="muted">{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : ''}</span>
                </li>
              ))}
            </ul>
          )}
          <Link to="/station/history">Xem tất cả →</Link>
        </section>
        <section className="card">
          <h3>System Health</h3>
          <pre className="code-block">{health ? JSON.stringify(health, null, 2) : 'Chưa có dữ liệu — backend chưa cung cấp health đầy đủ.'}</pre>
          <h3 style={{ marginTop: 12 }}>Lane Status</h3>
          {!lanes || lanes.length === 0 ? <EmptyState title="Chưa có dữ liệu" /> : (
            <ul className="list">
              {lanes.map((l) => (
                <li key={l.id} className="list-row"><span>{l.name}</span><span>{l.direction}</span><span className={`badge ${l.active ? 'badge-success' : 'badge-muted'}`}>{l.active ? 'ACTIVE' : 'Inactive'}</span></li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
