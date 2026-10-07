import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearCandidates, confirmDetection, createDetection, getActiveLanes } from '../../src/modules/station/api.ts'
import { setToken } from '../../src/api/token.ts'

const result = { detection_id: null, normalized_plate_number: '29A12345', confidence: 0.9 }
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })

describe('Station API contract', () => {
  beforeEach(() => { clearCandidates(); localStorage.clear(); setToken('operator-token') })
  afterEach(() => vi.restoreAllMocks())

  it('uses the shared token and real lane activity field', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response([
      { id: 'in', name: 'Entry', direction: 'IN', is_active: true },
      { id: 'out', name: 'Exit', direction: 'OUT', is_active: true },
    ]))
    expect(await getActiveLanes()).toMatchObject([{ id: 'in', active: true }])
    expect(fetch.mock.calls[0][0]).toContain('/api/v1/lanes/active')
    expect(fetch.mock.calls[0][1]?.headers).toMatchObject({ Authorization: 'Bearer operator-token' })
  })

  it('previews without persistence and retries canonical confirmation without another final frame', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(response(result))
      .mockResolvedValueOnce(response({ ...result, detection_id: 'saved-detection' }))
      .mockRejectedValueOnce(new TypeError('connection lost'))
      .mockResolvedValueOnce(response({ transaction: { id: 'parked' } }))
    const preview = await createDetection(new Blob(['jpeg'], { type: 'image/jpeg' }), 'in')
    expect(preview.detection_id).toBeNull()
    const form = fetch.mock.calls[0][1]?.body as FormData
    expect(form.get('persist')).toBe('false')
    const payload = { accepted: false as const, confirmed_plate_number: '30F12345' }
    await expect(confirmDetection(preview.candidate_id!, 'in', payload)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    expect(await confirmDetection(preview.candidate_id!, 'in', payload)).toEqual({ transactionId: 'parked' })
    expect(fetch).toHaveBeenCalledTimes(4)
    const finalForm = fetch.mock.calls[1][1]!.body as FormData
    expect(finalForm.get('persist')).toBe('true')
    expect(finalForm.get('capture_id')).toBe(preview.candidate_id)
    expect(fetch.mock.calls[2][0]).toContain('/api/v1/alpr/detections/saved-detection/confirm')
    expect(JSON.parse(String(fetch.mock.calls[2][1]?.body))).toEqual({ confirmed_plate: '30F12345', check_in: true })
    expect(fetch.mock.calls[2][1]?.headers).toEqual(fetch.mock.calls[3][1]?.headers)
    await confirmDetection(preview.candidate_id!, 'in', payload)
    await expect(confirmDetection(preview.candidate_id!, 'in', { accepted: false, confirmed_plate_number: '30F99999' }))
      .rejects.toMatchObject({ status: 409 })
    expect(fetch).toHaveBeenCalledTimes(4)
  })

  it('rejects a candidate from a different lane before persisting', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(result))
    const preview = await createDetection(new Blob(['jpeg']), 'in')
    await expect(confirmDetection(preview.candidate_id!, 'other', { accepted: true, confirmed_plate_number: '29A12345' }))
      .rejects.toMatchObject({ code: 'STALE_CANDIDATE' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('does not recreate a confirmable candidate after clearing a pending preview', async () => {
    let resolve!: (value: Response) => void
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() => new Promise(done => { resolve = done }))
    const pending = createDetection(new Blob(['jpeg']), 'in')
    clearCandidates()
    resolve(response(result))
    expect((await pending).candidate_id).toBeUndefined()
  })
  it('does not send a notification/error report for every failed preview frame', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({ code: 'ALPR_NOT_READY', message: 'Unavailable' }, 503))
    await expect(createDetection(new Blob(['jpeg']), 'in')).rejects.toMatchObject({ code: 'ALPR_NOT_READY' })
    await Promise.resolve()
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
