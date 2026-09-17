import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ApiError } from '../../src/api/errors.ts'
import { apiClient, setUnauthorizedHandler } from '../../src/api/client.ts'
import { getToken, setToken } from '../../src/api/token.ts'

function mockFetchOnce(handler: (req: Request) => Response | Promise<Response>) {
  const orig = globalThis.fetch
  globalThis.fetch = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
    const req = new Request(url as string, init)
    return handler(req)
  }) as unknown as typeof fetch
  return () => { globalThis.fetch = orig }
}

afterEach(() => vi.restoreAllMocks())

describe('api/client', () => {
  beforeEach(() => { localStorage.clear(); setUnauthorizedHandler(null) })

  it('attaches Authorization header when token exists', async () => {
    setToken('tok123')
    let auth = ''
    const restore = mockFetchOnce((req) => { auth = req.headers.get('Authorization') ?? ''; return new Response(JSON.stringify({ ok: true }), { status: 200 }) })
    await apiClient.get('/api/v1/auth/me')
    expect(auth).toBe('Bearer tok123')
    restore()
  })

  it('parses success JSON', async () => {
    const restore = mockFetchOnce(() => new Response(JSON.stringify({ hello: 'world' }), { status: 200 }))
    const data = await apiClient.get<{ hello: string }>('/api/v1/lanes')
    expect(data.hello).toBe('world')
    restore()
  })

  it('parses standard error contract', async () => {
    const restore = mockFetchOnce(() => new Response(JSON.stringify({ code: 'DUPLICATE_LANE_NAME', message: 'Exists', correlation_id: 'cid1' }), { status: 409 }))
    try { await apiClient.post('/api/v1/lanes', {}); expect.fail('should throw') }
    catch (e) { const err = e as ApiError; expect(err.code).toBe('DUPLICATE_LANE_NAME'); expect(err.status).toBe(409); expect(err.correlationId).toBe('cid1') }
    restore()
  })

  it('handles 401: removes token and throws ApiError', async () => {
    setToken('bad')
    const restore = mockFetchOnce(() => new Response(JSON.stringify({ code: 'UNAUTHENTICATED', message: 'Unauthorized' }), { status: 401 }))
    try { await apiClient.get('/api/v1/auth/me'); expect.fail() } catch (e) { expect((e as ApiError).status).toBe(401) }
    expect(getToken()).toBeNull()
    restore()
  })

  it('calls onUnauthorized on 401 when not on /login', async () => {
    const fn = vi.fn()
    setUnauthorizedHandler(fn)
    setToken('bad')
    const restore = mockFetchOnce(() => new Response('{}', { status: 401 }))
    try { await apiClient.get('/api/v1/lanes') } catch { /* ignore */ }
    expect(fn).toHaveBeenCalled()
    restore()
  })

  it('does not break FormData (client sets no explicit Content-Type)', async () => {
    let bodyIsFormData = false
    let explicitCT: string | null = 'unset'
    const orig = globalThis.fetch
    globalThis.fetch = vi.fn(async (_url: string | URL | Request, init?: RequestInit) => {
      bodyIsFormData = init?.body instanceof FormData
      explicitCT = (init?.headers as Record<string, string>)?.['Content-Type'] ?? null
      return new Response(JSON.stringify({ ok: true }), { status: 200 })
    }) as unknown as typeof fetch
    const fd = new FormData()
    fd.append('image', new Blob(['x']), 'x.jpg')
    fd.append('lane_id', '1')
    await apiClient.postMultipart('/api/v1/alpr/detections', fd)
    expect(bodyIsFormData).toBe(true)
    expect(explicitCT).toBeNull()
    globalThis.fetch = orig
  })
})
