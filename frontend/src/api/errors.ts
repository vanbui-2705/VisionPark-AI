export interface ApiErrorPayload {
  code: string
  message: string
  details?: unknown
  correlation_id?: string
}

export class ApiError extends Error {
  status: number
  code: string
  details?: unknown
  correlationId?: string

  constructor(
    message: string,
    opts: { status: number; code: string; details?: unknown; correlationId?: string },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = opts.status
    this.code = opts.code
    this.details = opts.details
    this.correlationId = opts.correlationId
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError
}
