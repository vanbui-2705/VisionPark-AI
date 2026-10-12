import { t as translate } from "../lib/i18n"
import { useEffect, useState } from 'react'
import { apiClient, getApiBaseUrl } from '../api/client.ts'
import type { Detection } from '../api/domain.ts'

export function DetectionImage({ src, bbox }: { src: string; bbox?: Detection['bbox'] }) {
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [loaded, setLoaded] = useState<{ src: string; url?: string; failed?: boolean }>()
  const base = new URL(getApiBaseUrl(), window.location.origin)
  const target = new URL(src, base)
  const protectedMedia = target.origin === base.origin && target.pathname.startsWith('/api/v1/alpr/media/')
  useEffect(() => {
    if (!protectedMedia) return
    const controller = new AbortController()
    let objectUrl: string | undefined
    void apiClient.getBlob(src, { signal: controller.signal }).then(blob => {
      if (controller.signal.aborted) return
      objectUrl = URL.createObjectURL(blob)
      setLoaded({ src, url: objectUrl })
    }).catch(() => {
      if (!controller.signal.aborted) setLoaded({ src, failed: true })
    })
    return () => {
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [src, protectedMedia])
  const imageSrc = protectedMedia ? (loaded?.src === src ? loaded.url : undefined) : src
  if (protectedMedia && loaded?.src === src && loaded.failed) return <p role="status">Không tải được ảnh.</p>
  if (!imageSrc) return <p role="status">Đang tải ảnh…</p>
  return <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%' }}>
    <img src={imageSrc} alt={translate("Khung hình nhận diện")} style={{ maxWidth: '100%', display: 'block', borderRadius: 8 }} onLoad={event => {
      setSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })
    }} />
    {bbox && size.width > 0 && size.height > 0 && <span title="AI bounding box" style={{
      position: 'absolute', pointerEvents: 'none', border: '2px solid #22c55e', boxSizing: 'border-box',
      left: `${100 * bbox.x / size.width}%`, top: `${100 * bbox.y / size.height}%`,
      width: `${100 * bbox.w / size.width}%`, height: `${100 * bbox.h / size.height}%`,
    }} />}
  </div>
}
