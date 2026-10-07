import { t as translate } from "../lib/i18n"
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../api/client'
import { mapDetection } from '../api/services'
import type { DetectionResponse } from '../api/services'
import type { Detection, ParkingTransaction } from '../api/domain'
import { lanesApi } from '../api/lanesApi'
import type { Lane } from '../api/types'
import { Alert } from './ui/Alert'

type Page<T> = { items: T[]; total: number }
export function HistoryBrowser({ kind }: { kind: 'detections' | 'parking' }) {
  const [rows, setRows] = useState<(Detection | ParkingTransaction)[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [lane, setLane] = useState('')
  const [direction, setDirection] = useState('')
  const [inputKind, setInputKind] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [min, setMin] = useState('')
  const [max, setMax] = useState('')
  const [lanes, setLanes] = useState<Lane[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [refresh, setRefresh] = useState(0)
  useEffect(() => { lanesApi.getActiveLanes().then(setLanes).catch(() => undefined) }, [])
  useEffect(() => {
    let alive = true
    const timer = setTimeout(() => {
      setLoading(true); setError('')
      const params = { paginated: true, limit: 20, page, skip: page * 20, q, status, lane_id: lane,
        direction: kind === 'detections' ? direction : undefined, input_kind: kind === 'detections' ? inputKind : undefined,
        from: from ? new Date(`${from}T00:00:00`).toISOString() : undefined,
        to: to ? new Date(`${to}T23:59:59.999`).toISOString() : undefined,
        min_confidence: min ? Number(min) / 100 : undefined, max_confidence: max ? Number(max) / 100 : undefined }
      const url = kind === 'detections' ? '/api/v1/alpr/detections' : '/api/v1/parking/transactions'
      apiClient.get<Page<DetectionResponse | ParkingTransaction>>(url, { params }).then(data => {
        if (!alive) return
        setRows(kind === 'detections' ? data.items.map(row => mapDetection(row as DetectionResponse)) : data.items as ParkingTransaction[])
        setTotal(data.total)
      }).catch(e => { if (alive) setError(e instanceof Error ? e.message : translate("Không tải được lịch sử.")) })
        .finally(() => { if (alive) setLoading(false) })
    }, 200)
    return () => { alive = false; clearTimeout(timer) }
  }, [kind, page, q, status, lane, direction, inputKind, from, to, min, max, refresh])
  const statuses = kind === 'detections' ? ['DETECTED', 'NEEDS_CONFIRMATION', 'CONFIRMED', 'CORRECTED', 'NO_PLATE'] : ['PARKED', 'COMPLETED', 'CANCELLED']
  const filter = (setter: (value: string) => void) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => { setter(e.target.value); setPage(0) }
  return <section>
    <h2>{kind === 'detections' ? translate("Lịch sử nhận diện") : translate("Lịch sử đỗ xe")}</h2>
    <p>{total}{translate("kết quả từ database")}</p>
    <div className="card" style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
      <label>{translate("Biển số")}<input value={q} onChange={filter(setQ)} /></label>
      <label>{translate("Làn")}<select value={lane} onChange={filter(setLane)}><option value="">{translate("Tất cả")}</option>{lanes.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
      <label>{translate("Trạng thái")}<select value={status} onChange={filter(setStatus)}><option value="">{translate("Tất cả")}</option>{statuses.map(s => <option key={s}>{s}</option>)}</select></label>
      <label>{translate("Từ ngày")}<input type="date" value={from} onChange={filter(setFrom)} /></label>
      <label>{translate("Đến ngày")}<input type="date" value={to} onChange={filter(setTo)} /></label>
      {kind === 'detections' && <>
        <label>{translate("Hướng")}<select value={direction} onChange={filter(setDirection)}><option value="">{translate("Tất cả")}</option><option>IN</option><option>OUT</option></select></label>
        <label>{translate("Đầu vào")}<select value={inputKind} onChange={filter(setInputKind)}><option value="">{translate("Tất cả")}</option><option value="IMAGE_UPLOAD">{translate("Ảnh")}</option><option value="VIDEO_FRAME">Video</option></select></label>
        <label>Confidence min % <input type="number" min="0" max="100" value={min} onChange={filter(setMin)} /></label>
        <label>Confidence max % <input type="number" min="0" max="100" value={max} onChange={filter(setMax)} /></label>
      </>}
      <button type="button" className="btn" onClick={() => setRefresh(v => v + 1)}>{translate("Làm mới")}</button>
    </div>
    {error && <Alert variant="error">{error}</Alert>}
    {loading && <p role="status">{translate("Đang tải…")}</p>}
    <table className="table"><thead><tr><th>{translate("Biển số")}</th><th>{translate("Làn")}</th><th>{translate("Trạng thái")}</th><th>{translate("Nguồn / đầu vào")}</th><th>{translate("Thời gian")}</th><th /></tr></thead><tbody>
      {rows.map(row => {
        const detection = row as Detection
        const parking = row as ParkingTransaction
        return <tr key={row.id}><td>{kind === 'detections' ? detection.final_plate ?? detection.normalized_plate ?? translate("Không đọc được") : parking.license_plate}</td>
          <td>{row.lane_name ?? row.lane_id}</td><td>{row.status}</td><td>{kind === 'detections' ? detection.input_kind ?? 'Unknown' : parking.source}</td>
          <td>{new Date(kind === 'detections' ? detection.created_at : parking.check_in_time).toLocaleString()}</td>
          <td><Link to={kind === 'detections' ? `/detections/${row.id}` : `/parking/${row.id}`}>{translate("Chi tiết")}</Link></td></tr>
      })}
    </tbody></table>
    {!loading && !rows.length && <p>{translate("Không có kết quả phù hợp.")}</p>}
    <div style={{ display: 'flex', gap: 12 }}><button disabled={page === 0 || loading} onClick={() => setPage(p => p - 1)}>{translate("Trước")}</button><span>Trang {page + 1} / {Math.max(1, Math.ceil(total / 20))}</span><button disabled={(page + 1) * 20 >= total || loading} onClick={() => setPage(p => p + 1)}>Sau</button></div>
  </section>
}
