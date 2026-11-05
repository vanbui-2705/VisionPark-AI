import { useEffect, useState } from 'react'
import { apiClient } from '../../api/client.ts'

type Building = { id: string; name: string }
type Summary = { building_id: string; lanes_total: number; lanes_active: number; parked: number; capacity: number | null; available: number | null; occupancy_status: string }
type Stat = { stat_date: string; vehicle_type: string; entries: number; exits: number; revenue: number | string; occupancy_peak: number }
type Device = { code: string; name: string; device_type: string; status: string; last_heartbeat_at: string | null }
const base = '/api/v1/m5'
export function M5Page() {
  const [buildings, setBuildings] = useState<Building[]>([])
  const [buildingId, setBuildingId] = useState('')
  const [start, setStart] = useState(new Date().toISOString().slice(0,10))
  const [end, setEnd] = useState(new Date().toISOString().slice(0,10))
  const [summary, setSummary] = useState<Summary | null>(null)
  const [stats, setStats] = useState<Stat[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [alerts, setAlerts] = useState<Device[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { apiClient.get<Building[]>('/api/v1/buildings').then(items => { setBuildings(items); if (items.length) setBuildingId(items[0].id) }).catch(e => setError(String(e))) }, [])
  useEffect(() => {
    if (!buildingId) return
    let active = true
    const load = async () => {
      try {
        const params = { building_id: buildingId }
        const [a,b,c,d] = await Promise.all([
          apiClient.get<Summary>(`${base}/dashboard`, { params }),
          apiClient.get<Stat[]>(`${base}/daily-stats`, { params: { ...params, start, end } }),
          apiClient.get<Device[]>(`${base}/devices`, { params }),
          apiClient.get<Device[]>(`${base}/devices/alerts`, { params }),
        ])
        if (active) { setSummary(a); setStats(b); setDevices(c); setAlerts(d); setError('') }
      } catch (e) { if (active) setError(String(e)) }
    }
    void load()
    const interval = window.setInterval(() => { void load() }, 15000)
    return () => { active = false; window.clearInterval(interval) }
  }, [buildingId, start, end])
  const download = async (format: 'csv' | 'pdf') => {
    setBusy(true)
    try {
      const blob = await apiClient.getBlob(`${base}/daily-stats.${format}`, { params: { building_id: buildingId, start, end }, timeoutMs: 30000 })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a'); link.href = url; link.download = `m5-report.${format}`; link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  return <main style={{ padding: 24, maxWidth: 1100 }}>
    <h1>M5 - Báo cáo và thiết bị</h1>
    {error && <p role="alert" style={{ color: 'crimson' }}>{error}</p>}
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
      <label>Tòa nhà <select value={buildingId} onChange={e => setBuildingId(e.target.value)}>{buildings.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
      <label>Từ ngày <input type="date" value={start} onChange={e => setStart(e.target.value)} /></label>
      <label>Đến ngày <input type="date" value={end} onChange={e => setEnd(e.target.value)} /></label>
      <button disabled={!buildingId || busy} onClick={() => void download('csv')}>Xuất CSV</button>
      <button disabled={!buildingId || busy} onClick={() => void download('pdf')}>Xuất PDF</button>
    </div>
    <h2>Tổng quan</h2>
    {summary ? <p>Làn hoạt động: {summary.lanes_active}/{summary.lanes_total} | Đang đỗ: {summary.parked} | Sức chứa: {summary.capacity ?? 'Chưa cấu hình'} | Còn trống: {summary.available ?? 'Chưa xác định'}</p> : <p>Chưa có dữ liệu</p>}
    <h2>Thống kê ngày</h2>
    <table><thead><tr><th>Ngày</th><th>Loại xe</th><th>Vào</th><th>Ra</th><th>Doanh thu (VND)</th></tr></thead><tbody>{stats.map(s => <tr key={`${s.stat_date}-${s.vehicle_type}`}><td>{s.stat_date}</td><td>{s.vehicle_type}</td><td>{s.entries}</td><td>{s.exits}</td><td>{s.revenue}</td></tr>)}</tbody></table>
    {!stats.length && <p>Chưa có thống kê trong khoảng đã chọn.</p>}
    <h2>Cảnh báo thiết bị ({alerts.length})</h2>
    {alerts.length ? <ul>{alerts.map(d => <li key={d.code}>{d.name} ({d.code}): {d.status}</li>)}</ul> : <p>Không có thiết bị OFFLINE hoặc DEGRADED.</p>}
    <h2>Thiết bị ({devices.length})</h2>
    <table><thead><tr><th>Mã</th><th>Tên</th><th>Loại</th><th>Trạng thái</th><th>Heartbeat cuối</th></tr></thead><tbody>{devices.map(d => <tr key={d.code}><td>{d.code}</td><td>{d.name}</td><td>{d.device_type}</td><td>{d.status}</td><td>{d.last_heartbeat_at ?? 'Chưa có'}</td></tr>)}</tbody></table>
    <p>Dữ liệu làm mới mỗi 15 giây. Cảnh báo là trạng thái khi truy vấn, chưa có gửi thông báo chủ động.</p>
  </main>
}
