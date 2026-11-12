import { useEffect, useRef } from 'react'

type Props = {
  open: boolean
  busy: boolean
  needsCash: boolean
  plate: string
  laneId: string
  feeLabel: string
  hasEntryImage: boolean
  hasExitImage: boolean
  onCancel: () => void
  onConfirm: () => void
}

export default function CheckoutConfirmationDialog({
  open,
  busy,
  needsCash,
  plate,
  laneId,
  feeLabel,
  hasEntryImage,
  hasExitImage,
  onCancel,
  onConfirm,
}: Props) {
  const confirmRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!open) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const frame = requestAnimationFrame(() => confirmRef.current?.focus())
    return () => {
      cancelAnimationFrame(frame)
      previousFocus?.focus()
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onCancel()
      if (event.key !== 'Tab') return
      const focusable = [...(dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])') ?? [])]
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [busy, onCancel, open])

  if (!open) return null

  return <div className="station-dialog-backdrop" role="presentation" onMouseDown={event => {
    if (event.target === event.currentTarget && !busy) onCancel()
  }}>
    <section ref={dialogRef} className="station-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="checkout-confirm-title">
      <div className="scan-card-head">
        <div>
          <span className="card-kicker">XÁC NHẬN CUỐI</span>
          <h3 id="checkout-confirm-title">{needsCash ? 'Thu tiền và mở cổng' : 'Mở cổng xe ra'}</h3>
        </div>
      </div>
      <p className="station-confirm-warning">
        Hãy đối chiếu đúng xe trước khi tiếp tục. Thao tác này sẽ ghi nhận checkout và mở barrier mô phỏng.
      </p>
      <dl className="station-confirm-facts">
        <div><dt>Biển số</dt><dd>{plate}</dd></div>
        <div><dt>Làn ra</dt><dd>{laneId}</dd></div>
        <div><dt>Số tiền</dt><dd className="station-exit-amount">{feeLabel}</dd></div>
        <div><dt>Ảnh lúc vào</dt><dd>{hasEntryImage ? 'Đã có' : 'Không có'}</dd></div>
        <div><dt>Ảnh lúc ra</dt><dd className={hasExitImage ? undefined : 'text-danger'}>{hasExitImage ? 'Đã có' : 'Thiếu ảnh'}</dd></div>
      </dl>
      <div className="scan-dialog-actions">
        <button type="button" className="btn" disabled={busy} onClick={onCancel}>Quay lại đối chiếu</button>
        <button ref={confirmRef} type="button" className="btn btn-primary" disabled={busy || !hasExitImage} onClick={onConfirm}>
          {busy ? 'Đang xử lý…' : needsCash ? `Xác nhận đã thu ${feeLabel}` : 'Xác nhận mở cổng'}
        </button>
      </div>
    </section>
  </div>
}
