import { apiClient } from '../../api/client.ts'
import { lanesApi } from '../../api/lanesApi.ts'
import { parkingTransactionsApi } from '../../api/services.ts'
import type { CheckInResponse } from '../../api/domain.ts'
import type { ConfirmationPayload, DetectionResult, Lane, RecentHistoryItem } from './types.ts'

export type InputContext = { inputKind: "IMAGE_UPLOAD" | "VIDEO_FRAME"; videoTimeMs?: number }
type Candidate = { image: Blob; laneId: string; context: InputContext; final?: DetectionResult }
const candidates = new Map<string, Candidate>()
let candidateGeneration = 0
const confirmations = new Map<string, { laneId: string; plate: string; promise: Promise<{ transactionId: string }> }>()

function upload(image: Blob, laneId: string, mode: 'preview' | 'final', captureId?: string, context: InputContext = { inputKind: 'VIDEO_FRAME' }) {
  const form = new FormData()
  form.append('image', image, image.type === 'image/png' ? 'station-image.png' : 'station-image.jpg')
  form.append('input_kind', context.inputKind)
  if (context.videoTimeMs != null) form.append('video_time_ms', String(context.videoTimeMs))
  form.append('lane_id', laneId)
  form.append('mode', mode)
  form.append('persist', mode === 'final' ? 'true' : 'false')
  if (captureId) form.append('capture_id', captureId)
  return apiClient.postMultipart<DetectionResult>('/api/v1/alpr/detections', form, { timeoutMs: 60000 })
}

export async function getActiveLanes(): Promise<Lane[]> {
  return (await lanesApi.getActiveLanes()).filter(lane => lane.direction === 'IN')
}

export async function createDetection(image: Blob, laneId: string, context: InputContext = { inputKind: "VIDEO_FRAME" }): Promise<DetectionResult> {
  const generation = candidateGeneration
  const result = await upload(image, laneId, 'preview', undefined, context)
  if (generation !== candidateGeneration) return result
  const candidateId = crypto.randomUUID()
  candidates.set(candidateId, { image, laneId, context })
  // Retain the recent consensus window, never a video worth of image blobs.
  while (candidates.size > 8) candidates.delete(candidates.keys().next().value!)
  return { ...result, candidate_id: candidateId }
}

export function clearCandidates(): void {
  candidateGeneration += 1
  candidates.clear()
  confirmations.clear()
}

export async function confirmDetection(candidateId: string, laneId: string, payload: ConfirmationPayload): Promise<{ transactionId: string }> {
  const existing = confirmations.get(candidateId)
  const plate = (payload.confirmed_plate_number ?? '').toUpperCase().replace(/[^A-Z0-9]/g, '')
  if (existing) {
    if (existing.laneId !== laneId || existing.plate !== plate) {
      throw { status: 409, code: 'IDEMPOTENCY_KEY_REUSED', message: 'Khung hình đã được xác nhận với dữ liệu khác.' }
    }
    return existing.promise
  }
  const candidate = candidates.get(candidateId)
  if (!candidate || candidate.laneId !== laneId) {
    throw { status: 409, code: 'STALE_CANDIDATE', message: 'Khung hình đã đổi. Vui lòng chụp lại.' }
  }
  const promise = (async () => {
    candidate.final ??= await upload(candidate.image, laneId, 'final', candidateId, candidate.context)
    if (!candidate.final.detection_id) throw new Error('Final detection was not persisted.')
    const response = await apiClient.post<CheckInResponse>(
      `/api/v1/alpr/detections/${candidate.final.detection_id}/confirm`,
      { confirmed_plate: payload.confirmed_plate_number, check_in: true },
      { headers: { 'Idempotency-Key': `station-${candidateId}` } },
    )
    return { transactionId: response.transaction.id }
  })()
  confirmations.set(candidateId, { laneId, plate, promise })
  try { return await promise } catch (error) {
    confirmations.delete(candidateId)
    throw error
  }

}

export async function manualCheckIn(laneId: string, plate: string, key: string): Promise<{ transactionId: string }> {
  const response = await parkingTransactionsApi.checkIn({
    lane_id: laneId, license_plate: plate, source: 'MANUAL_ENTRY',
  }, key)
  return { transactionId: response.transaction.id }
}

export async function getRecentHistory(): Promise<RecentHistoryItem[]> {
  return (await parkingTransactionsApi.list({ limit: 10 })).map(transaction => ({
    id: transaction.id,
    detectionId: transaction.detection_id ?? '',
    laneId: transaction.lane_id,
    plateNumber: transaction.license_plate,
    accepted: transaction.source === 'AI_ACCEPTED',
    confirmedAt: transaction.check_in_time,
    transactionId: transaction.id,
  }))
}
