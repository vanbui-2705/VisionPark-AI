import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { lanesApi } from '../../api/lanesApi.ts'
import { detectionsApi } from '../../api/services.ts'
import type { Detection } from '../../api/domain.ts'
import { Alert } from '../../components/ui/Alert.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Dialog } from '../../components/ui/Dialog.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Spinner } from '../../components/ui/Spinner.tsx'
import { useToast } from '../../components/ui/Toast.tsx'
import { pushNotification } from '../../lib/notifications.ts'

// Shell — Person 4 vẫn sở hữu player/canvas/throttle/bbox/confirm integration.
// Ponytail: 12 states map to UI only, không duplicate detection logic.

type ScanState =
  | 'NO_VIDEO'
  | 'READY'
  | 'PLAYING'
  | 'PROCESSING'
  | 'DETECTED'
  | 'LOW_CONFIDENCE'
  | 'NO_PLATE'
  | 'WAITING_CONFIRMATION'
  | 'CONFIRMED'
  | 'CORRECTED'
  | 'ERROR'
  | 'OFFLINE'

const STATES: ScanState[] = ['NO_VIDEO','READY','PLAYING','PROCESSING','DETECTED','LOW_CONFIDENCE','NO_PLATE','WAITING_CONFIRMATION','CONFIRMED','CORRECTED','ERROR','OFFLINE']

function isMockProvider(p?: string): boolean { const v = (p ?? '').toLowerCase(); return v.includes('mock') || v === 'mock-alpr' }

