import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { lanesApi } from '../../api/lanesApi.ts'
import { detectionsApi, parkingTransactionsApi } from '../../api/services.ts'
import type { Detection, ParkingTransaction } from '../../api/domain.ts'
import type { Lane, HealthStatus } from '../../api/types.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Badge } from '../../components/ui/Badge.tsx'

export function DashboardPage() {
  const { user } = useAuth()
  const [lanes, setLanes] = useState<Lane[] | null>(null)
  const [detections, setDetections] = useState<Detection[] | null>(null)
  const [parking, setParking] = useState<ParkingTransaction[] | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    Promise.allSettled([
      lanesApi.getLanes(),
      detectionsApi.list({ limit: 5 }),
      parkingTransactionsApi.list({ limit: 5 }),
      healthApi.ready(),
    ]).then((r) => {
      if (!alive) return
      if (r[0].status === 'fulfilled') setLanes(r[0].value)
      if (r[1].status === 'fulfilled') setDetections(r[1].value)
      if (r[2].status === 'fulfilled') setParking(r[2].value)
      if (r[3].status === 'fulfilled') setHealth(r[3].value)
      if (r.some((x) => x.status === 'rejected')) setErr('Một số dữ liệu chưa tải được (backend pending).')
      setLoading(false)
    })
    return () => { alive = false }
  }, [])

  if (loading) return <Spinner />

  const activeLanes = lanes?.filter((l) => l.active).length ?? 0
  const needConfirm = detections?.filter((d) => d.status === 'NEEDS_CONFIRMATION').length ?? 0
  const parked = parking?.filter((p) => p.status === 'PARKED').length ?? 0
  const manual = parking?.filter((p) => p.is_manual_override).length ?? 0
  const alprProvider = health?.alpr?.provider ?? '—'

  return (
    <div className="dashboard-v2">
      <section className="dashboard-hero">
        <div>
          <div className="eyebrow">VisionPark Control Center · Duy Anh</div>
          <h1>Xin chào, {user?.display_name}</h1>
          <p>Giám sát nhận diện biển số, làn xe, check-in PARKED và audit vận hành trong một màn hình.</p>
          <div className="hero-actions">
            <Link to="/parking" className="btn btn-primary">Lịch sử đỗ xe</Link>
            <Link to="/station/scan" className="btn hero-secondary">Quét biển số</Link>
          </div>
        </div>
        <div className="hero-status-card">
          <span className="status-dot dot-ok"></span>
          <div>
            <b>ALPR online</b>
            <span>{alprProvider}</span>
          </div>
        </div>
      </section>

      {err ? <Alert variant="warning">{err}</Alert> : null}

      <div className="stat-grid stat-grid-v2">
        <div className="stat-card stat-card-v2"><div className="stat-icon">⇆</div><div><div className="stat-label">Làn hoạt động</div><div className="stat-value">{lanes ? activeLanes : '—'}</div></div></div>
        <div className="stat-card stat-card-v2"><div className="stat-icon">◎</div><div><div className="stat-label">Nhận diện gần đây</div><div className="stat-value">{detections ? detections.length : '—'}</div></div></div>
        <div className="stat-card stat-card-v2"><div className="stat-icon warning">!</div><div><div className="stat-label">Cần xác nhận</div><div className="stat-value">{detections ? needConfirm : '—'}</div></div></div>
        <div className="stat-card stat-card-v2"><div className="stat-icon success">P</div><div><div className="stat-label">Xe đang đỗ</div><div className="stat-value">{parking ? parked : '—'}</div></div></div>
      </div>

      <div className="dashboard-grid">
        <section className="card card-polished">
          <div className="card-head">
            <div><h3>Parking Operations</h3><p className="muted">Check-in Phase 2</p></div>
            <Link to="/parking">Xem tất cả →</Link>
          </div>
          {!parking || parking.length === 0 ? <EmptyState title="Chưa có dữ liệu" /> : (
            <ul className="list rich-list">
              {parking.slice(0, 5).map((p) => (
                <li key={p.id} className="list-row rich-row">
                  <div><span className="plate-mini">{p.license_plate}</span><small>{p.lane_name ?? p.lane_id} · {new Date(p.check_in_time).toLocaleString('vi-VN')}</small></div>
                  <div className="row-actions"><Badge variant={p.status === 'PARKED' ? 'success' : 'neutral'}>{p.status}</Badge>{p.is_manual_override ? <Badge variant="warning">sửa tay</Badge> : null}</div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card card-polished">
          <div className="card-head">
            <div><h3>Nhận diện gần đây</h3><p className="muted">ALPR detections</p></div>
            <Link to="/detections">Xem tất cả →</Link>
          </div>
          {!detections || detections.length === 0 ? <EmptyState title="Chưa có dữ liệu" /> : (
            <ul className="list rich-list">
              {detections.slice(0, 5).map((d) => (
                <li key={d.id} className="list-row rich-row">
                  <div><span className="plate-mini">{d.normalized_plate ?? d.ai_plate ?? '—'}</span><small>{d.lane_name ?? d.lane_id} · {d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</small></div>
                  <Badge variant={d.status === 'NEEDS_CONFIRMATION' ? 'warning' : 'success'}>{d.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card card-polished">
          <div className="card-head"><div><h3>Lane Status</h3><p className="muted">Cổng vào / ra</p></div></div>
          {!lanes || lanes.length === 0 ? <EmptyState title="Chưa có dữ liệu" /> : (
            <ul className="list rich-list">
              {lanes.map((l) => (
                <li key={l.id} className="list-row rich-row"><div><strong>{l.name}</strong><small>{l.direction} · {l.id}</small></div><Badge variant={l.active ? 'success' : 'neutral'}>{l.active ? 'ACTIVE' : 'Inactive'}</Badge></li>
              ))}
            </ul>
          )}
        </section>

        <section className="card card-polished system-card">
          <div className="card-head"><div><h3>System Health</h3><p className="muted">Runtime snapshot</p></div></div>
          <pre className="code-block">{health ? JSON.stringify(health, null, 2) : 'Chưa có dữ liệu — backend chưa cung cấp health đầy đủ.'}</pre>
          <div className="mini-metrics"><span>{manual} manual override</span><span>{parked} parked</span></div>
        </section>
      </div>
    </div>
  )
}
