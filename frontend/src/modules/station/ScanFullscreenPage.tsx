import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/Button.tsx'

// Shell toàn màn hình — video player thật sẽ do Người 4 ghép vào .fs-video.
// Phím tắt: Enter=Confirm, E=Edit, R=Retry, Space=Play/Pause, Esc=Exit.
export function ScanFullscreenPage() {
  const nav = useNavigate()
  const [playing, setPlaying] = useState(true)
  const [plate] = useState('51H-123.45')
  const [confidence] = useState(0.91)
  const [direction] = useState<'IN' | 'OUT'>('IN')
  const [status, setStatus] = useState<'WAITING_CONFIRMATION' | 'CONFIRMED'>('WAITING_CONFIRMATION')
  const [editing, setEditing] = useState(false)
  const [finalPlate, setFinalPlate] = useState(plate.replace(/[^A-Z0-9]/gi, '').toUpperCase())
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === 'INPUT' && e.key !== 'Escape') return
      if (e.key === 'Enter') {
        e.preventDefault()
        if (!editing) setStatus('CONFIRMED')
      } else if (e.key.toLowerCase() === 'e') {
        setEditing((v) => !v)
      } else if (e.key.toLowerCase() === 'r') {
        setStatus('WAITING_CONFIRMATION')
        setEditing(false)
      } else if (e.key === ' ') {
        e.preventDefault()
        setPlaying((v) => !v)
      } else if (e.key === 'Escape') {
        nav('/station/scan')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [nav, editing])

  return (
    <div className="fs-shell">
      <header className="fs-bar">
        <div className="fs-bar-heading">
          <span className="fs-brand-mark" aria-hidden="true">◎</span>
          <div className="fs-bar-copy">
            <span className="fs-kicker">TRẠM KIỂM SOÁT · VISIONPARK</span>
            <h1>Vận hành toàn màn hình</h1>
          </div>
          <div className="fs-shortcuts" aria-label="Phím tắt">
            <span><kbd className="kbd">Enter</kbd> Xác nhận</span>
            <span><kbd className="kbd">E</kbd> Sửa</span>
            <span><kbd className="kbd">R</kbd> Thử lại</span>
            <span><kbd className="kbd">Space</kbd> Phát / tạm dừng</span>
            <span><kbd className="kbd">Esc</kbd> Thoát</span>
          </div>
        </div>
        <div className="fs-bar-actions">
          <Button type="button" className="fs-upload-action" onClick={() => fileRef.current?.click()}>Chọn video</Button>
          <input ref={fileRef} type="file" accept="video/mp4" style={{ display: 'none' }} aria-label="Chọn video MP4" />
          <Link to="/station/scan" className="btn btn-sm fs-minimize-action">Thu nhỏ</Link>
        </div>
      </header>
      <main className="fs-main">
        <div className="fs-video" data-testid="fs-video">
          <span className="fs-video-state">{playing ? '▶ ĐANG PHÁT' : '⏸ TẠM DỪNG'}</span>
          <span className="fs-video-placeholder">Khu vực hiển thị luồng camera · Player</span>
        </div>
        <aside className="fs-panel" aria-label="Kết quả nhận diện">
          <div className="fs-panel-heading">
            <span className="fs-kicker">NHẬN DIỆN GẦN NHẤT</span>
            <h2>Thông tin phương tiện</h2>
          </div>
          <div className="fs-primary-result">
            <div className="fs-data-label">Biển số</div>
            {editing ? (
              <input
                value={finalPlate}
                autoFocus
                onChange={(e) => setFinalPlate(e.target.value.toUpperCase())}
                className="fs-plate-input"
                aria-label="Sửa biển số"
              />
            ) : (
              <div className="fs-plate">{finalPlate}</div>
            )}
          </div>
          <div className="fs-metric-grid">
            <div className="fs-metric">
              <span className="fs-data-label">Độ tin cậy</span>
              <strong className={`fs-metric-value ${confidence < 0.7 ? 'is-warning' : 'is-positive'}`}>{Math.round(confidence * 100)}%</strong>
            </div>
            <div className="fs-metric">
              <span className="fs-data-label">Hướng di chuyển</span>
              <strong className="fs-metric-value">{direction === 'IN' ? 'Vào' : 'Ra'}</strong>
            </div>
          </div>
          <div className={`fs-review-state ${status === 'CONFIRMED' ? 'is-confirmed' : 'is-pending'}`} role="status">
            <span className="fs-review-dot" aria-hidden="true" />
            {status === 'CONFIRMED' ? 'Đã xác nhận' : 'Chờ xác nhận'}
          </div>
          <div className="fs-actions">
            <Button type="button" onClick={() => setStatus('CONFIRMED')} disabled={status === 'CONFIRMED'}>✓ Xác nhận <kbd className="fs-action-key">Enter</kbd></Button>
            <Button type="button" variant="secondary" onClick={() => setEditing((v) => !v)}>✎ Sửa <kbd className="fs-action-key">E</kbd></Button>
            <div className="fs-actions-secondary">
              <Button type="button" variant="secondary" onClick={() => { setStatus('WAITING_CONFIRMATION'); setEditing(false) }}>⟳ Thử lại <kbd className="fs-action-key">R</kbd></Button>
              <Button type="button" variant="secondary" onClick={() => setPlaying((v) => !v)}>{playing ? '⏸ Tạm dừng' : '▶ Phát'} <kbd className="fs-action-key">Space</kbd></Button>
            </div>
            <Button type="button" variant="ghost" className="fs-exit-action" onClick={() => nav('/station/scan')}>Thoát toàn màn hình <kbd className="fs-action-key">Esc</kbd></Button>
          </div>
        </aside>
      </main>
    </div>
  )
}
