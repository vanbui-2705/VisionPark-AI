import { useRef, useState } from 'react'
import { completeExit, prepareExit, type CheckOutResult, type ExitSession } from '../api'

type Props = { session: ExitSession; onBusyChange: (busy: boolean) => void; onCompleted: () => void; onNext: () => void }

export default function ExitSummary({ session, onBusyChange, onCompleted, onNext }: Props) {
  const [preview, setPreview] = useState(session)
  const [outcome, setOutcome] = useState<CheckOutResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [needsRefresh, setNeedsRefresh] = useState(false)
  const [error, setError] = useState('')
  const submitting = useRef(false)
  const needsCash = preview.fee > 0 && preview.status !== 'PAID'
  const completed = Boolean(outcome)
  const minutes = outcome ? Math.max(0, Math.floor((Date.parse(outcome.transaction.exit_time) - Date.parse(preview.check_in_time)) / 60000)) : preview.duration_minutes
  const days = Math.floor(minutes / 1440)
  const duration = `${days ? `${days} ngày ` : ''}${Math.floor(minutes % 1440 / 60)} giờ ${minutes % 60} phút`
  const exitTime = outcome?.transaction.exit_time ?? preview.exit_time
  const act = async (refresh = false) => {
    if (submitting.current || completed || (!refresh && needsRefresh)) return
    submitting.current = true
    setBusy(true); onBusyChange(true); setError('')
    try {
      if (refresh) {
        setPreview(await prepareExit(preview.laneId, preview.license_plate ?? '', preview.exit_image_url ?? undefined, preview.session_id))
        setNeedsRefresh(false)
        return
      }
      const response = await completeExit(preview, needsCash)
      if (!['COMPLETED', 'EXITED'].includes(response.status) || !response.barrier_opened || response.transaction.id !== preview.session_id || response.transaction.exit_lane_id !== preview.laneId || response.fee !== preview.fee) {
        throw new Error('Backend chưa xác nhận đúng phiên xe ra, số tiền và trạng thái mở cổng.')
      }
      setOutcome(response); onCompleted()
    } catch (value) {
      const code = value && typeof value === 'object' && 'code' in value ? value.code : undefined
      if (code === 'FEE_CHANGED') setNeedsRefresh(true)
      setError(value instanceof Error ? value.message : 'Thao tác thất bại. Vui lòng thử lại cùng phiên xe.')
    } finally {
      submitting.current = false
      setBusy(false); onBusyChange(false)
    }
  }
  return <section className="card scan-result" aria-label="Thông tin xe ra">
    <div className="scan-card-head"><div><span className="card-kicker">LÀN RA OUT</span><h3>Thông tin thanh toán</h3></div></div>
    <dl className="station-exit-details">
      <div><dt>Biển số</dt><dd>{preview.license_plate ?? preview.ticket_code}</dd></div>
      <div><dt>Thời điểm vào</dt><dd><time dateTime={preview.check_in_time}>{new Date(preview.check_in_time).toLocaleString('vi-VN')}</time></dd></div>
      <div><dt>{completed ? 'Thời điểm ra' : 'Thời điểm ra dự kiến'}</dt><dd><time dateTime={exitTime}>{new Date(exitTime).toLocaleString('vi-VN')}</time></dd></div>
      <div><dt>Tổng thời gian gửi</dt><dd>{duration}</dd></div>
      <div><dt>{completed ? 'Số tiền đã xác nhận' : 'Số tiền phải thu'}</dt><dd className="station-exit-amount">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(outcome?.fee ?? preview.fee)}</dd></div>
      <div><dt>Mã phiên</dt><dd>{preview.session_id}</dd></div>
    </dl>
    {!completed && <p>{needsCash ? 'Đối chiếu ảnh và xác nhận đã nhận đủ tiền trước khi mở cổng.' : 'Xe miễn phí hoặc đã thanh toán. Đối chiếu ảnh trước khi mở cổng.'}</p>}
    {preview.message && <p role="status">{preview.message}</p>}
    <div className="scan-result-actions">
      {needsCash ? <button type="button" className="btn btn-primary" data-station-shortcut="cash" aria-keyshortcuts="F8" disabled={busy || completed || needsRefresh || preview.vehicle_type_mismatch} onClick={() => void act()}>Xác nhận thu tiền và mở cổng (F8)</button>
        : <button type="button" className="btn btn-primary" data-station-shortcut="gate" aria-keyshortcuts="F10" disabled={busy || completed || needsRefresh || preview.vehicle_type_mismatch} onClick={() => void act()}>Mở cổng (F10)</button>}
      {needsRefresh && <button type="button" className="btn" disabled={busy} onClick={() => void act(true)}>Cập nhật phí</button>}
      {completed && <button type="button" className="btn" data-station-shortcut="next" aria-keyshortcuts="F9" onClick={onNext}>Xe tiếp theo (F9)</button>}
    </div>
    {busy && <p role="status">Đang xử lý…</p>}
    {completed && <p role="status" className="alert alert-success">Backend đã xác nhận checkout và ghi nhận mở barrier mô phỏng.</p>}
    <p className="muted">Barrier hiện được mô phỏng ở backend; chưa điều khiển thiết bị vật lý.</p>
    {error && <p role="alert" className="alert alert-danger">{error}</p>}
  </section>
}
