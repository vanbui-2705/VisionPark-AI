import { ApiError } from './errors.ts'
import { getToken, removeToken } from './token.ts'

function getBaseUrl(): string {
  const v = import.meta.env.VITE_API_BASE_URL
  if (v) return v.replace(/\/$/, '')
  return 'http://localhost:8000'
}

function getTimeoutMs(): number {
  const v = import.meta.env.VITE_API_TIMEOUT_MS
  const n = v ? Number(v) : 15000
  return Number.isFinite(n) && n > 0 ? n : 15000
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  params?: Record<string, string | number | boolean | undefined | null>
}

function buildUrl(path: string, params?: RequestOptions['params']): string {
  const base = getBaseUrl()
  const url = path.startsWith('http') ? path : `${base}${path.startsWith('/') ? '' : '/'}${path}`
  if (!params) return url
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const qs = sp.toString()
  return qs ? `${url}?${qs}` : url
}

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn
}

async function parseErrorBody(res: Response): Promise<{ message: string; code: string; details?: unknown; correlationId?: string }> {
  try {
    const data = (await res.json()) as Record<string, unknown>
    return {
      message: (data.message as string) || (data.detail as string) || res.statusText,
      code: (data.code as string) || String(res.status),
      details: data.details ?? data.detail,
      correlationId: data.correlation_id as string | undefined,
    }
  } catch {
    return { message: res.statusText || `Request failed (${res.status})`, code: String(res.status) }
  }
}

async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const { params, body, headers: extraHeaders, signal: externalSignal, ...rest } = opts

  const url = buildUrl(path, params)
  const token = getToken()

  const headers: Record<string, string> = {}
  if (extraHeaders) {
    for (const [k, v] of Object.entries(extraHeaders as Record<string, string>)) headers[k] = v
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let fetchBody: BodyInit | undefined
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  if (body !== undefined && body !== null) {
    if (isFormData) {
      fetchBody = body as unknown as BodyInit
      // do not set Content-Type for FormData; browser sets boundary
    } else if (typeof body === 'string') {
      fetchBody = body
      if (!headers['Content-Type']) headers['Content-Type'] = 'application/json'
    } else {
      fetchBody = JSON.stringify(body)
      if (!headers['Content-Type']) headers['Content-Type'] = 'application/json'
    }
  }

  const timeoutMs = getTimeoutMs()
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(new DOMException('TimeoutError', 'TimeoutError')), timeoutMs)
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort((externalSignal as AbortSignal).reason)
    else externalSignal.addEventListener('abort', () => controller.abort((externalSignal as AbortSignal).reason), { once: true })
  }

  let res: Response
  try {
    res = await fetch(url, { method, headers, body: fetchBody, signal: controller.signal, ...rest })
  } catch (e: unknown) {
    clearTimeout(id)
    if (e instanceof DOMException && e.name === 'TimeoutError') {
      throw new ApiError('Không thể kết nối tới máy chủ. Vui lòng thử lại.', {
        status: 0,
        code: 'TIMEOUT',
      })
    }
    if (e instanceof DOMException && e.name === 'AbortError') {
      // Re-throw timeout as ApiError, other aborts as-is
      throw e
    }
    throw new ApiError('Không thể kết nối tới máy chủ. Vui lòng thử lại.', {
      status: 0,
      code: 'NETWORK_ERROR',
    })
  }
  clearTimeout(id)

  if (res.status === 401) {
    const inLogin = typeof window !== 'undefined' && window.location.pathname === '/login'
    removeToken()
    if (!inLogin && onUnauthorized) onUnauthorized()
    const parsed = await parseErrorBody(res)
    throw new ApiError(parsed.message || 'Unauthorized', {
      status: 401,
      code: parsed.code || 'UNAUTHENTICATED',
      details: parsed.details,
      correlationId: parsed.correlationId,
    })
  }

  if (!res.ok) {
    const parsed = await parseErrorBody(res)
    throw new ApiError(parsed.message, {
      status: res.status,
      code: parsed.code,
      details: parsed.details,
      correlationId: parsed.correlationId,
    })
  }

  if (res.status === 204) return undefined as T
  const text = await res.text()
  if (!text) return undefined as T
  try {
    return JSON.parse(text) as T
  } catch {
    return text as unknown as T
  }
}

export const apiClient = {
  get<T>(path: string, opts?: RequestOptions): Promise<T> {
    return request<T>('GET', path, opts)
  },
  post<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
    return request<T>('POST', path, { ...opts, body })
  },
  postMultipart<T>(path: string, formData: FormData, opts?: RequestOptions): Promise<T> {
    return request<T>('POST', path, { ...opts, body: formData })
  },
  patch<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
    return request<T>('PATCH', path, { ...opts, body })
  },
  put<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
    return request<T>('PUT', path, { ...opts, body })
  },
  del<T>(path: string, opts?: RequestOptions): Promise<T> {
    return request<T>('DELETE', path, opts)
  },
}

export function getApiBaseUrl(): string {
  return getBaseUrl()
}
