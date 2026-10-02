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

const SCAN_STATE_LABEL: Record<ScanState, string> = {
  NO_VIDEO: 'Chưa có video',
  READY: 'Sẵn sàng',
  PLAYING: 'Đang phát',
  PROCESSING: 'Đang xử lý',
  DETECTED: 'Đã nhận diện',
  LOW_CONFIDENCE: 'Độ tin cậy thấp',
  NO_PLATE: 'Không có biển số',
  WAITING_CONFIRMATION: 'Chờ xác nhận',
  CONFIRMED: 'Đã xác nhận',
  CORRECTED: 'Đã sửa',
  ERROR: 'Lỗi xử lý',
  OFFLINE: 'Ngoại tuyến',
}

const DETECTION_STATUS_LABEL: Record<string, string> = {
  DETECTED: 'Đã nhận diện',
  NEEDS_CONFIRMATION: 'Cần xác nhận',
  CONFIRMED: 'Đã xác nhận',
  CORRECTED: 'Đã sửa',
  NO_PLATE: 'Không có biển số',
  ERROR: 'Lỗi',
}

const DETECTION_STATUS_TONE: Record<string, string> = {
  DETECTED: 'info',
  NEEDS_CONFIRMATION: 'warning',
  CONFIRMED: 'success',
  CORRECTED: 'success',
  NO_PLATE: 'neutral',
  ERROR: 'danger',
}

function detectionStatusLabel(status: string): string {
  return DETECTION_STATUS_LABEL[status] ?? status
}

function detectionStatusTone(status: string): string {
  return DETECTION_STATUS_TONE[status] ?? 'neutral'
}

function isMockProvider(p?: string): boolean { const v = (p ?? '').toLowerCase(); return v.includes('mock') || v === 'mock-alpr' }

