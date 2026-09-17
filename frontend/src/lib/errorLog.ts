// Error log nội bộ frontend cho Error Center. Chỉ ghi lỗi client bắt được — không fake server errors.
export interface ClientError {
  id: number
  time: string
  code: string
  status: number
  message: string
  source: string
  correlationId?: string
}

let list: ClientError[] = []
let nextId = 1
const subs = new Set<() => void>()

export function recordError(e: { code: string; status: number; message: string; source?: string; correlationId?: string }): void {
  list = [{ id: nextId++, time: new Date().toISOString(), source: e.source ?? 'frontend', ...e }, ...list].slice(0, 200)
  subs.forEach((fn) => fn())
}

export function getErrorLog(): ClientError[] {
  return list
}

export function subscribeErrorLog(fn: () => void): () => void {
  subs.add(fn)
  return () => subs.delete(fn)
}

export function clearErrorLog(): void {
  list = []
  subs.forEach((fn) => fn())
}
