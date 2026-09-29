import { useEffect, useState } from 'react'
import { healthApi } from '../api/healthApi.ts'

function isMockProvider(p?: string): boolean {
  if (!p) return false
  const v = p.toLowerCase()
  return v === 'mock' || v === 'mock-alpr' || v === 'mockalprruntime' || v.includes('mock')
}

function isDetectorOnlyProvider(p?: string): boolean {
  return p?.toLowerCase() === 'real'
}

export function MockProviderBanner() {
  const [provider, setProvider] = useState<string | null | undefined>(undefined)

  useEffect(() => {
    healthApi
      .ready()
      .then((h) => {
        const alpr = (h as { alpr?: { provider?: string; ocr_enabled?: boolean } })?.alpr
        const p = alpr?.provider as string | undefined
        setProvider(alpr?.ocr_enabled === false && isDetectorOnlyProvider(p) ? 'real-detector-only' : (p ?? null))
      })
      .catch(() => setProvider(null))
  }, [])

  if (provider === undefined) return null
  if (provider === null) {
    return <div className="banner-mock">Không xác định trạng thái ALPR provider.</div>
  }
  if (!isMockProvider(provider) && provider !== 'real-detector-only') return null
  return (
    <div className="banner-mock" role="status">
      {provider === 'real-detector-only' ? (
        <><strong>DETECTOR-ONLY</strong> — Đã dùng model AI để vẽ bounding box; OCR đang hoãn, cần xác nhận biển số thủ công.</>
      ) : (
        <><strong>CHẾ ĐỘ MÔ PHỎNG ALPR</strong> — Hệ thống hiện đang sử dụng Mock ALPR ({provider}). Kết quả nhận diện không đến từ model AI thực tế.</>
      )}
    </div>
  )
}