export function ScanPage() {
  const [search] = useSearchParams()
  const toast = useToast()
  const initial = (search.get('demoState') as ScanState) ?? 'READY'
  const [state, setState] = useState<ScanState>(STATES.includes(initial) ? initial : 'READY')
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const [lanes, setLanes] = useState<{ id: string; name: string }[]>([])
  const [laneId, setLaneId] = useState('')
  const [editOpen, setEditOpen] = useState(false)
  const [finalPlate, setFinalPlate] = useState('')
  const [recent, setRecent] = useState<Detection[]>([])
  const [recentLoading, setRecentLoading] = useState(true)
  const [videoName, setVideoName] = useState<string | null>(null)
  const videoRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    healthApi.ready().then((h) => setProvider((h as { alpr?: { provider?: string } })?.alpr?.provider)).catch(() => {})
    lanesApi.getLanes().then((ls) => { setLanes(ls.map((l) => ({ id: l.id, name: l.name }))); if (ls[0]) setLaneId(ls[0].id) }).catch(() => {})
    detectionsApi.list({ limit: 5 }).then(setRecent).catch(() => setRecent([])).finally(() => setRecentLoading(false))
  }, [])

  const confirm = async (detectionId: string, final: string) => {
    try {
      const updated = await detectionsApi.confirm(detectionId, { final_plate: final })
      setRecent((items) => items.map((item) => item.id === detectionId ? { ...item, ...updated, id: item.id } : item))
      pushNotification({ title: 'Đã xác nhận biển số', message: final, to: '/detections' })
      toast.push('Đã xác nhận ' + final, 'success')
      setState('CONFIRMED')
    } catch {
      // Keep the UI pending when the API has not confirmed the update.
      toast.push('UI confirmed (API pending)', 'warning')
      pushNotification({ title: 'Xác nhận (API pending)', message: final, to: '/detections' })
    }
  }

  const mock = useMemo(() => isMockProvider(provider), [provider])
  const currentDetection = recent[0] ?? null
  const currentPlate = currentDetection?.final_plate ?? currentDetection?.normalized_plate ?? currentDetection?.ai_plate ?? ''
  const displayPlate = state === 'CORRECTED' && finalPlate.trim() ? finalPlate.trim() : currentPlate
  const confidencePercent = currentDetection?.confidence != null ? Math.round(currentDetection.confidence * 100) : null
  const hasResultState = ['DETECTED', 'LOW_CONFIDENCE', 'WAITING_CONFIRMATION', 'CONFIRMED', 'CORRECTED', 'READY', 'PLAYING'].includes(state)
  const hasManualCorrection = state === 'CORRECTED' && Boolean(finalPlate.trim())

  return (
    <div className="scan-page">
      {mock ? (
        <div className="banner-mock" role="status" title="Hệ thống hiện sử dụng dữ liệu nhận diện mô phỏng. Không phải kết quả từ model AI thực tế.">
          <strong>⚠ MOCK ALPR</strong> — Hệ thống hiện sử dụng dữ liệu nhận diện mô phỏng. Không phải kết quả từ model AI thực tế.
        </div>
      ) : null}
      <section className="scan-hero">
        <div className="scan-hero-copy">
          <div className="scan-kicker">Trạm kiểm soát · VisionPark</div>
          <h2>Trạm quét biển số</h2>
          <p>Giám sát camera làn xe {laneId ? lanes.find((l) => l.id === laneId)?.name ?? laneId : '—'} · Hỗ trợ nhận dạng AI tự động</p>
        </div>
        <div className="scan-hero-actions">
          <Link to="/station/scan/fullscreen" className="btn btn-secondary">⛶ Toàn màn hình</Link>
        </div>
      </section>

      <section className="scan-toolbar" aria-label="Điều khiển trạm quét">
        <div className="scan-control-group">
          <label htmlFor="scan-demo-state">Trạng thái demo</label>
          <span className="scan-select-wrap">
            <select id="scan-demo-state" className="scan-select" value={state} onChange={(e) => setState(e.target.value as ScanState)}>
              {STATES.map((s) => <option key={s} value={s}>{SCAN_STATE_LABEL[s]}</option>)}
            </select>
          </span>
        </div>
        <div className="scan-control-group">
          <label htmlFor="scan-lane">Làn xe</label>
          <span className="scan-select-wrap">
            <select id="scan-lane" className="scan-select" value={laneId} onChange={(e) => setLaneId(e.target.value)}>
              {lanes.length === 0 ? <option value="">(chưa có làn)</option> : lanes.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </span>
        </div>
        <input ref={videoRef} type="file" accept="video/mp4" style={{ display: 'none' }} aria-label="Chọn video MP4" onChange={(e) => setVideoName(e.target.files?.[0]?.name ?? null)} />
        <div className="scan-toolbar-actions">
          <Button type="button" variant="secondary" className="scan-upload-button" onClick={() => videoRef.current?.click()}>Chọn video (MP4)</Button>
          {videoName ? <span className="scan-file-name" title={videoName}>{videoName}</span> : <span className="scan-file-name scan-file-name--empty">Chưa chọn tệp</span>}
        </div>
      </section>

      <div className="scan-grid">
        <section className="scan-video card">
          <div className="scan-card-head">
            <div>
              <span className="card-kicker">VIDEO INPUT</span>
              <h3>Camera làn xe</h3>
              <p className="muted">Khung hình phân tích nhận diện biển số</p>
            </div>
            <span className="scan-state">{SCAN_STATE_LABEL[state]}</span>
          </div>
          <div className="video-placeholder">
            <div className="bbox"><span>KHUNG NHẬN DIỆN</span></div>
            <span className="video-placeholder-caption">CAMERA TRỰC TIẾP / VIDEO PHÂN TÍCH</span>
            {state === 'PROCESSING' ? <Spinner label="Đang nhận diện biển số..." /> : null}
          </div>
          <div className="scan-controls">
            <Button type="button">▶ Phát</Button>
            <Button type="button" variant="secondary">⏸ Tạm dừng</Button>
            <Button type="button" variant="secondary">⟳ Phát lại</Button>
          </div>
          <p className="muted">{videoName ? `Đã chọn: ${videoName}` : 'Hỗ trợ phát video mẫu MP4 hoặc nguồn luồng camera RTSP trực tiếp.'}</p>
        </section>

        <section className="scan-result card">
          <div className="scan-card-head">
            <div>
              <span className="card-kicker">AI / ALPR</span>
              <h3>Kết quả nhận diện</h3>
              <p className="muted">Dữ liệu mới nhất từ detection API</p>
            </div>
            <span className="scan-state">{SCAN_STATE_LABEL[state]}</span>
          </div>
          {state === 'OFFLINE' ? <Alert variant="error">Mất kết nối ALPR.</Alert> : null}
          {state === 'ERROR' ? <Alert variant="error">Lỗi xử lý — vui lòng thử lại.</Alert> : null}
          {state === 'NO_VIDEO' ? <Alert variant="info">Chưa có tín hiệu video.</Alert> : null}
          {state === 'NO_PLATE' ? (
            <div className="scan-result-message">
              <Alert variant="warning">Không phát hiện thấy biển số xe.</Alert>
              <div className="scan-result-actions"><Button onClick={() => { setFinalPlate(''); setEditOpen(true) }}>Nhập biển số thủ công</Button><Button variant="secondary" onClick={() => setState('READY')}>Quét lại</Button></div>
            </div>
          ) : null}
          {state === 'LOW_CONFIDENCE' ? <Alert variant="warning">Độ tin cậy thấp{confidencePercent != null ? `: ${confidencePercent}%` : ''} — vui lòng kiểm tra trước khi xác nhận.</Alert> : null}
          {state === 'PROCESSING' ? <p>Đang nhận diện biển số...</p> : null}
          {hasResultState && currentDetection ? (
            <div className="result-fields">
              <div className="result-metric result-metric--plate"><span className="muted">Biển số</span><div className="plate">{displayPlate || '—'}</div></div>
              <div className="result-metric"><span className="muted">Độ tin cậy</span><div>{confidencePercent != null ? `${confidencePercent}%` : '—'}</div></div>
              <div className="result-metric"><span className="muted">Mô hình AI</span><div>{currentDetection.model_version ?? provider ?? '—'}</div></div>
              <div className="result-metric"><span className="muted">Độ trễ xử lý</span><div>{currentDetection.processing_ms != null ? `${currentDetection.processing_ms} ms` : '—'}</div></div>
              {state === 'WAITING_CONFIRMATION' || state === 'LOW_CONFIDENCE' || state === 'DETECTED' ? (
                <div className="scan-result-actions">
                  <Button onClick={() => confirm(currentDetection.id, finalPlate || currentPlate)} disabled={!currentDetection.id || !(finalPlate || currentPlate).trim()}>✓ Biển số đúng</Button>
                  <Button variant="secondary" onClick={() => { setFinalPlate(currentPlate); setEditOpen(true) }}>✎ Sửa biển số</Button>
                </div>
              ) : null}
              {currentDetection.status === 'CONFIRMED' ? <Alert variant="success">Đã xác nhận thành công.</Alert> : null}
              {state === 'CORRECTED' ? <Alert variant="success">Đã sửa: {finalPlate || currentPlate}</Alert> : null}
            </div>
          ) : hasManualCorrection ? (
            <div className="result-fields">
              <div className="result-metric result-metric--plate"><span className="muted">Biển số nhập thủ công</span><div className="plate">{finalPlate.trim()}</div></div>
              <p className="muted scan-manual-note">Chưa có detection tương ứng từ API.</p>
            </div>
          ) : hasResultState ? (
            <div className="scan-result-empty"><strong>{recentLoading ? 'Đang tải kết quả' : 'Chưa có kết quả'}</strong><span>{recentLoading ? 'Đang chờ detection API phản hồi.' : 'Chưa nhận được detection từ API.'}</span></div>
          ) : null}
        </section>
      </div>

      <section className="scan-history card">
        <div className="scan-card-head">
          <div>
            <span className="card-kicker">ACTIVITY LOG</span>
            <h3>Nhận diện gần đây</h3>
            <p className="muted">Lịch sử detection mới nhất từ API</p>
          </div>
          <span className="scan-count">{recentLoading ? 'Đang tải' : `${recent.length} bản ghi`}</span>
        </div>
        <div className="table-wrap scan-history-table">
          <table className="table">
            <thead><tr><th>Thời gian</th><th>Làn xe</th><th>Biển số</th><th>Độ tin cậy</th><th>Trạng thái</th></tr></thead>
            <tbody>
              {recent.length === 0 ? (
                <tr><td colSpan={5} className="muted scan-table-empty">{recentLoading ? 'Đang tải dữ liệu detection…' : 'Chưa có dữ liệu detection từ API.'}</td></tr>
              ) : recent.map((d) => (
                <tr key={d.id}>
                  <td>{new Date(d.created_at).toLocaleTimeString('vi-VN')}</td>
                  <td>{d.lane_name ?? d.lane_id}</td>
                  <td><span className="scan-plate-cell">{d.final_plate ?? d.normalized_plate ?? d.ai_plate ?? '—'}</span></td>
                  <td>{d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}</td>
                  <td><span className={`scan-status scan-status--${detectionStatusTone(d.status)}`}><span className="scan-status-dot" />{detectionStatusLabel(d.status)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted scan-source-note">Nguồn: GET /api/v1/alpr/detections?limit=5</p>
      </section>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} title="Sửa kết quả nhận diện">
        <p className="muted">AI nhận diện: {currentPlate || '—'}{confidencePercent != null ? ` (confidence ${confidencePercent}%)` : ''}</p>
        <Input label="Biển số chính xác" value={finalPlate} onChange={(e) => setFinalPlate(e.target.value)} />
        <div className="scan-dialog-actions">
          <Button type="button" variant="secondary" onClick={() => setEditOpen(false)}>Hủy</Button>
          <Button type="button" onClick={() => { setState('CORRECTED'); setEditOpen(false) }} disabled={!finalPlate.trim()}>Xác nhận</Button>
        </div>
      </Dialog>
    </div>
  )
}
