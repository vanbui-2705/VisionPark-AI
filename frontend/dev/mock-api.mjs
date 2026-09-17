// Mock API cho local dev khi chưa có backend. Chạy: npm run mock-api
// ponytail: chỉ phục vụ dev; bỏ khi backend thật chạy ở :8000
import { createServer } from 'node:http'

const PORT = Number(process.env.MOCK_PORT ?? 8000)
const USERS = {
  admin: { password: 'admin', id: 'u-admin', username: 'admin', display_name: 'Quản trị', role: 'ADMIN', active: true },
  operator: { password: 'admin', id: 'u-op', username: 'operator', display_name: 'Nhân viên', role: 'OPERATOR', active: true },
}

let lanes = [
  { id: '1', name: 'LANE_IN_01', direction: 'IN', video_source: 'rtsp://mock/cam-in-01', active: true },
  { id: '2', name: 'LANE_OUT_01', direction: 'OUT', video_source: 'rtsp://mock/cam-out-01', active: true },
]
const sessions = new Map() // token -> username
let nextId = 3

let detections = [
  {
    id: 'd-1', lane_id: '1', lane_name: 'LANE_IN_01', direction: 'IN',
    ai_plate: '51H-123.45', normalized_plate: '51H12345', final_plate: '51H12345',
    confidence: 0.91, status: 'CONFIRMED', processing_ms: 132, model_version: 'mock-alpr-0.1.0',
    operator: 'Nhân viên', created_at: '2026-09-13T02:10:00Z', confirmed_at: '2026-09-13T02:10:05Z', confirmed_by: 'operator',
  },
  {
    id: 'd-2', lane_id: '2', lane_name: 'LANE_OUT_01', direction: 'OUT',
    ai_plate: '30E-99x.88', normalized_plate: '30E99X88', final_plate: null,
    confidence: 0.64, status: 'NEEDS_CONFIRMATION', processing_ms: 155, model_version: 'mock-alpr-0.1.0',
    operator: null, created_at: '2026-09-13T02:12:00Z', confirmed_at: null, confirmed_by: null,
  },
]

let auditLogs = [
  {
    id: 'a-1', actor: 'admin', action: 'LANE_CREATE', resource: 'lane', resource_id: '2',
    before: null, after: { name: 'LANE_OUT_01', direction: 'OUT' },
    created_at: '2026-09-12T08:00:00Z', correlation_id: 'mock-corr-1',
  },
]
let nextAuditId = 2

const auditPush = (actor, action, resource, resourceId, before, after) =>
  auditLogs.unshift({
    id: `a-${nextAuditId++}`, actor, action, resource, resource_id: resourceId,
    before, after, created_at: new Date().toISOString(), correlation_id: `mock-${Date.now()}`,
  })

const json = (res, status, body) => {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
  })
  res.end(JSON.stringify(body))
}
const err = (res, status, code, message) =>
  json(res, status, { code, message, details: null, correlation_id: `mock-${Date.now()}` })

const readBody = (req) =>
  new Promise((resolve) => {
    let raw = ''
    req.on('data', (c) => (raw += c))
    req.on('end', () => {
      try {
        resolve(raw ? JSON.parse(raw) : {})
      } catch {
        resolve({})
      }
    })
  })

const userOf = (req) => {
  const h = req.headers.authorization ?? ''
  const username = sessions.get(h.replace(/^Bearer\s+/i, ''))
  const u = username && USERS[username]
  return u && u.active ? { id: u.id, username: u.username, display_name: u.display_name, role: u.role, active: u.active } : null
}

createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`)
  const path = url.pathname
  if (req.method === 'OPTIONS') return json(res, 204, null)

  if (path === '/health/live' || path === '/health/ready')
    return json(res, 200, path.endsWith('live') ? { status: 'ok' } : { status: 'ready', alpr: { ready: true, provider: 'mock-alpr-0.1.0' } })

  if (path === '/api/v1/auth/login' && req.method === 'POST') {
    const { username, password } = await readBody(req)
    const u = USERS[username]
    if (!u || u.password !== password || !u.active) return err(res, 401, 'UNAUTHENTICATED', 'Tên đăng nhập hoặc mật khẩu không đúng.')
    const token = `mock-token-${username}-${Date.now()}`
    sessions.set(token, username)
    return json(res, 200, { access_token: token, token_type: 'bearer' })
  }

  const me = userOf(req)
  if (path === '/api/v1/auth/register' && req.method === 'POST') {
    const b = await readBody(req)
    const username = String(b.username ?? '').trim()
    const email = b.email ? String(b.email).trim() : null
    const allowed = process.env.VITE_PUBLIC_REGISTRATION_ENABLED ?? process.env.PUBLIC_REGISTRATION_ENABLED
    if (String(allowed).toLowerCase() !== 'true') return err(res, 404, 'NOT_FOUND', 'Đăng ký tài khoản hiện không được bật.')
    if (!username || !b.display_name || !b.password) return err(res, 422, 'VALIDATION_ERROR', 'Thiếu trường bắt buộc.')
    if (USERS[username]) return err(res, 409, 'DUPLICATE_USER', 'Tên đăng nhập đã tồn tại.')
    const id = `u-${Date.now()}`
    USERS[username] = { password: String(b.password), id, username, display_name: String(b.display_name), role: 'OPERATOR', active: true, email }
    auditPush('system', 'USER_REGISTER', 'user', id, null, { username })
    return json(res, 201, { id, username, display_name: USERS[username].display_name, role: 'OPERATOR', active: true })
  }
  if (path === '/api/v1/auth/me' && req.method === 'GET') {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    return json(res, 200, me)
  }

  if (path === '/api/v1/lanes' && req.method === 'GET') {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    return json(res, 200, lanes)
  }

  if (path === '/api/v1/lanes' && req.method === 'POST') {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    if (me.role !== 'ADMIN') return err(res, 403, 'FORBIDDEN', 'Không có quyền.')
    const b = await readBody(req)
    const name = String(b.name ?? '').trim()
    if (!name || (b.direction !== 'IN' && b.direction !== 'OUT')) return err(res, 422, 'VALIDATION_ERROR', 'Tên làn và direction không hợp lệ.')
    if (lanes.some((l) => l.name === name)) return err(res, 409, 'DUPLICATE_LANE_NAME', 'Tên làn đã tồn tại.')
    const lane = { id: String(nextId++), name, direction: b.direction, video_source: b.video_source ?? null, active: b.active !== false }
    lanes.push(lane)
    return json(res, 201, lane)
  }

  const laneMatch = path.match(/^\/api\/v1\/lanes\/([^/]+)$/)
  if (laneMatch) {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    const lane = lanes.find((l) => l.id === laneMatch[1])
    if (!lane) return err(res, 404, 'NOT_FOUND', 'Không tìm thấy làn.')
    if (req.method === 'GET') return json(res, 200, lane)
    if (req.method === 'PATCH') {
      if (me.role !== 'ADMIN') return err(res, 403, 'FORBIDDEN', 'Không có quyền.')
      const b = await readBody(req)
      if (b.name !== undefined) {
        const name = String(b.name).trim()
        if (lanes.some((l) => l.id !== lane.id && l.name === name)) return err(res, 409, 'DUPLICATE_LANE_NAME', 'Tên làn đã tồn tại.')
        lane.name = name
      }
      if (b.direction !== undefined) lane.direction = b.direction
      if (b.video_source !== undefined) lane.video_source = b.video_source
      if (b.active !== undefined) lane.active = !!b.active
      return json(res, 200, lane)
    }
  }

  if (path === '/api/v1/users' && req.method === 'GET') {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    if (me.role !== 'ADMIN') return err(res, 403, 'FORBIDDEN', 'Không có quyền.')
    const q = (url.searchParams.get('q') ?? '').toLowerCase()
    const role = url.searchParams.get('role')
    const list = Object.values(USERS)
      .filter((u) => !q || u.username.toLowerCase().includes(q) || u.display_name.toLowerCase().includes(q))
      .filter((u) => !role || u.role === role)
      .map(({ password: _pw, ...u }) => u)
    return json(res, 200, list)
  }

  if (path === '/api/v1/users' && req.method === 'POST') {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    if (me.role !== 'ADMIN') return err(res, 403, 'FORBIDDEN', 'Không có quyền.')
    const b = await readBody(req)
    const username = String(b.username ?? '').trim()
    if (!username || !b.display_name || !b.password || (b.role !== 'ADMIN' && b.role !== 'OPERATOR'))
      return err(res, 422, 'VALIDATION_ERROR', 'Dữ liệu không hợp lệ.')
    if (USERS[username]) return err(res, 409, 'DUPLICATE_USER', 'Tên đăng nhập hoặc email đã tồn tại.')
    const id = `u-${Date.now()}`
    USERS[username] = { password: String(b.password), id, username, display_name: String(b.display_name), role: b.role, active: b.active !== false, email: b.email ?? null }
    const { password: _pw, ...pub } = USERS[username]
    auditPush(me.username, 'USER_CREATE', 'user', id, null, { username, role: b.role })
    return json(res, 201, pub)
  }

  const userMatch = path.match(/^\/api\/v1\/users\/([^/]+)$/)
  if (userMatch) {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    if (me.role !== 'ADMIN') return err(res, 403, 'FORBIDDEN', 'Không có quyền.')
    const u = Object.values(USERS).find((x) => x.id === userMatch[1])
    if (!u) return err(res, 404, 'NOT_FOUND', 'Không tìm thấy người dùng.')
    if (req.method === 'GET') { const { password: _pw, ...pub } = u; return json(res, 200, pub) }
    if (req.method === 'PATCH') {
      const b = await readBody(req)
      if (b.display_name !== undefined) u.display_name = String(b.display_name)
      if (b.email !== undefined) u.email = b.email
      if (b.role !== undefined && b.role !== u.role) {
        if (u.username === 'admin' && b.role !== 'ADMIN') return err(res, 422, 'LAST_ADMIN', 'Không thể hạ quyền quản trị viên cuối cùng.')
        u.role = b.role
      }
      if (b.active !== undefined) {
        if (u.username === 'admin' && !b.active) return err(res, 422, 'LAST_ADMIN', 'Không thể vô hiệu hóa quản trị viên cuối cùng.')
        u.active = !!b.active
      }
      const { password: _pw, ...pub } = u
      auditPush(me.username, 'USER_UPDATE', 'user', u.id, null, { username: u.username, role: u.role, active: u.active })
      return json(res, 200, pub)
    }
  }

  if (path === '/api/v1/detections' && req.method === 'GET') {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    const limit = Number(url.searchParams.get('limit') ?? 50)
    const laneId = url.searchParams.get('lane_id')
    let list = [...detections].reverse()
    if (laneId) list = list.filter((d) => d.lane_id === laneId)
    return json(res, 200, list.slice(0, limit))
  }

  const detMatch = path.match(/^\/api\/v1\/detections\/([^/]+)(\/confirm)?$/)
  if (detMatch) {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    const d = detections.find((x) => x.id === detMatch[1])
    if (!d) return err(res, 404, 'NOT_FOUND', 'Không tìm thấy nhận diện.')
    if (detMatch[2] && req.method === 'POST') {
      const b = await readBody(req)
      const finalPlate = String(b.final_plate ?? '').trim()
      if (!finalPlate) return err(res, 422, 'VALIDATION_ERROR', 'final_plate không hợp lệ.')
      const wasCorrected = finalPlate.replace(/[^A-Z0-9]/gi, '').toUpperCase() !== (d.normalized_plate ?? '').toUpperCase()
      d.final_plate = finalPlate
      d.status = wasCorrected ? 'CORRECTED' : 'CONFIRMED'
      d.confirmed_at = new Date().toISOString()
      d.confirmed_by = me.username
      auditPush(me.username, 'DETECTION_CONFIRM', 'detection', d.id, { status: 'NEEDS_CONFIRMATION' }, { status: d.status, final_plate: finalPlate })
      return json(res, 200, d)
    }
    if (req.method === 'GET') return json(res, 200, d)
  }

  if (path === '/api/v1/audit-logs' && req.method === 'GET') {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    if (me.role !== 'ADMIN') return err(res, 403, 'FORBIDDEN', 'Không có quyền.')
    const limit = Number(url.searchParams.get('limit') ?? 50)
    return json(res, 200, auditLogs.slice(0, limit))
  }

  if (path === '/api/v1/roles' && req.method === 'GET') {
    if (!me) return err(res, 401, 'UNAUTHENTICATED', 'Chưa đăng nhập.')
    return json(res, 200, [
      { name: 'ADMIN', display_name: 'Quản trị viên', description: 'Toàn quyền cấu hình và vận hành' },
      { name: 'OPERATOR', display_name: 'Nhân viên vận hành', description: 'Scan, xác nhận biển số, xem lịch sử' },
    ])
  }

  return err(res, 404, 'NOT_FOUND', `Không có endpoint ${req.method} ${path}`)
}).listen(PORT, () => console.log(`Mock VisionPark API: http://localhost:${PORT} (admin/admin, operator/admin)`))
