import { t as translate } from "../lib/i18n"
import { useState } from 'react'
import type { Detection } from '../api/domain.ts'

export function DetectionImage({ src, bbox }: { src: string; bbox?: Detection['bbox'] }) {
  const [size, setSize] = useState({ width: 0, height: 0 })
  return <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%' }}>
    <img src={src} alt={translate("Khung hình nhận diện")} style={{ maxWidth: '100%', display: 'block', borderRadius: 8 }} onLoad={event => {
      setSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })
    }} />
    {bbox && size.width > 0 && size.height > 0 && <span title="AI bounding box" style={{
      position: 'absolute', pointerEvents: 'none', border: '2px solid #22c55e', boxSizing: 'border-box',
      left: `${100 * bbox.x / size.width}%`, top: `${100 * bbox.y / size.height}%`,
      width: `${100 * bbox.w / size.width}%`, height: `${100 * bbox.h / size.height}%`,
    }} />}
  </div>
}
