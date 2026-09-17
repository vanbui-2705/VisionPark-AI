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
      <div className="fs-bar">
        <div>◎ Trạm quét — toàn màn hình <span className="muted" style={{ color: '#94a3b8', fontSize: 12, marginLeft: 12 }}><span className="kbd">Enter</span> Xác nhận · <span className="kbd">E</span> Sửa · <span className="kbd">R</span> Thử lại · <span className="kbd">Space</span> Play/Pause · <span className="kbd">Esc</span> Thoát</span></div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button type="button" onClick={() => fileRef.current?.click()}>Chọn video</Button>
          <input ref={fileRef} type="file" accept="video/mp4" style={{ display: 'none' }} aria-label="Chọn video MP4" />
          <Link to="/station/scan" className="btn btn-sm">Thu nhỏ</Link>
        </div>
      </div>
      <div className="fs-main">
        <div className="fs-video" data-testid="fs-video">
          <span style={{ color: '#94a3b8' }}>{playing ? '▶ ĐANG PHÁT' : '⏸ TẠM DỪNG'} — video area (player Người 4)</span>
        </div>
        <div className="fs-panel">
          <div>
            <div style={{ color: '#94a3b8', fontSize: 13 }}>BIỂN SỐ</div>
            {editing ? (
              <input
                value={finalPlate}
                autoFocus
                onChange={(e) => setFinalPlate(e.target.value.toUpperCase())}
                style={{ width: '100%', fontSize: 32, fontWeight: 800, background: '#1e293b', color: '#fff', border: '1px solid #475569', borderRadius: 8, padding: 8, letterSpacing: '0.08em' }}
                aria-label="Sửa biển số"
              />
            ) : (
              <div className="fs-plate">{finalPlate}</div>
            )}
          </div>
          <div>
            <div style={{ color: '#94a3b8', fontSize: 13 }}>CONFIDENCE</div>
            <div className="fs-conf" style={{ color: confidence < 0.7 ? '#fbbf24' : '#4ade80' }}>{Math.round(confidence * 100)}%</div>
          </div>
          <div>
            <div style={{ color: '#94a3b8', fontSize: 13 }}>HƯỚNG</div>
            <div className="fs-conf">{direction}</div>
          </div>
          <div>
            {status === 'CONFIRMED' ? <div style={{ color: '#4ade80', fontWeight: 700 }}>✓ Đã xác nhận</div> : <div style={{ color: '#fbbf24', fontWeight: 700 }}>Chờ xác nhận</div>}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Button type="button" onClick={() => setStatus('CONFIRMED')} disabled={status === 'CONFIRMED'}>✓ Xác nhận (Enter)</Button>
            <Button type="button" variant="secondary" onClick={() => setEditing((v) => !v)}>✎ Sửa (E)</Button>
            <Button type="button" variant="secondary" onClick={() => { setStatus('WAITING_CONFIRMATION'); setEditing(false) }}>⟳ Thử lại (R)</Button>
            <Button type="button" variant="secondary" onClick={() => setPlaying((v) => !v)}>{playing ? '⏸ Pause (Space)' : '▶ Play (Space)'}</Button>
            <Button type="button" onClick={() => nav('/station/scan')}>Thoát (Esc)</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
