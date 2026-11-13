import { getToken } from '../api/token.ts'

export function recordError(error: {
  code: string
  status: number
  source?: string
  correlationId?: string
}): void {
  const token = getToken()
  if (!token) return
  const base = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
  const code = error.code.replace(/[^A-Z0-9_]/g, '_').slice(0, 64) || 'UNKNOWN'
  void fetch(`${base}/api/v1/errors`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      code,
      status: error.status,
      source: (error.source ?? 'frontend').replace(/[^a-zA-Z0-9_.-]/g, '_').slice(0, 32),
      correlation_id: error.correlationId?.replace(/[^a-zA-Z0-9-]/g, '').slice(0, 64),
    }),
  }).catch(() => undefined)
}
