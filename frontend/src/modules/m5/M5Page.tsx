import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { apiClient } from '../../api/client.ts'
import { useAuth } from '../auth/AuthContext.tsx'

type Building = { id: string; name: string }
type Capacity = { physical_capacity: number; safe_capacity: number; nearly_full_threshold: number; full_threshold: number }
type LotSettings = { schema_version: 1; information: Record<string, unknown>; capacities: Record<string, Capacity>; [key: string]: unknown }
type SettingsResponse = { revision: number; settings: LotSettings }
type Summary = { building_id: string; lanes_total: number; lanes_active: number; parked: number; capacity: number | null; available: number | null; occupancy_status: string }
type Stat = { stat_date: string; vehicle_type: string; entries: number; exits: number; revenue: number | string; occupancy_peak: number }
type Device = { code: string; name: string; device_type: string; status: string; last_heartbeat_at: string | null }
type Availability = { vehicle_type: string; occupied: number; safe_capacity: number; physical_capacity: number; available: number; available_for_visitor: number; status: string }
type CashReport = { entries: number; exits: number; cash_revenue_vnd: number }
const base = '/api/v1/m5'
const todayLocal = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }

export function M5Page() {
  const { user } = useAuth()
  const [buildings, setBuildings] = useState<Building[]>([])
  const [buildingId, setBuildingId] = useState('')
  const [start, setStart] = useState(todayLocal())
  const [end, setEnd] = useState(todayLocal())
  const [shiftStart, setShiftStart] = useState('08:00')
  const [shiftEnd, setShiftEnd] = useState('16:00')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [stats, setStats] = useState<Stat[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [alerts, setAlerts] = useState<Device[]>([])
  const [cashReport, setCashReport] = useState<CashReport | null>(null)
  const [availability, setAvailability] = useState<Availability[]>([])
  const [lot, setLot] = useState<SettingsResponse | null>(null)
  const [capacities, setCapacities] = useState<Record<string, Capacity> | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const canConfigureCapacity = user?.role === 'BUILDING_ADMIN' || (user?.role as string) === 'ADMIN'

  useEffect(() => {
    apiClient.get<Building[]>('/api/v1/buildings')
      .then(items => { setBuildings(items); if (items.length) setBuildingId(items[0].id) })
      .catch(e => setError(String(e)))
  }, [])

  useEffect(() => {
    if (!buildingId) return
    let active = true
    const load = async () => {
      try {
        const params = { building_id: buildingId }
        const [a, b, c, d, capacity] = await Promise.all([
          apiClient.get<Summary>(`${base}/dashboard`, { params }),
          apiClient.get<Stat[]>(`${base}/daily-stats`, { params: { ...params, start, end } }),
          apiClient.get<Device[]>(`${base}/devices`, { params }),
          apiClient.get<Device[]>(`${base}/devices/alerts`, { params }),
          apiClient.get<Availability[]>('/api/v1/parking/availability', { params }),
        ])
        if (active) { setSummary(a); setStats(b); setDevices(c); setAlerts(d); setAvailability(capacity); setError('') }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : String(e)) }
    }
    void load()
    const interval = window.setInterval(() => { void load() }, 15000)
    return () => { active = false; window.clearInterval(interval) }
  }, [buildingId, start, end])

  useEffect(() => {
    if (!buildingId) return
    let active = true
    apiClient.get<SettingsResponse>('/api/v1/settings/lot', {
      params: user?.role === 'SYSTEM_ADMIN' ? { building_id: buildingId } : undefined,
    }).then(result => {
      if (active) { setLot(result); setCapacities(result.settings.capacities) }
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : String(e)) })
    return () => { active = false }
  }, [buildingId, user?.role])

  const totalCapacity = useMemo(() => capacities ? Object.values(capacities).reduce((sum, value) => sum + Number(value.safe_capacity || 0), 0) : 0, [capacities])
  const totalOccupied = useMemo(() => availability.reduce((sum, value) => sum + value.occupied, 0), [availability])
  const available = capacities && totalCapacity > 0 ? availability.reduce((sum, item) => {
    const cap = capacities[item.vehicle_type]
    return sum + (cap?.safe_capacity ? Math.max(0, cap.safe_capacity - item.occupied) : 0)
  }, 0) : null
  const occupancy = totalCapacity > 0 ? Math.min(100, totalOccupied / totalCapacity * 100) : null

  const download = async (format: 'csv' | 'pdf') => {
    setBusy(true)
    try {
      const blob = await apiClient.getBlob(`${base}/daily-stats.${format}`, { params: { building_id: buildingId, start, end }, timeoutMs: 30000 })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a'); link.href = url; link.download = `visionpark-m5-${start}-${end}.${format}`; link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }

  const exportSessions = async () => {
    setBusy(true)
    try {
      const from = new Date(`${start}T00:00:00`).toISOString()
      const to = new Date(`${end}T23:59:59`).toISOString()
      const blob = await apiClient.getBlob('/api/v1/lifecycle/sessions/export-csv', { params: { from_time: from, to_time: to }, timeoutMs: 30000 })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a'); link.href = url; link.download = `parking-sessions-${start}-${end}.csv`; link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }

  const loadCashReport = async () => {
    setBusy(true); setError(''); setCashReport(null)
    try {
      const from = new Date(`${start}T${shiftStart}:00`)
      let to = new Date(`${end}T${shiftEnd}:00`)
      if (to <= from && start === end) to = new Date(to.getTime() + 24 * 60 * 60 * 1000)
      const report = await apiClient.get<CashReport>(`${base}/cash-shifts`, { params: { building_id: buildingId, start: from.toISOString(), end: to.toISOString() } })
      setCashReport(report)
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false) }
  }

  const saveCapacity = async (event: FormEvent) => {
    event.preventDefault()
    if (!lot || !capacities) return
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await apiClient.put<SettingsResponse>('/api/v1/settings/lot', { revision: lot.revision, settings: { ...lot.settings, capacities } })
      setLot(result); setCapacities(result.settings.capacities); setMessage('Đã lưu sức chứa an toàn.')
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false) }
  }

  return <main className="data-page" style={{ maxWidth: 1160 }}>
    <h1>Báo cáo vận hành</h1>
    {error && <p role="alert" style={{ color: 'crimson' }}>{error}</p>}{message && <p role="status">{message}</p>}
    <section className="card card-polished stack">
      <div className="form-grid">
        <label className="field"><span>Tòa nhà</span><select value={buildingId} onChange={e => setBuildingId(e.target.value)}>{buildings.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
        <label className="field"><span>Từ ngày</span><input type="date" value={start} onChange={e => setStart(e.target.value)} /></label>
        <label className="field"><span>Đến ngày</span><input type="date" value={end} onChange={e => setEnd(e.target.value)} /></label>
      </div>
      <div className="row-actions"><button className="btn" disabled={!buildingId || busy} onClick={() => void download('csv')}>Xuất thống kê CSV</button><button className="btn" disabled={!buildingId || busy} onClick={() => void download('pdf')}>Xuất thống kê PDF</button><button className="btn" disabled={!buildingId || busy} onClick={() => void exportSessions()}>Xuất danh sách lượt xe CSV</button></div>
    </section>

    <section className="card card-polished">
      <div className="card-head"><div><span className="card-kicker">OCCUPANCY</span><h2>Tổng quan bãi xe</h2></div></div>
      {summary ? <><p>Làn hoạt động: {summary.lanes_active}/{summary.lanes_total} · Đang đỗ: {totalOccupied} · Sức chứa an toàn: {totalCapacity || 'Chưa cấu hình'} · Còn trống: {available ?? 'Chưa xác định'} · Tỷ lệ sử dụng: {occupancy === null ? 'Chưa xác định' : `${occupancy.toFixed(1)}%`}</p><div className="table-wrap"><table><thead><tr><th>Loại xe</th><th>Đang đỗ</th><th>Sức chứa an toàn</th><th>Còn chỗ</th><th>Trạng thái</th></tr></thead><tbody>{availability.map(item => { const cap = capacities?.[item.vehicle_type]; const remaining = cap && cap.safe_capacity > 0 ? Math.max(0, cap.safe_capacity - item.occupied) : null; const ratio = cap && cap.safe_capacity > 0 ? item.occupied / cap.safe_capacity * 100 : null; const status = ratio === null ? 'Chưa cấu hình' : ratio >= cap.full_threshold ? 'Đã đầy' : ratio >= cap.nearly_full_threshold ? 'Gần đầy' : 'Còn chỗ'; return <tr key={item.vehicle_type}><td>{item.vehicle_type}</td><td>{item.occupied}</td><td>{cap?.safe_capacity || 'Chưa cấu hình'}</td><td>{remaining ?? '—'}</td><td>{status}</td></tr> })}</tbody></table></div></> : <p>Chưa có dữ liệu.</p>}
    </section>

    {canConfigureCapacity && capacities && <section className="card card-polished stack">
      <div className="card-head"><div><span className="card-kicker">LOT SETTINGS</span><h2>Cấu hình sức chứa bãi xe</h2></div></div>
      <form className="stack" onSubmit={saveCapacity}>
        <div className="form-grid">{Object.entries(capacities).map(([vehicle, capacity]) => <fieldset key={vehicle} className="stack"><legend>{vehicle === 'CAR' ? 'Ô tô' : vehicle === 'MOTORBIKE' ? 'Xe máy' : 'Xe đạp'}</legend>
          <label className="field"><span>Sức chứa vật lý</span><input type="number" min="0" value={capacity.physical_capacity} onChange={e => setCapacities(old => old ? { ...old, [vehicle]: { ...old[vehicle], physical_capacity: Number(e.target.value), safe_capacity: Math.min(old[vehicle].safe_capacity, Number(e.target.value)) } } : old)} /></label>
          <label className="field"><span>Sức chứa an toàn</span><input type="number" min="0" max={capacity.physical_capacity} value={capacity.safe_capacity} onChange={e => setCapacities(old => old ? { ...old, [vehicle]: { ...old[vehicle], safe_capacity: Number(e.target.value) } } : old)} /></label>
        </fieldset>)}</div>
        <div><button className="btn btn-primary" disabled={busy}>Lưu cấu hình</button></div>
      </form>
    </section>}

    <section className="card card-polished stack">
      <div className="card-head"><div><span className="card-kicker">CASH RECONCILIATION</span><h2>Báo cáo doanh thu tiền mặt theo ca</h2></div></div>
      <p className="muted">Chọn thời gian bắt đầu và kết thúc ca. Số tiền chỉ cộng các khoản thanh toán tiền mặt đã xác nhận trong khoảng thời gian này.</p>
      <div className="form-grid"><label className="field"><span>Bắt đầu ca</span><input type="time" value={shiftStart} onChange={e => setShiftStart(e.target.value)} /></label><label className="field"><span>Kết thúc ca</span><input type="time" value={shiftEnd} onChange={e => setShiftEnd(e.target.value)} /></label></div>
      <div><button className="btn btn-primary" disabled={busy || !buildingId} onClick={() => void loadCashReport()}>Xem báo cáo ca</button></div>
      {cashReport && <div className="form-grid" role="status"><div><strong>Lượt xe vào</strong><p>{cashReport.entries}</p></div><div><strong>Lượt xe ra</strong><p>{cashReport.exits}</p></div><div><strong>Tiền mặt đã thu</strong><p>{cashReport.cash_revenue_vnd.toLocaleString('vi-VN')} ₫</p></div></div>}
    </section>

    <section className="card card-polished"><h2>Thống kê ngày</h2>
      <div className="table-wrap"><table><thead><tr><th>Ngày</th><th>Loại xe</th><th>Vào</th><th>Ra</th><th>Doanh thu (VND)</th><th>Đỉnh xe</th></tr></thead><tbody>{stats.map(s => <tr key={`${s.stat_date}-${s.vehicle_type}`}><td>{s.stat_date}</td><td>{s.vehicle_type}</td><td>{s.entries}</td><td>{s.exits}</td><td>{Number(s.revenue).toLocaleString('vi-VN')}</td><td>{s.occupancy_peak}</td></tr>)}</tbody></table></div>
      {!stats.length && <p>Chưa có thống kê trong khoảng đã chọn.</p>}
    </section>
    <section className="card card-polished"><h2>Cảnh báo thiết bị ({alerts.length})</h2>{alerts.length ? <ul>{alerts.map(d => <li key={d.code}>{d.name} ({d.code}): {d.status}</li>)}</ul> : <p>Không có thiết bị OFFLINE hoặc DEGRADED.</p>}<h3>Thiết bị ({devices.length})</h3><div className="table-wrap"><table><thead><tr><th>Mã</th><th>Tên</th><th>Loại</th><th>Trạng thái</th><th>Heartbeat cuối</th></tr></thead><tbody>{devices.map(d => <tr key={d.code}><td>{d.code}</td><td>{d.name}</td><td>{d.device_type}</td><td>{d.status}</td><td>{d.last_heartbeat_at ? new Date(d.last_heartbeat_at).toLocaleString('vi-VN') : 'Chưa có'}</td></tr>)}</tbody></table></div><p className="muted">Dữ liệu làm mới mỗi 15 giây. Cảnh báo hiển thị trạng thái hiện tại của thiết bị.</p></section>
  </main>
}
