import { MockProviderBanner } from '../../components/MockProviderBanner.tsx'
import { useAuth } from '../auth/AuthContext.tsx'

// Integration seam for Người 4 — do not rewrite internals.
// Người 4 replaces this file with the real Station entrypoint (StationLayout / StationPage).
// Shared deps available to Station: useAuth(), apiClient (Bearer + timeout + FormData), UI components.

export function StationPage() {
  const { user } = useAuth()
  return (
    <div>
      <MockProviderBanner />
      <div style={{ padding: 16 }}>
        <h2>Station</h2>
        <p>
          Xin chào {user?.display_name} ({user?.role})
        </p>
        <p>
          Chờ bàn giao Station module từ Người 4. Route /station + auth + API client đã sẵn sàng.
        </p>
      </div>
    </div>
  )
}
