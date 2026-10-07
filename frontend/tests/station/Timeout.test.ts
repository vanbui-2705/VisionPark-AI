import { afterEach, expect, it, vi } from 'vitest'
import { createDetection } from '../../src/modules/station/api'

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })
it('allows slow real inference beyond the ordinary 15s API timeout, with a bounded deadline', async () => {
  vi.useFakeTimers()
  let signal!: AbortSignal
  vi.spyOn(globalThis, 'fetch').mockImplementation((_url, options) => {
    signal = options!.signal as AbortSignal
    return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(signal.reason)))
  })
  const outcome = createDetection(new Blob(['frame'], { type: 'image/jpeg' }), 'lane').catch(error => error)
  await vi.advanceTimersByTimeAsync(15001)
  expect(signal.aborted).toBe(false)
  await vi.advanceTimersByTimeAsync(45000)
  expect((await outcome).code).toBe('TIMEOUT')
})
