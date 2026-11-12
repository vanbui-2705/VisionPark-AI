import { useRef, useState } from 'react'
import { completeExit, prepareExit, type CheckOutResult, type ExitSession } from '../api'
import CheckoutConfirmationDialog from './CheckoutConfirmationDialog'

type Props = {
  session: ExitSession
  onBusyChange: (busy: boolean) => void
  onCompleted: () => void
  onNext: () => void
  onRequireExitImage: () => void
}

const currency = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' })

export default function ExitSummary({ session, onBusyChange, onCompleted, onNext, onRequireExitImage }: Props) {
  const [preview, setPreview] = useState(session)
  const [outcome, setOutcome] = useState<CheckOutResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [needsRefresh, setNeedsRefresh] = useState(false)
  const [error, setError] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const submitting = useRef(false)
  const needsCash = preview.fee > 0 && preview.status !== 'PAID'
  const completed = Boolean(outcome)
  const missingExitImage = !preview.exit_image_url
  const actionBlocked = busy || completed || needsRefresh || preview.vehicle_type_mismatch || missingExitImage
  const minutes = outcome ? Math.max(0, Math.floor((Date.parse(outcome.transaction.exit_time) - Date.parse(preview.check_in_time)) / 60000)) : preview.duration_minutes
  const days = Math.floor(minutes / 1440)
  const duration = `${days ? `${days} ngày ` : ''}${Math.floor(minutes % 1440 / 60)} giờ ${minutes % 60} phút`
  const exitTime = outcome?.transaction.exit_time ?? preview.exit_time
  const feeLabel = currency.format(outcome?.fee ?? preview.fee)
  const plate = preview.license_plate ?? preview.ticket_code ?? 'Không xác định'
  const shortSessionId = preview.session_id.length > 14
    ? `${preview.session_id.slice(0, 8)}…${preview.session_id.slice(-4)}`
    : preview.session_id

  const act = async (refresh = false) => {
    if (submitting.current || completed || (!refresh && (needsRefresh || missingExitImage || preview.vehicle_type_mismatch))) return
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
      setOutcome(response)
      setConfirmOpen(false)
      onCompleted()
    } catch (value) {
      const code = value && typeof value === 'object' && 'code' in value ? String(value.code) : undefined
      if (code === 'FEE_CHANGED') {
        setNeedsRefresh(true)
        setConfirmOpen(false)
      }
      const message = value && typeof value === 'object' && 'message' in value
        ? String(value.message)
        : 'Thao tác thất bại. Vui lòng thử lại cùng phiên xe.'
      setError(message)
    } finally {
      submitting.current = false
      setBusy(false); onBusyChange(false)
    }
  }

  const copySessionId = async () => {
    try {
      await navigator.clipboard.writeText(preview.session_id)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  return <>
    <section className="card scan-result station-checkout-summary" aria-label="Thông tin xe ra">
      <div className="scan-card-head">
        <div><span className="card-kicker">LÀN RA OUT</span><h3>Thông tin thanh toán</h3></div>
        <span className={`scan-status ${completed ? 'scan-status--success' : 'scan-status--info'}`}>
          <span className="scan-status-dot" />
          {completed ? 'Đã hoàn tất' : 'Chờ xác nhận'}
        </span>
      </div>

      <div className="station-exit-critical">
        <div><span>Biển số</span><strong>{plate}</strong></div>
        <div><span>{completed ? 'Đã thu' : 'Phải thu'}</span><strong className="station-exit-amount">{feeLabel}</strong></div>
      </div>

      {!completed && <p className="station-checkout-instruction">
        {needsCash ? 'Đối chiếu ảnh và xác nhận đã nhận đủ tiền trước khi mở cổng.' : 'Xe miễn phí hoặc đã thanh toán. Đối chiếu ảnh trước khi mở cổng.'}
      </p>}
      {missingExitImage && !completed && <div role="alert" className="alert alert-danger station-action-alert">
        <strong>Chưa có ảnh xe ra.</strong>
        <span> Checkout đang bị khóa để tránh mở cổng nhầm xe.</span>
        <button type="button" className="btn btn-small" onClick={onRequireExitImage}>Chụp hoặc chọn ảnh xe ra</button>
      </div>}
      {preview.vehicle_type_mismatch && !completed && <div role="alert" className="alert alert-danger station-action-alert">
        <strong>Loại xe không khớp.</strong>
        <span> Vui lòng kiểm tra lại xe, biển số và liên hệ quản lý trước khi tiếp tục.</span>
      </div>}
      {preview.message && <p role="status" className="station-preview-message">{preview.message}</p>}
      {error && <p role="alert" className="alert alert-danger">{error}</p>}

      <div className="scan-result-actions station-checkout-actions">
        {!completed && (needsCash
          ? <button type="button" className="btn btn-primary" data-station-shortcut="cash" aria-keyshortcuts="F8" disabled={actionBlocked} onClick={() => setConfirmOpen(true)}>{busy ? 'Đang xử lý…' : 'Xác nhận thu tiền và mở cổng (F8)'}</button>
          : <button type="button" className="btn btn-primary" data-station-shortcut="gate" aria-keyshortcuts="F10" disabled={actionBlocked} onClick={() => setConfirmOpen(true)}>{busy ? 'Đang xử lý…' : 'Mở cổng (F10)'}</button>)}
        {needsRefresh && <button type="button" className="btn" disabled={busy} onClick={() => void act(true)}>Cập nhật phí</button>}
        {completed && <button type="button" className="btn btn-primary" data-station-shortcut="next" aria-keyshortcuts="F9" onClick={onNext}>Xe tiếp theo (F9)</button>}
      </div>
      {busy && <p role="status" className="station-busy-status"><span className="station-spinner" aria-hidden="true" />Đang gửi xác nhận checkout…</p>}
      {completed && <p role="status" className="alert alert-success">Backend đã xác nhận checkout và ghi nhận mở barrier mô phỏng.</p>}

      <details className="station-exit-details-panel">
        <summary>Chi tiết phiên xe</summary>
        <dl className="station-exit-details">
          <div><dt>Thời điểm vào</dt><dd><time dateTime={preview.check_in_time}>{new Date(preview.check_in_time).toLocaleString('vi-VN')}</time></dd></div>
          <div><dt>{completed ? 'Thời điểm ra' : 'Thời điểm ra dự kiến'}</dt><dd><time dateTime={exitTime}>{new Date(exitTime).toLocaleString('vi-VN')}</time></dd></div>
          <div><dt>Tổng thời gian gửi</dt><dd>{duration}</dd></div>
          <div><dt>Mã phiên</dt><dd className="station-session-id"><code title={preview.session_id}>{shortSessionId}</code><button type="button" className="btn btn-small" onClick={() => void copySessionId()}>{copied ? 'Đã chép' : 'Sao chép'}</button></dd></div>
        </dl>
      </details>
      <p className="muted station-barrier-note">Barrier hiện được mô phỏng ở backend; chưa điều khiển thiết bị vật lý.</p>
    </section>

    <CheckoutConfirmationDialog
      open={confirmOpen}
      busy={busy}
      needsCash={needsCash}
      plate={plate}
      laneId={preview.laneId}
      feeLabel={feeLabel}
      hasEntryImage={Boolean(preview.check_in_image_url)}
      hasExitImage={Boolean(preview.exit_image_url)}
      onCancel={() => setConfirmOpen(false)}
      onConfirm={() => void act()}
    />
  </>
}
