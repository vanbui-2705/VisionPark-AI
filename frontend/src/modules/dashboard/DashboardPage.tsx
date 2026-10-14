import { t as translate } from "../../lib/i18n"
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { lanesApi } from '../../api/lanesApi.ts'
import { detectionsApi, parkingTransactionsApi } from '../../api/services.ts'
import type { Detection, ParkingTransaction } from '../../api/domain.ts'
import type { Lane, HealthStatus } from '../../api/types.ts'
import { useAuth } from '../auth/AuthContext.tsx'
import { can } from '../../lib/permissions.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { Badge } from '../../components/ui/Badge.tsx'

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

  const [lanes, setLanes] = useState<Lane[] | null>(null)
  const [detections, setDetections] = useState<Detection[] | null>(null)
  const [parking, setParking] = useState<ParkingTransaction[] | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [summary, setSummary] = useState<{ parked: number; manual: number } | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [autoPoll, setAutoPoll] = useState(false)
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
      setIsRefreshing(true)
      setRefresh((v) => v + 1)
    }, 15000)
    return () => window.clearInterval(poll)
  }, [autoPoll])

  useEffect(() => {
    let alive = true
    Promise.allSettled([
      mayReadLanes ? lanesApi.getLanes() : Promise.resolve(null),
      mayReadDetections ? detectionsApi.list({ limit: 5 }) : Promise.resolve(null),
      parkingTransactionsApi.list({ limit: 5 }),
      healthApi.ready(),
      parkingTransactionsApi.summary(),
    ]).then((r) => {
      if (!alive) return
      if (r[0].status === 'fulfilled') setLanes(r[0].value)
      if (r[1].status === 'fulfilled') setDetections(r[1].value)
      if (r[2].status === 'fulfilled') setParking(r[2].value)
      if (r[3].status === 'fulfilled') setHealth(r[3].value)
      if (r[4].status === 'fulfilled') setSummary(r[4].value)
      if (r.some((x) => x.status === 'rejected')) setErr(translate("Một số dữ liệu chưa tải được (backend pending)."))
      setLoading(false)
      setIsRefreshing(false)
    })
    return () => { alive = false }
  }, [refresh, mayReadLanes, mayReadDetections])

  if (loading) return <Spinner />

  const totalLanes = lanes?.length ?? 0
  const activeLanes = lanes?.filter((l) => l.active).length ?? 0
  const entryLanes = lanes?.filter((l) => l.direction === 'IN').length ?? 0
  const exitLanes = lanes?.filter((l) => l.direction === 'OUT').length ?? 0
  const needConfirm = detections?.filter((d) => d.status === 'NEEDS_CONFIRMATION').length ?? 0
  const parked = summary?.parked
  const manual = summary?.manual
  const alprReady = health?.alpr?.ready === true || (health?.alpr as { status?: string } | undefined)?.status === 'ready'
  const alprPending = health === null
  const alprProvider = health?.alpr?.provider ?? '—'

  const confList = (detections ?? []).map((d) => d.confidence).filter((c): c is number => typeof c === 'number')
  const avgConfPct = confList.length > 0 ? Math.round((confList.reduce((a, b) => a + b, 0) / confList.length) * 100) : null
  const autoRatePct = parked != null && parked > 0 && manual != null
    ? Math.max(0, Math.min(100, Math.round(((parked - manual) / parked) * 100)))
    : 100

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
      {/* 1. Editorial Hero Surface (White Canvas + Warm Cream Callout per design.md) */}
      <section className="dashboard-hero">
        <div className="dashboard-hero-main">
          <div className="hero-top-badges">
            <div className="eyebrow">
              <span className="eyebrow-pulse" aria-hidden="true" />
              Trung tâm điều hành · VisionPark
            </div>
            {user?.role ? <span className="hero-role-pill">{user.role}</span> : null}
            <span className="hero-clock-pill" title="Thời gian hệ thống">
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
              {translate("Lịch sử đỗ xe")}
            </Link>
            {mayUseStation && (
              <Link to="/station/scan" className="btn hero-secondary hero-btn">
                {translate("Quét biển số")}
              </Link>
            )}
            {mayReadLanes && (
              <Link to="/admin/lanes" className="btn hero-secondary hero-btn">
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
              Refresh
            </button>
            <button
              type="button"
              className={`btn hero-secondary hero-btn hero-poll-toggle${autoPoll ? ' is-active' : ''}`}
              onClick={() => setAutoPoll((v) => !v)}
              aria-pressed={autoPoll}
            >
              <span className="poll-dot" aria-hidden="true" />
              {autoPoll ? 'Tự động làm mới: 15s' : 'Tự động làm mới'}
            </button>
          </div>
        </div>

        <aside className="hero-status-card hero-editorial-summary" aria-label="Tóm tắt ca trực">
          <div className="hero-hud-head">
            <div className="hero-hud-status">
              <span className={`status-dot ${alprPending ? 'dot-warn' : alprReady ? 'dot-ok' : 'dot-bad'}`} />
              <div className="hero-status-copy">
                <span className="status-label">TRẠNG THÁI NHẬN DIỆN</span>
                <b>{alprReady ? translate("ALPR sẵn sàng") : translate("ALPR chưa sẵn sàng")}</b>
              </div>
            </div>
            <span className="hero-provider-chip">{alprProvider}</span>
          </div>

          <div className="hero-summary-cells">
            <div className="hero-summary-cell">
              <span>Cổng mở</span>
              <strong>{mayReadLanes ? `${activeLanes}/${totalLanes}` : '—'}</strong>
            </div>
            <div className="hero-summary-cell">
              <span>Đang đỗ</span>
              <strong>{parked ?? 0}</strong>
            </div>
            <div className="hero-summary-cell">
              <span>Chờ duyệt</span>
              <strong>{mayReadDetections ? needConfirm : '—'}</strong>
            </div>
          </div>

          <div className="hero-summary-foot">
            <span>Tỷ lệ tự động: <strong>{autoRatePct}%</strong></span>
            <span>{mayReadLanes ? `${entryLanes} làn vào · ${exitLanes} làn ra` : 'Chế độ vận hành tiêu chuẩn'}</span>
          </div>
        </aside>
      </section>

      {err ? <Alert variant="warning">{err}</Alert> : null}

      {/* 2. Editorial KPI Metric Strip */}
      <div className="stat-grid stat-grid-v2">
        {mayReadLanes && (
          <article className="stat-card stat-card-v2">
            <div className="stat-card-top">
              <span className="stat-index">01 / CỔNG LÀN</span>
              <div className="stat-icon"><MetricIcon name="lanes" /></div>
            </div>
            <div className="stat-card-body">
              <div className="stat-value">{lanes ? activeLanes : '—'}</div>
              <div className="stat-label">{translate("Làn hoạt động")}</div>
            </div>
            <div className="stat-card-foot">
              <small>{totalLanes > 0 ? `${entryLanes} cổng vào · ${exitLanes} cổng ra (${activeLanes}/${totalLanes} mở)` : 'Chưa cấu hình làn xe'}</small>
            </div>
          </article>
        )}

        {mayReadDetections && (
          <article className="stat-card stat-card-v2">
            <div className="stat-card-top">
              <span className="stat-index">02 / NHẬN DIỆN</span>
              <div className="stat-icon"><MetricIcon name="detections" /></div>
            </div>
            <div className="stat-card-body">
              <div className="stat-value">{detections ? detections.length : '—'}</div>
              <div className="stat-label">{translate("Nhận diện gần đây")}</div>
            </div>
            <div className="stat-card-foot">
              <small>{avgConfPct != null ? `Độ tin cậy trung bình: ${avgConfPct}%` : '5 bản ghi nhận diện mới nhất'}</small>
            </div>
          </article>
        )}

        {mayReadDetections && (
          <article className="stat-card stat-card-v2 stat-card-v2--cream">
            <div className="stat-card-top">
              <span className="stat-index">03 / KIỂM DUYỆT</span>
              <div className="stat-icon warning"><MetricIcon name="confirm" /></div>
            </div>
            <div className="stat-card-body">
              <div className="stat-value">{detections ? needConfirm : '—'}</div>
              <div className="stat-label">{translate("Cần xác nhận (5 gần nhất)")}</div>
            </div>
            <div className="stat-card-foot">
              <small>{needConfirm > 0 ? `${needConfirm} biển số cần Operator đối chiếu` : 'Không có lượt chờ xác nhận'}</small>
            </div>
          </article>
        )}

        <article className="stat-card stat-card-v2 stat-card-v2--forest">
          <div className="stat-card-top">
            <span className="stat-index">04 / LƯU BÃI</span>
            <div className="stat-icon success"><MetricIcon name="parking" /></div>
          </div>
          <div className="stat-card-body">
            <div className="stat-value">{parked ?? '—'}</div>
            <div className="stat-label">{translate("Xe đang đỗ")}</div>
          </div>
          <div className="stat-card-foot">
            <small>{manual != null ? `${manual} lượt ghi đè biển số thủ công` : 'Đang đồng bộ số liệu bãi xe'}</small>
          </div>
        </article>
      </div>

      {/* 3. Restrained Quick Shortcuts Bar */}
      <nav className="dashboard-command-dock" aria-label="Lối tắt nghiệp vụ">
        {mayUseStation && (
          <Link to="/station/scan" className="command-dock-tile">
            <div className="command-dock-copy">
              <span className="command-dock-kicker">TRẠM GÁC</span>
              <strong>Trạm quét biển số</strong>
              <small>Camera trực tiếp &amp; tải ảnh</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayUseStation && (
          <Link to="/station/fullscreen" className="command-dock-tile">
            <div className="command-dock-copy">
              <span className="command-dock-kicker">MÀN HÌNH TRẠM</span>
              <strong>Chế độ toàn màn hình</strong>
              <small>Giao diện trực cổng tốc độ cao</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayReadAlpr && (
          <Link to="/admin/alpr/test" className="command-dock-tile">
            <div className="command-dock-copy">
              <span className="command-dock-kicker">KIỂM THỬ</span>
              <strong>Phòng thử nghiệm ALPR</strong>
              <small>Kiểm tra cắt vùng &amp; đọc ký tự</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayManageLanes && (
          <Link to="/admin/lanes/new" className="command-dock-tile">
            <div className="command-dock-copy">
              <span className="command-dock-kicker">CẤU HÌNH CỔNG</span>
              <strong>Thêm làn xe mới</strong>
              <small>Khai báo cổng vào / cổng ra</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayUpdateSettings && (
          <Link to="/settings" className="command-dock-tile">
            <div className="command-dock-copy">
              <span className="command-dock-kicker">THAM SỐ</span>
              <strong>Biểu phí &amp; cài đặt</strong>
              <small>Ngưỡng nhận diện &amp; giá vé</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
        {mayReadAudit && (
          <Link to="/admin/audit-logs" className="command-dock-tile">
            <div className="command-dock-copy">
              <span className="command-dock-kicker">ĐỐI SOÁT</span>
              <strong>Nhật ký kiểm toán</strong>
              <small>Lịch sử thao tác hệ thống</small>
            </div>
            <span className="command-dock-arrow" aria-hidden="true">→</span>
          </Link>
        )}
      </nav>

      {/* 4. Main 4 Bento Operations Cards */}
      <div className="dashboard-grid">
        <section className="card card-polished dashboard-card dashboard-card--parking">
          <div className="card-head">
            <div>
              <span className="card-kicker">01 · PHƯƠNG TIỆN TRONG BÃI</span>
              <h3>Parking Operations</h3>
              <p className="muted">Check-in Phase 2 · Các lượt xe vào bãi gần nhất</p>
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
              <div className="empty-title">{translate("Chưa có dữ liệu")}</div>
              <p className="dashboard-empty-desc">Chưa có lượt xe check-in khớp bộ lọc hiện tại.</p>
              {mayUseStation && (
                <Link to="/station/scan" className="btn btn-sm dashboard-empty-cta">
                  Mở trạm quét biển số →
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
                <span className="card-kicker">02 · NHẬN DIỆN BIỂN SỐ</span>
                <h3>{translate("Nhận diện gần đây")}</h3>
                <p className="muted">Kết quả đọc biển số từ luồng camera và ảnh tải lên</p>
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
              <div className="dashboard-empty-visual">
                <div className="empty-title">{translate("Chưa có dữ liệu")}</div>
                <p className="dashboard-empty-desc">Chưa ghi nhận lượt đọc biển số nào trong danh sách gần đây.</p>
                <div className="dashboard-empty-actions">
                  {mayUseStation && <Link to="/station/scan" className="btn btn-sm dashboard-empty-cta">Quét biển số →</Link>}
                  {mayReadAlpr && <Link to="/admin/alpr/test" className="btn btn-sm btn-ghost">Thử nghiệm ALPR</Link>}
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
                <span className="card-kicker">03 · DANH SÁCH CỔNG</span>
                <h3>Lane Status</h3>
                <p className="muted">{translate("Cổng vào / ra")} · Phân luồng phương tiện</p>
              </div>
              <Link to="/admin/lanes" className="card-head-link">Quản lý làn →</Link>
            </div>
            {!lanes || lanes.length === 0 ? (
              <div className="dashboard-empty-visual">
                <div className="empty-title">{translate("Chưa có dữ liệu")}</div>
              </div>
            ) : (
              <ul className="list rich-list lane-tile-list">
                {lanes.map((l) => (
                  <li key={l.id} className="list-row rich-row lane-tile">
                    <div className="lane-tile-main">
                      <span className={`lane-dir-badge ${l.direction === 'IN' ? 'is-entry' : 'is-exit'}`}>
                        {l.direction === 'IN' ? 'VÀO · IN' : 'RA · OUT'}
                      </span>
                      <div>
                        <strong>{l.name}</strong>
                        <small>Mã cổng #{String(l.id).slice(0, 8)}</small>
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
              <span className="card-kicker">04 · HẠ TẦNG DỊCH VỤ</span>
              <h3>System Health</h3>
              <p className="muted">Trạng thái kết nối API &amp; bộ nhận diện ALPR</p>
            </div>
            {can(user, 'system.read') && <Link to="/admin/system" className="card-head-link system-head-link">Chi tiết →</Link>}
          </div>

          <div className="system-telemetry-grid">
            <div className="system-telemetry-item">
              <span>DỊCH VỤ API</span>
              <strong><i className="status-dot dot-ok" /> {String(health?.status ?? 'READY').toUpperCase()}</strong>
            </div>
            <div className="system-telemetry-item">
              <span>BỘ ĐỌC BIỂN SỐ</span>
              <strong>{alprProvider}</strong>
            </div>
          </div>

          <pre className="code-block">{health ? JSON.stringify(health, null, 2) : translate("Chưa có dữ liệu — backend chưa cung cấp health đầy đủ.")}</pre>
          <div className="mini-metrics">
            <span>{manual ?? '—'} manual override</span>
            <span>{parked ?? '—'} parked</span>
          </div>
        </section>
      </div>
    </div>
  )
}
