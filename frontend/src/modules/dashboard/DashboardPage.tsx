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

function MetricIcon({ name }: { name: 'lanes' | 'detections' | 'confirm' | 'parking' }) {
  if (name === 'lanes') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 4-2 16M17 4l2 16M12 4v3M12 10v4M12 17v3" /></svg>
  }
  if (name === 'detections') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7" /><path d="m12 12 4-4M5 5a10 10 0 0 1 14 0" /></svg>
  }
  if (name === 'confirm') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="m8 12 2.5 2.5L16 9" /></svg>
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 17h14l-1-6H6l-1 6Z" /><path d="m7 11 1.5-4h7L17 11M7 17v2M17 17v2M7.5 14h.01M16.5 14h.01" /></svg>
}

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
      if (r[1].status === 'fulfilled') setDetections((r[1].value as unknown as { items: Detection[] }).items ?? r[1].value as unknown as Detection[])
      if (r[2].status === 'fulfilled') setParking((r[2].value as unknown as { items: ParkingTransaction[] }).items ?? r[2].value as unknown as ParkingTransaction[])
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
  const alprReady = health?.alpr?.ready === true
  const alprPending = health === null
  const alprProvider = health?.alpr?.provider ?? 'Chưa có thông tin'

  return (
    <div className="dashboard-v2">
      <section className="dashboard-hero">
        <div>
          <div className="eyebrow">Trung tâm điều hành VisionPark</div>
          <h1>Xin chào, {user?.display_name ?? user?.username ?? 'Người dùng'}</h1>
          <p>Giám sát nhận diện biển số, tình trạng làn xe, quản lý xe đang đỗ và nhật ký vận hành thời gian thực.</p>
          <div className="hero-actions">
            <Link to="/parking" className="btn btn-primary">Lịch sử đỗ xe</Link>
            <Link to="/station/scan" className="btn hero-secondary">Quét biển số</Link>
          </div>
        </div>
        <div className="hero-status-card">
          <span className={`status-dot ${alprPending ? 'dot-warn' : alprReady ? 'dot-ok' : 'dot-bad'}`} />
          <div className="hero-status-copy">
            <span className="status-label">TRẠNG THÁI HỆ THỐNG</span>
            <b>{alprPending ? 'ALPR đang kiểm tra' : alprReady ? 'ALPR sẵn sàng' : 'ALPR chưa sẵn sàng'}</b>
            <span>{alprProvider}</span>
          </div>
        </div>
      </section>

      {err ? <Alert variant="warning">{err}</Alert> : null}

      <div className="stat-grid stat-grid-v2">
        <article className="stat-card stat-card-v2"><div className="stat-icon"><MetricIcon name="lanes" /></div><div><div className="stat-label">Làn hoạt động</div><div className="stat-value">{lanes && lanes.length > 0 ? activeLanes : '—'}</div></div></article>
        <article className="stat-card stat-card-v2"><div className="stat-icon"><MetricIcon name="detections" /></div><div><div className="stat-label">Nhận diện gần đây</div><div className="stat-value">{detections ? detections.length : '—'}</div></div></article>
        <article className="stat-card stat-card-v2"><div className="stat-icon warning"><MetricIcon name="confirm" /></div><div><div className="stat-label">Cần xác nhận</div><div className="stat-value">{detections ? needConfirm : '—'}</div></div></article>
        <article className="stat-card stat-card-v2"><div className="stat-icon success"><MetricIcon name="parking" /></div><div><div className="stat-label">Xe đang đỗ</div><div className="stat-value">{parking ? parked : '—'}</div></div></article>
      </div>

      <div className="dashboard-grid">
        <section className="card card-polished dashboard-card dashboard-card--parking">
          <div className="card-head">
            <div><span className="card-kicker">VẬN HÀNH</span><h3>Hoạt động đỗ xe</h3><p className="muted">Lượt gửi xe mới nhất</p></div>
            <Link to="/parking">Xem tất cả →</Link>
          </div>
          {!parking || parking.length === 0 ? <EmptyState title="Chưa có dữ liệu" /> : (
            <ul className="list rich-list">
              {parking.slice(0, 5).map((p) => (
                <li key={p.id} className="list-row rich-row">
                  <div><span className="plate-mini">{p.license_plate}</span><small>{p.lane_name ?? p.lane_id} · {new Date(p.check_in_time).toLocaleString('vi-VN')}</small></div>
                  <div className="row-actions"><Badge variant={p.status === 'PARKED' ? 'success' : 'neutral'}>{p.status === 'PARKED' ? 'Đang đỗ' : p.status}</Badge>{p.is_manual_override ? <Badge variant="warning">Sửa tay</Badge> : null}</div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card card-polished dashboard-card dashboard-card--detections">
          <div className="card-head">
            <div><span className="card-kicker">AI / ALPR</span><h3>Nhận diện gần đây</h3><p className="muted">Lịch sử ALPR nhận dạng</p></div>
            <Link to="/detections">Xem tất cả →</Link>
          </div>
          {!detections || detections.length === 0 ? <EmptyState title="Chưa có dữ liệu" /> : (
            <ul className="list rich-list">
              {detections.slice(0, 5).map((d) => (
                <li key={d.id} className="list-row rich-row">
                  <div><span className="plate-mini">{d.normalized_plate ?? d.ai_plate ?? '—'}</span><small>{d.lane_name ?? d.lane_id} · {d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</small></div>
                  <Badge variant={d.status === 'NEEDS_CONFIRMATION' ? 'warning' : 'success'}>{d.status === 'NEEDS_CONFIRMATION' ? 'Cần xác nhận' : 'Hoàn tất'}</Badge>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card card-polished dashboard-card dashboard-card--lanes">
          <div className="card-head"><div><span className="card-kicker">LANE MONITOR</span><h3>Trạng thái làn xe</h3><p className="muted">Cổng vào / cổng ra</p></div></div>
          {!lanes || lanes.length === 0 ? <EmptyState title="Chưa có dữ liệu" /> : (
            <ul className="list rich-list">
              {lanes.map((l) => (
                <li key={l.id} className="list-row rich-row"><div><strong>{l.name}</strong><small>{l.direction === 'IN' ? 'Làn vào' : l.direction === 'OUT' ? 'Làn ra' : l.direction} · {l.id}</small></div><Badge variant={l.active ? 'success' : 'neutral'}>{l.active ? 'Hoạt động' : 'Tạm dừng'}</Badge></li>
              ))}
            </ul>
          )}
        </section>

        <section className="card card-polished dashboard-card dashboard-card--system system-card">
          <div className="card-head"><div><span className="card-kicker">HEALTH CHECK</span><h3>Tình trạng hệ thống</h3><p className="muted">Thông số vận hành hiện tại</p></div></div>
          <pre className="code-block">{health ? JSON.stringify(health, null, 2) : 'Chưa có dữ liệu — backend chưa cung cấp thông tin kiểm tra.'}</pre>
          <div className="mini-metrics"><span>{manual} lần sửa tay</span><span>{parked} xe đang đỗ</span></div>
        </section>
      </div>
    </div>
  )
}
