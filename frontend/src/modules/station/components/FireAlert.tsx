import { useEffect, useRef } from 'react'
import type { FireSignalEvent } from '../api.ts'

type Props = {
  event: FireSignalEvent
  laneName: string
  onDismiss: () => void
}

export default function FireAlert({ event, laneName, onDismiss }: Props) {
  const dismissRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dismissRef.current?.focus()
    return () => previousFocus?.focus()
  }, [])

  const isSmoke = event.event_type === 'SMOKE'
  return <div className="station-fire-backdrop">
    <section
      className="station-fire-alert"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="station-fire-title"
      aria-describedby="station-fire-description"
      onKeyDown={keyEvent => {
        if (keyEvent.key === 'Tab') {
          keyEvent.preventDefault()
          dismissRef.current?.focus()
        }
      }}
    >
      <span className="station-fire-kicker">CẢNH BÁO KHẨN CẤP</span>
      <h2 id="station-fire-title">{isSmoke ? 'PHÁT HIỆN KHÓI' : 'CẢNH BÁO CHÁY'}</h2>
      <p id="station-fire-description" className="station-fire-message">
        Phát hiện {isSmoke ? 'khói' : 'lửa'} tại <strong>{laneName}</strong>. Vui lòng kiểm tra và xử lý ngay.
      </p>
      <dl className="station-fire-facts">
        <div><dt>Camera</dt><dd>{event.camera_id}</dd></div>
        <div><dt>Độ tin cậy</dt><dd>{Math.round(event.confidence * 100)}%</dd></div>
      </dl>
      <button ref={dismissRef} type="button" className="btn station-fire-dismiss" onClick={onDismiss}>
        ĐÃ NHẬN CẢNH BÁO – TẮT
      </button>
    </section>
  </div>
}