export function ScanPage() {
  const [search] = useSearchParams()
  const toast = useToast()
  const initial = (search.get('demoState') as ScanState) ?? 'READY'
  const [state, setState] = useState<ScanState>(STATES.includes(initial) ? initial : 'READY')
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const [lanes, setLanes] = useState<{ id: string; name: string }[]>([])
  const [laneId, setLaneId] = useState('')
  const [plate, setPlate] = useState('29A-123.45')
  const [confidence] = useState(0.91)
  const [editOpen, setEditOpen] = useState(false)
  const [finalPlate, setFinalPlate] = useState('29A12345')
  const [recent, setRecent] = useState<Detection[]>([])
  const [videoName, setVideoName] = useState<string | null>(null)
  const videoRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    healthApi.ready().then((h) => setProvider((h as { alpr?: { provider?: string } })?.alpr?.provider)).catch(() => {})
    lanesApi.getLanes().then((ls) => { setLanes(ls.map((l) => ({ id: l.id, name: l.name }))); if (ls[0]) setLaneId(ls[0].id) }).catch(() => {})
    detectionsApi.list({ limit: 5 }).then(setRecent).catch(() => setRecent([]))
  }, [])

  const confirm = async (final: string) => {
    try {
      await detectionsApi.confirm('d-1', { final_plate: final })
      pushNotification({ title: 'Đã xác nhận biển số', message: final, to: '/detections' })
      toast.push('Đã xác nhận ' + final, 'success')
    } catch {
      // backend pending / mock — vẫn chuyển UI state nhưng không fake thành công API
      toast.push('UI confirmed (API pending)', 'warning')
      pushNotification({ title: 'Xác nhận (API pending)', message: final, to: '/detections' })
    }
    setState('CONFIRMED')
  }

  const mock = useMemo(() => isMockProvider(provider), [provider])

  return (
    <div className="scan-page">
      {mock ? (
        <div className="banner-mock" role="status" title="Hệ thống hiện sử dụng dữ liệu nhận diện mô phỏng. Không phải kết quả từ model AI thực tế.">
          <strong>⚠ MOCK ALPR</strong> — Hệ thống hiện sử dụng dữ liệu nhận diện mô phỏng. Không phải kết quả từ model AI thực tế.
        </div>
      ) : null}
      <div className="page-head">
        <h2>Trạm quét biển số</h2>
        <p className="muted">Hướng xe {laneId ? lanes.find((l) => l.id === laneId)?.name ?? laneId : '—'}</p>
      </div>
      <div className="scan-toolbar">
        <label>
          Trạng thái demo{' '}
          <select value={state} onChange={(e) => setState(e.target.value as ScanState)}>
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label>
          Lane{' '}
          <select value={laneId} onChange={(e) => setLaneId(e.target.value)}>
            {lanes.length === 0 ? <option value="">(chưa có làn)</option> : lanes.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </label>
        <input ref={videoRef} type="file" accept="video/mp4" style={{ display: 'none' }} aria-label="Chọn video MP4" onChange={(e) => setVideoName(e.target.files?.[0]?.name ?? null)} />
        <Button type="button" onClick={() => videoRef.current?.click()}>Chọn video (MP4)</Button>
        <Link to="/station/scan/fullscreen" className="btn btn-primary">⛶ Toàn màn hình</Link>
      </div>

      <div className="scan-grid">
        <section className="scan-video card">
          <div className="video-placeholder">
            <div className="bbox">BBOX</div>
            <span>VIDEO / CAMERA VIEW</span>
            {state === 'PROCESSING' ? <Spinner label="Đang nhận diện biển số..." /> : null}
          </div>
          <div className="scan-controls">
            <Button type="button">▶ Play</Button>
            <Button type="button">⏸ Pause</Button>
            <Button type="button">⟳ Replay</Button>
          </div>
          <p className="muted">{videoName ? `Đã chọn: ${videoName}` : 'Video: parking_test.mp4 — ghép player của Người 4 tại đây (canvas + throttle + bbox).'}</p>
        </section>

        <section className="scan-result card">
          <h3>Kết quả nhận diện</h3>
          {state === 'OFFLINE' ? <Alert variant="error">Mất kết nối ALPR.</Alert> : null}
          {state === 'ERROR' ? <Alert variant="error">Lỗi xử lý — thử lại.</Alert> : null}
          {state === 'NO_VIDEO' ? <Alert variant="info">Chưa có video.</Alert> : null}
          {state === 'NO_PLATE' ? (
            <div>
              <Alert variant="warning">Không phát hiện biển số.</Alert>
              <div style={{ display: 'flex', gap: 8 }}><Button onClick={() => setEditOpen(true)}>Nhập biển số thủ công</Button><Button variant="secondary" onClick={() => setState('READY')}>Quét lại</Button></div>
            </div>
          ) : null}
          {state === 'LOW_CONFIDENCE' ? <Alert variant="warning">Độ tin cậy thấp: {Math.round(confidence * 100)}% — vui lòng kiểm tra trước khi xác nhận.</Alert> : null}
          {state === 'PROCESSING' ? <p>Đang nhận diện biển số...</p> : null}
          {['DETECTED','LOW_CONFIDENCE','WAITING_CONFIRMATION','CONFIRMED','CORRECTED','READY','PLAYING'].includes(state) ? (
            <div className="result-fields">
              <div><span className="muted">Biển số</span><div className="plate">{plate}</div></div>
              <div><span className="muted">Confidence</span><div>{Math.round(confidence * 100)}%</div></div>
              <div><span className="muted">Model</span><div>{provider ?? '—'}</div></div>
              <div><span className="muted">Latency</span><div>25 ms</div></div>
              {state === 'WAITING_CONFIRMATION' || state === 'LOW_CONFIDENCE' || state === 'DETECTED' ? (
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <Button onClick={() => confirm(finalPlate)}>✓ Biển số đúng</Button>
                  <Button variant="secondary" onClick={() => setEditOpen(true)}>✎ Sửa biển số</Button>
                </div>
              ) : null}
              {state === 'CONFIRMED' ? <Alert variant="success">Đã xác nhận.</Alert> : null}
              {state === 'CORRECTED' ? <Alert variant="success">Đã sửa: {finalPlate}</Alert> : null}
            </div>
          ) : null}
        </section>
      </div>

      <section className="card" style={{ marginTop: 16 }}>
        <h3>Nhận diện gần đây</h3>
        <table className="table">
          <thead><tr><th>Time</th><th>Lane</th><th>Plate</th><th>Confidence</th><th>Status</th></tr></thead>
          <tbody>
            {recent.length === 0 ? (
              <tr><td colSpan={5} className="muted">Chưa có dữ liệu detection (API pending).</td></tr>
            ) : recent.map((d) => (
              <tr key={d.id}>
                <td>{new Date(d.created_at).toLocaleTimeString('vi-VN')}</td>
                <td>{d.lane_name ?? d.lane_id}</td>
                <td>{d.final_plate ?? d.normalized_plate ?? d.ai_plate ?? '—'}</td>
                <td>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</td>
                <td>{d.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">Nguồn: GET /api/v1/detections?limit=5 — shell chỉ render table.</p>
      </section>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} title="Sửa kết quả nhận diện">
        <p className="muted">AI nhận diện: {plate} (confidence {Math.round(confidence * 100)}%)</p>
        <Input label="Biển số chính xác" value={finalPlate} onChange={(e) => setFinalPlate(e.target.value)} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
          <Button type="button" variant="secondary" onClick={() => setEditOpen(false)}>Hủy</Button>
          <Button type="button" onClick={() => { setPlate(finalPlate); setState('CORRECTED'); setEditOpen(false) }}>Xác nhận</Button>
        </div>
      </Dialog>
    </div>
  )
}
