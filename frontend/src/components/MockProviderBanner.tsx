import { useEffect, useState } from 'react'
import { healthApi } from '../api/healthApi.ts'

function isMockProvider(p?: string): boolean {
  if (!p) return false
  const v = p.toLowerCase()
  return v === 'mock' || v === 'mock-alpr' || v === 'mockalprruntime' || v.includes('mock')
}

export function MockProviderBanner() {
  const [provider, setProvider] = useState<string | null | undefined>(undefined)

  useEffect(() => {
    healthApi
      .ready()
      .then((h) => {
        const p = (h as { alpr?: { provider?: string } })?.alpr?.provider as string | undefined
        setProvider(p ?? null)
      })
      .catch(() => setProvider(null))
  }, [])

  if (provider === undefined) return null
  if (provider === null) {
    return <div className="banner-mock">Không xác định trạng thái ALPR provider.</div>
  }
  if (!isMockProvider(provider)) return null
  return (
    <div className="banner-mock" role="status">
      <strong>CHẾ ĐỘ MÔ PHỎNG ALPR</strong> — Hệ thống hiện đang sử dụng Mock ALPR ({provider}). Kết quả nhận diện không đến từ model AI thực tế.
    </div>
  )
}
