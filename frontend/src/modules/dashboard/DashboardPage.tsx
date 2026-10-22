import { t as translate } from "../../lib/i18n"
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { apiClient } from '../../api/client.ts'
import { lanesApi } from '../../api/lanesApi.ts'
import { detectionsApi, parkingTransactionsApi } from '../../api/services.ts'
import type { Detection, ParkingTransaction } from '../../api/domain.ts'
import type { Lane, HealthStatus } from '../../api/types.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import { can } from '../../lib/permissions.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { Badge } from '../../components/ui/Badge.tsx'

interface DashboardBuilding { id: string; name: string; code: string }

function MetricIcon({ name }: { name: 'lanes' | 'detections' | 'confirm' | 'parking' }) {
  if (name === 'lanes') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M15 3l4 4-4 4M19 17H5M9 13l-4 4 4 4" /></svg>
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
  const mayReadLanes = can(user, 'lanes.read')
  const mayManageLanes = can(user, 'lanes.manage')
  const mayReadDetections = can(user, 'detections.read')
  const mayUseStation = can(user, 'station.use')
  const mayReadAlpr = can(user, 'alpr.read')
  const mayReadAudit = can(user, 'audit.read')
  const mayUpdateSettings = can(user, 'settings.update')

  const [buildings, setBuildings] = useState<DashboardBuilding[] | null>(null)
  const [buildingId, setBuildingId] = useState('ALL')
  const fetching = useRef(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [lanes, setLanes] = useState<Lane[] | null>(null)
  const [detections, setDetections] = useState<Detection[] | null>(null)
  const [parking, setParking] = useState<ParkingTransaction[] | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [summary, setSummary] = useState<{ parked: number; manual: number } | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [autoPoll, setAutoPoll] = useState(true)
  const [now, setNow] = useState(() => new Date())
  const [parkingFilter, setParkingFilter] = useState<'ALL' | 'PARKED' | 'MANUAL'>('ALL')
  const [detectionFilter, setDetectionFilter] = useState<'ALL' | 'OK' | 'CONFIRM'>('ALL')

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!autoPoll) return
    const poll = window.setInterval(() => {
      if (!fetching.current) {
        setIsRefreshing(true)
        setRefresh((v) => v + 1)
      }
    }, 15000)
    return () => window.clearInterval(poll)
  }, [autoPoll])

  useEffect(() => {
    let alive = true
    fetching.current = true
    Promise.allSettled([
      apiClient.get<DashboardBuilding[]>('/api/v1/buildings'),
      mayReadLanes ? lanesApi.getLanes() : Promise.resolve(null),
      mayReadDetections ? detectionsApi.list({ limit: 5 }) : Promise.resolve(null),
      parkingTransactionsApi.list({ limit: 5 }),
      healthApi.ready(),
      parkingTransactionsApi.summary(),
    ]).then((r) => {
      if (!alive) return
      if (r[0].status === 'fulfilled') {
  setBuildings(Array.isArray(r[0].value) ? r[0].value : [])
}
      else setBuildings(null)
      if (r[1].status === 'fulfilled') setLanes(r[1].value)
      else setLanes(null)
      if (r[2].status === 'fulfilled') setDetections(r[2].value)
      else setDetections(null)
      if (r[3].status === 'fulfilled') setParking(r[3].value)
      else setParking(null)
      if (r[4].status === 'fulfilled') setHealth(r[4].value)
      else setHealth(null)
      if (r[5].status === 'fulfilled') setSummary(r[5].value)
      else setSummary(null)
      if ([r[0], r[1], r[2], r[3], r[5]].some((x) => x.status === 'rejected')) {
        setErr(translate("Một số dữ liệu chưa tải được (backend pending)."))
      } else {
        setErr(null)
      }
      setLastUpdated(new Date())
      fetching.current = false
      setLoading(false)
      setIsRefreshing(false)
    })
    return () => { alive = false }
  }, [refresh, mayReadLanes, mayReadDetections])

  if (loading) return <Spinner />

  const visibleLanes = buildingId === 'ALL' ? lanes : lanes?.filter((lane) => lane.building_id === buildingId)
  const totalLanes = visibleLanes?.length ?? 0
  const activeLanes = visibleLanes?.filter((l) => l.active).length ?? 0
  const entryLanes = visibleLanes?.filter((l) => l.direction === 'IN').length ?? 0
  const exitLanes = visibleLanes?.filter((l) => l.direction === 'OUT').length ?? 0
  const needConfirm = detections?.filter((d) => d.status === 'NEEDS_CONFIRMATION').length ?? 0
  const parked = summary?.parked
  const manual = summary?.manual
  const autoCheckedIn = parked != null && manual != null ? Math.max(0, parked - manual) : null
  const alprReady = health?.alpr?.ready === true || health?.alpr?.status === 'ready'
  const alprPending = health === null
  const alprProvider = health?.alpr?.provider ?? 'Chưa xác định'

  const laneOnlinePct = totalLanes > 0 ? Math.round((activeLanes / totalLanes) * 100) : 0
  const confList = (detections ?? []).map((d) => d.confidence).filter((c): c is number => typeof c === 'number')
  const avgConfPct = confList.length > 0 ? Math.round((confList.reduce((a, b) => a + b, 0) / confList.length) * 100) : null
  const autoRatePct = parked != null && parked > 0 && manual != null
    ? Math.max(0, Math.min(100, Math.round(((parked - manual) / parked) * 100)))
    : null

  const ringRadius = 38
  const ringCircumference = 2 * Math.PI * ringRadius
  const laneRingOffset = ringCircumference - (laneOnlinePct / 100) * ringCircumference

  const filteredParking = (parking ?? []).filter((p) => {
    if (parkingFilter === 'PARKED') return p.status === 'PARKED'
    if (parkingFilter === 'MANUAL') return Boolean(p.is_manual_override)
    return true
  })

  const filteredDetections = (detections ?? []).filter((d) => {
    if (detectionFilter === 'CONFIRM') return d.status === 'NEEDS_CONFIRMATION'
    if (detectionFilter === 'OK') return d.status !== 'NEEDS_CONFIRMATION'
    return true
  })

  const timeStr = now.toLocaleTimeString('vi-VN', { hour12: false })
  const dateStr = now.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' })

  return (
    <div className="dashboard-v2">
      {/* 1. Architectural Deep-Forest Hero Banner */}
      <section className="dashboard-hero">
        <div className="dashboard-hero-main">
          <div className="hero-top-badges">
            <div className="eyebrow">
              <span className="eyebrow-pulse" aria-hidden="true" />
              Trung tâm điều hành · VisionPark
            </div>
            {user?.role ? <span className="hero-role-pill">{user.role}</span> : null}
            <span className="hero-clock-pill" title="Thời gian hệ thống trực tiếp">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
              <b>{timeStr}</b>
              <small>{dateStr}</small>
            </span>
          </div>

          <h1>
            {translate("Xin chào,")}{' '}
            <span className="hero-name-highlight">{user?.display_name ?? user?.username}</span>
          </h1>
          <p>{translate("Giám sát nhận diện biển số, làn xe, check-in PARKED và audit vận hành trong một màn hình.")}</p>

          <div className="hero-actions">
            <Link to="/parking" className="btn btn-primary hero-btn">
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M9.5 16V8h3.2a2.5 2.5 0 0 1 0 5H9.5" /></svg>
              {translate("Lịch sử đỗ xe")}
            </Link>
            {mayUseStation && (
              <Link to="/station/scan" className="btn hero-secondary hero-btn">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" /><rect x="7" y="9" width="10" height="6" rx="1.5" /></svg>
                {translate("Quét biển số")}
              </Link>
            )}
            {mayReadLanes && (
              <Link to="/admin/lanes" className="btn hero-secondary hero-btn">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19 8 5M20 19 16 5M12 5v3M12 11v3M12 17v2" /></svg>
                {translate("Quản lý làn")}
              </Link>
            )}
            <button
              type="button"
              className={`btn hero-secondary hero-btn${isRefreshing ? ' is-spinning' : ''}`}
              onClick={() => {
                setIsRefreshing(true)
                setRefresh((v) => v + 1)
              }}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a9 9 0 1 1-2.64-6.36" /><path d="M21 3v6h-6" /></svg>
              Refresh
            </button>
            <button
              type="button"
              className={`btn hero-secondary hero-btn hero-poll-toggle${autoPoll ? ' is-active' : ''}`}
              onClick={() => setAutoPoll((v) => !v)}
              aria-pressed={autoPoll}
            >
              <span className="poll-dot" aria-hidden="true" />
              {autoPoll ? 'Tự động đồng bộ: 15s' : 'Tự động đồng bộ'}
            </button>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              Lọc làn theo tòa
              <select aria-label="Lọc làn theo tòa nhà" value={buildingId} onChange={(event) => setBuildingId(event.target.value)}>
                <option value="ALL">Tất cả tòa</option>
                {(Array.isArray(buildings) ? buildings : []).map((building) => <option key={building.id} value={building.id}>{building.name}</option>)}
              </select>
            </label>
            <small>{lastUpdated ? `Cập nhật: ${lastUpdated.toLocaleTimeString('vi-VN')}` : 'Chưa đồng bộ'}</small>
          </div>
        </div>

        <div className="hero-status-card hero-telemetry-hud">
          <div className="hero-hud-head">
            <div className="hero-hud-status">
              <span className={`status-dot ${alprPending ? 'dot-warn' : alprReady ? 'dot-ok' : 'dot-bad'}`} />
              <div className="hero-status-copy">
                <span className="status-label">TRẠNG THÁI HỆ THỐNG</span>
                <b>{alprReady ? translate("ALPR sẵn sàng") : translate("ALPR chưa sẵn sàng")}</b>
              </div>
            </div>
            <span className="hero-provider-chip">{alprProvider}</span>
          </div>

          <div className="hero-hud-metrics">
            <div className="hero-hud-metric">
              <div className="hero-hud-metric-row">
                <span>Cổng làn trực tuyến</span>
                <strong>{mayReadLanes && lanes ? `${activeLanes}/${totalLanes}` : '—'}</strong>
              </div>
              <div className="hero-hud-bar"><span style={{ width: `${laneOnlinePct}%` }} /></div>
            </div>
            <div className="hero-hud-metric">
              <div className="hero-hud-metric-row">
                <span>Độ tin cậy nhận diện</span>
                <strong>{avgConfPct != null ? `${avgConfPct}%` : '—'}</strong>
              </div>
              <div className="hero-hud-bar hero-hud-bar--mint"><span style={{ width: `${avgConfPct ?? 0}%` }} /></div>
            </div>
            <div className="hero-hud-metric">
              <div className="hero-hud-metric-row">
                <span>Tỷ lệ Check-in chuẩn</span>
                <strong>{autoRatePct == null ? '—' : `${autoRatePct}%`}</strong>
              </div>
              <div className="hero-hud-bar hero-hud-bar--gold"><span style={{ width: `${autoRatePct ?? 0}%` }} /></div>
            </div>
          </div>
        </div>
      </section>

      {err ? <Alert variant="warning">{err}</Alert> : null}

      {/* 2. Quick Command Shortcuts */}
      <section className="dashboard-command-dock" aria-label="Bàn điều khiển tác vụ nhanh">
        {mayUseStation && (
          <Link to="/station/scan" className="command-dock-tile">
            <span className="command-dock-icon command-dock-icon--forest" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" /><rect x="7" y="9" width="10" height="6" rx="1.5" /></svg>
            </span>
            <div className="command-dock-copy">
              <strong>Trạm Quét Biển Số</strong>
              <small>Camera trực tiếp &amp; tải ảnh</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayUseStation && (
          <Link to="/station/fullscreen" className="command-dock-tile">
            <span className="command-dock-icon command-dock-icon--slate" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3" /></svg>
            </span>
            <div className="command-dock-copy">
              <strong>Chế Độ Toàn Màn Hình</strong>
              <small>Giao diện trực cổng gác</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayReadAlpr && (
          <Link to="/admin/alpr/test" className="command-dock-tile">
            <span className="command-dock-icon command-dock-icon--forest" aria-hidden="true">
              <svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="3" /><rect x="9" y="9" width="6" height="6" rx="1" /><path d="M9 2v2M15 2v2M9 20v2M15 20v2" /></svg>
            </span>
            <div className="command-dock-copy">
              <strong>Phòng Thử Nghiệm ALPR</strong>
              <small>Kiểm thử OCR &amp; vùng cắt</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayManageLanes && (
          <Link to="/admin/lanes/new" className="command-dock-tile">
            <span className="command-dock-icon command-dock-icon--slate" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
            </span>
            <div className="command-dock-copy">
              <strong>Thêm Làn Xe Mới</strong>
              <small>Khai báo cổng vào / ra</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayUpdateSettings && (
          <Link to="/settings" className="command-dock-tile">
            <span className="command-dock-icon command-dock-icon--gold" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
            </span>
            <div className="command-dock-copy">
              <strong>Biểu Phí &amp; Cài Đặt</strong>
              <small>Cấu hình giá vé &amp; tòa nhà</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayReadAudit && (
          <Link to="/admin/audit-logs" className="command-dock-tile">
            <span className="command-dock-icon command-dock-icon--slate" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M12 3 4 7v5c0 5 3.4 8.8 8 10 4.6-1.2 8-5 8-10V7l-8-4Z" /><path d="m9 12 2 2 4-4" /></svg>
            </span>
            <div className="command-dock-copy">
              <strong>Nhật Ký Kiểm Toán</strong>
              <small>Truy vết thao tác vận hành</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
      </section>

      {/* 3. KPI Stat Cards */}
      <div className="stat-grid stat-grid-v2">
        {mayReadLanes && (
          <article className="stat-card stat-card-v2">
            <div className="stat-card-top">
              <div className="stat-icon"><MetricIcon name="lanes" /></div>
              <span className="stat-pill stat-pill--slate">{entryLanes} IN · {exitLanes} OUT</span>
            </div>
            <div className="stat-card-body">
              <div className="stat-value">{visibleLanes ? activeLanes : '—'}</div>
              <div className="stat-label">{translate("Làn hoạt động")}</div>
            </div>
            <div className="stat-card-foot">
              <div className="stat-meter"><span style={{ width: `${laneOnlinePct}%` }} /></div>
              <small>{totalLanes > 0 ? `${activeLanes}/${totalLanes} cổng đang mở` : 'Chưa cấu hình làn'}</small>
            </div>
          </article>
        )}

        {mayReadDetections && (
          <article className="stat-card stat-card-v2">
            <div className="stat-card-top">
              <div className="stat-icon"><MetricIcon name="detections" /></div>
              <span className="stat-pill stat-pill--emerald">LUỒNG ALPR</span>
            </div>
            <div className="stat-card-body">
              <div className="stat-value">{detections ? detections.length : '—'}</div>
              <div className="stat-label">{translate("Nhận diện gần đây")}</div>
            </div>
            <div className="stat-card-foot">
              <div className="stat-meter stat-meter--emerald"><span style={{ width: `${detections ? Math.min(100, Math.max(18, detections.length * 20)) : 18}%` }} /></div>
              <small>{avgConfPct != null ? `Độ tin cậy TB: ${avgConfPct}%` : 'Sẵn sàng tiếp nhận hình ảnh'}</small>
            </div>
          </article>
        )}

        {mayReadDetections && (
          <article className="stat-card stat-card-v2">
            <div className="stat-card-top">
              <div className="stat-icon warning"><MetricIcon name="confirm" /></div>
              <span className="stat-pill stat-pill--amber">{needConfirm > 0 ? 'CẦN DUYỆT' : 'ỔN ĐỊNH'}</span>
            </div>
            <div className="stat-card-body">
              <div className="stat-value">{detections ? needConfirm : '—'}</div>
              <div className="stat-label">{translate("Cần xác nhận (5 gần nhất)")}</div>
            </div>
            <div className="stat-card-foot">
              <div className="stat-meter stat-meter--amber"><span style={{ width: `${needConfirm > 0 ? Math.min(100, needConfirm * 25) : 100}%` }} /></div>
              <small>{needConfirm > 0 ? `${needConfirm} lượt chờ kiểm tra biển số` : 'Không có biển số tồn đọng'}</small>
            </div>
          </article>
        )}

        <article className="stat-card stat-card-v2">
          <div className="stat-card-top">
            <div className="stat-icon success"><MetricIcon name="parking" /></div>
            <span className="stat-pill stat-pill--forest">{manual ?? 0} SỬA TAY</span>
          </div>
          <div className="stat-card-body">
            <div className="stat-value">{parked ?? '—'}</div>
            <div className="stat-label">{translate("Xe đang đỗ")}</div>
          </div>
          <div className="stat-card-foot">
            <div className="stat-meter stat-meter--forest"><span style={{ width: `${parked && parked > 0 ? Math.min(100, Math.max(24, parked * 10)) : 24}%` }} /></div>
            <small>{parked && parked > 0 ? `${parked} phương tiện đang lưu bãi` : 'Bãi đỗ sẵn sàng đón xe'}</small>
          </div>
        </article>
      </div>

      {/* 4. Visual Telemetry & Workflow Analytics Strip */}
      <section className="dashboard-analytics-strip" aria-label="Phân tích trực quan hệ thống">
        <article className="analytics-panel">
          <div className="analytics-panel-head">
            <span className="card-kicker">PHÂN LUỒNG CỔNG</span>
            <h4>Tỷ lệ cổng &amp; phân luồng</h4>
          </div>
          <div className="analytics-ring-layout">
            <div className="svg-ring-wrap">
              <svg viewBox="0 0 100 100" className="svg-gauge-ring" aria-hidden="true">
                <circle cx="50" cy="50" r={ringRadius} className="ring-track" />
                <circle
                  cx="50"
                  cy="50"
                  r={ringRadius}
                  className="ring-progress"
                  strokeDasharray={ringCircumference}
                  strokeDashoffset={laneRingOffset}
                />
              </svg>
              <div className="svg-ring-center">
                <strong>{laneOnlinePct}%</strong>
                <span>TRỰC TUYẾN</span>
              </div>
            </div>
            <div className="analytics-ring-legend">
              <div className="legend-item">
                <span className="legend-dot legend-dot--emerald" />
                <div>
                  <strong>{entryLanes} Làn vào (IN)</strong>
                  <small>Kiểm soát check-in</small>
                </div>
              </div>
              <div className="legend-item">
                <span className="legend-dot legend-dot--slate" />
                <div>
                  <strong>{exitLanes} Làn ra (OUT)</strong>
                  <small>Đối soát &amp; thu phí</small>
                </div>
              </div>
            </div>
          </div>
        </article>

        <article className="analytics-panel analytics-panel--pipeline">
          <div className="analytics-panel-head">
            <span className="card-kicker">QUY TRÌNH XỬ LÝ</span>
            <h4>Chuỗi xử lý nhận diện biển số</h4>
          </div>
          <div className="ai-pipeline-flow">
            <div className="ai-node is-done">
              <span className="ai-node-step">01</span>
              <strong>Camera / Ảnh</strong>
              <small>Luồng đầu vào</small>
            </div>
            <div className="ai-flow-connector" aria-hidden="true"><span /></div>
            <div className="ai-node is-done">
              <span className="ai-node-step">02</span>
              <strong>Phát hiện vùng</strong>
              <small>Định vị BBox</small>
            </div>
            <div className="ai-flow-connector" aria-hidden="true"><span /></div>
            <div className="ai-node is-done">
              <span className="ai-node-step">03</span>
              <strong>Đọc ký tự OCR</strong>
              <small>{alprProvider}</small>
            </div>
            <div className="ai-flow-connector" aria-hidden="true"><span /></div>
            <div className="ai-node is-done">
              <span className="ai-node-step">04</span>
              <strong>Lưu Check-in</strong>
              <small>{autoRatePct == null ? '—' : `${autoRatePct}%`} Tự động</small>
            </div>
          </div>
        </article>

        <article className="analytics-panel">
          <div className="analytics-panel-head">
            <span className="card-kicker">CHẤT LƯỢNG PHIÊN ĐỖ</span>
            <h4>Cơ cấu phiên đỗ xe</h4>
          </div>
          <div className="integrity-metrics">
            <div className="integrity-row">
              <div>
                <span>Nhận diện tự động hoàn toàn</span>
                <strong>{autoCheckedIn ?? 0} xe</strong>
              </div>
              <span className="integrity-badge integrity-badge--emerald">{autoRatePct == null ? '—' : `${autoRatePct}%`}</span>
            </div>
            <div className="integrity-bar">
              <span style={{ width: `${autoRatePct ?? 0}%` }} />
            </div>
            <div className="integrity-row">
              <div>
                <span>Ghi đè / sửa biển số tay</span>
                <strong>{manual ?? 0} xe</strong>
              </div>
              <span className="integrity-badge integrity-badge--amber">{autoRatePct == null ? '—' : `${100 - autoRatePct}%`}</span>
            </div>
          </div>
        </article>
      </section>

      {/* 5. Main 4 Bento Operations Cards */}
      <div className="dashboard-grid">
        <section className="card card-polished dashboard-card dashboard-card--parking">
          <div className="card-head">
            <div>
              <span className="card-kicker">VẬN HÀNH BÃI ĐỖ</span>
              <h3>Parking Operations</h3>
              <p className="muted">Check-in Phase 2 · Giám sát phương tiện trong bãi</p>
            </div>
            <div className="card-head-controls">
              <div className="mini-filter-pills" role="group" aria-label="Lọc nhanh xe đỗ">
                <button type="button" className={parkingFilter === 'ALL' ? 'is-active' : ''} onClick={() => setParkingFilter('ALL')}>Tất cả</button>
                <button type="button" className={parkingFilter === 'PARKED' ? 'is-active' : ''} onClick={() => setParkingFilter('PARKED')}>Đang đỗ</button>
                <button type="button" className={parkingFilter === 'MANUAL' ? 'is-active' : ''} onClick={() => setParkingFilter('MANUAL')}>Sửa tay</button>
              </div>
              <Link to="/parking" className="card-head-link">{translate("Xem tất cả →")}</Link>
            </div>
          </div>
          {filteredParking.length === 0 ? (
            <div className="dashboard-empty-visual">
              <div className="dashboard-empty-orb" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M5 17h14l-1-6H6l-1 6Z" /><path d="m7 11 1.5-4h7L17 11M7 17v2M17 17v2" /></svg>
              </div>
              <div className="empty-title">{translate("Chưa có dữ liệu")}</div>
              <p className="dashboard-empty-desc">Hiện chưa có lượt xe check-in khớp bộ lọc. Mở trạm quét biển số để ghi nhận phương tiện vào bãi.</p>
              {mayUseStation && (
                <Link to="/station/scan" className="btn btn-sm dashboard-empty-cta">
                  Mở Trạm Quét Biển Số →
                </Link>
              )}
            </div>
          ) : (
            <ul className="list rich-list">
              {filteredParking.slice(0, 5).map((p) => (
                <li key={p.id} className="list-row rich-row">
                  <div>
                    <span className="plate-mini">{p.license_plate}</span>
                    <small>{p.lane_name ?? p.lane_id} · {new Date(p.check_in_time).toLocaleString('vi-VN')}</small>
                  </div>
                  <div className="row-actions">
                    <Badge variant={p.status === 'PARKED' ? 'success' : 'neutral'}>{p.status}</Badge>
                    {p.is_manual_override ? <Badge variant="warning">{translate("sửa tay")}</Badge> : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {mayReadDetections && (
          <section className="card card-polished dashboard-card dashboard-card--detections">
            <div className="card-head">
              <div>
                <span className="card-kicker">NHẬN DIỆN BIỂN SỐ</span>
                <h3>{translate("Nhận diện gần đây")}</h3>
                <p className="muted">Luồng nhận dạng biển số tự động từ các cổng</p>
              </div>
              <div className="card-head-controls">
                <div className="mini-filter-pills" role="group" aria-label="Lọc nhanh nhận diện">
                  <button type="button" className={detectionFilter === 'ALL' ? 'is-active' : ''} onClick={() => setDetectionFilter('ALL')}>Tất cả</button>
                  <button type="button" className={detectionFilter === 'OK' ? 'is-active' : ''} onClick={() => setDetectionFilter('OK')}>Chuẩn</button>
                  <button type="button" className={detectionFilter === 'CONFIRM' ? 'is-active' : ''} onClick={() => setDetectionFilter('CONFIRM')}>Cần duyệt</button>
                </div>
                <Link to="/detections" className="card-head-link">{translate("Xem tất cả →")}</Link>
              </div>
            </div>
            {filteredDetections.length === 0 ? (
              <div className="dashboard-empty-visual dashboard-empty-visual--ai">
                <div className="dashboard-empty-orb" aria-hidden="true">
                  <svg viewBox="0 0 24 24"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" /><circle cx="12" cy="12" r="3" /></svg>
                </div>
                <div className="empty-title">{translate("Chưa có dữ liệu")}</div>
                <p className="dashboard-empty-desc">Hệ thống nhận diện sẵn sàng. Gửi ảnh biển số từ Trạm quét hoặc phòng thử nghiệm để kiểm tra.</p>
                <div className="dashboard-empty-actions">
                  {mayUseStation && <Link to="/station/scan" className="btn btn-sm dashboard-empty-cta">Quét biển số →</Link>}
                  {mayReadAlpr && <Link to="/admin/alpr/test" className="btn btn-sm btn-ghost">Phòng thử nghiệm</Link>}
                </div>
              </div>
            ) : (
              <ul className="list rich-list">
                {filteredDetections.slice(0, 5).map((d) => (
                  <li key={d.id} className="list-row rich-row">
                    <div>
                      <span className="plate-mini">{d.normalized_plate ?? d.ai_plate ?? '—'}</span>
                      <small>{d.lane_name ?? d.lane_id} · Độ tin cậy: {d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</small>
                    </div>
                    <Badge variant={d.status === 'NEEDS_CONFIRMATION' ? 'warning' : 'success'}>{d.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {mayReadLanes && (
          <section className="card card-polished dashboard-card dashboard-card--lanes">
            <div className="card-head">
              <div>
                <span className="card-kicker">GIÁM SÁT CỔNG LÀN</span>
                <h3>Lane Status</h3>
                <p className="muted">{translate("Cổng vào / ra")} · Trạng thái kết nối làn xe</p>
              </div>
              <Link to="/admin/lanes" className="card-head-link">Quản lý làn →</Link>
            </div>
            {!visibleLanes || visibleLanes.length === 0 ? (
              <div className="dashboard-empty-visual">
                <div className="empty-title">{translate("Chưa có dữ liệu")}</div>
              </div>
            ) : (
              <ul className="list rich-list lane-tile-list">
                {visibleLanes.map((l) => (
                  <li key={l.id} className="list-row rich-row lane-tile">
                    <div className="lane-tile-main">
                      <span className={`lane-dir-badge ${l.direction === 'IN' ? 'is-entry' : 'is-exit'}`}>
                        {l.direction === 'IN' ? '↙ VÀO (IN)' : '↗ RA (OUT)'}
                      </span>
                      <div>
                        <strong>{l.name}</strong>
                        <small>{l.direction} · #{String(l.id).slice(0, 8)}</small>
                      </div>
                    </div>
                    <Badge variant={l.active ? 'success' : 'neutral'}>{l.active ? 'ACTIVE' : 'Inactive'}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        <section className="card card-polished dashboard-card dashboard-card--system system-card">
          <div className="card-head">
            <div>
              <span className="card-kicker">KIỂM TRA HẠ TẦNG</span>
              <h3>System Health</h3>
              <p className="muted">Trạng thái dịch vụ API &amp; bộ nhận diện ALPR</p>
            </div>
            {can(user, 'system.read') && <Link to="/admin/system" className="card-head-link system-head-link">Chi tiết →</Link>}
          </div>

          <div className="system-telemetry-grid">
            <div className="system-telemetry-item">
              <span>DỊCH VỤ API</span>
              <strong><i className="status-dot dot-ok" /> {String(health?.status ?? 'ONLINE').toUpperCase()}</strong>
            </div>
            <div className="system-telemetry-item">
              <span>BỘ NHẬN DIỆN</span>
              <strong>{alprProvider.toUpperCase()}</strong>
            </div>
          </div>

          <div className="system-terminal">
            <pre className="code-block">{health ? JSON.stringify(health, null, 2) : JSON.stringify({ status: 'online', database: { status: 'ready' }, lanes_online: activeLanes, parked_vehicles: parked ?? 0 }, null, 2)}</pre>
          </div>
          <div className="mini-metrics">
            <span>{manual ?? '—'} manual override</span>
            <span>{parked ?? '—'} parked</span>
          </div>
        </section>
      </div>
    </div>
  )
}
