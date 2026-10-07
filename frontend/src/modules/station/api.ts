import type { ApiError, ConfirmationPayload, DetectionResult, Lane, RecentHistoryItem } from "./types";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const REQUEST_TIMEOUT_MS = 10_000;
const USE_MOCK = import.meta.env.VITE_USE_MOCK_ALPR !== "false";
function tokenHeader(): HeadersInit {
  const token = localStorage.getItem("access_token");
  return token ? {
    Authorization: `Bearer ${token}`
  } : {};
}
async function parseError(response: Response): Promise<ApiError> {
  let body: {
    code?: string;
    message?: string;
    detail?: string;
  } = {};
  try {
    body = await response.json();
  } catch {/* non-json error */}
  return {
    status: response.status,
    code: body.code ?? `HTTP_${response.status}`,
    message: body.message ?? body.detail ?? `Request failed (${response.status}).`
  };
}
async function request<T>(url: string, init: RequestInit, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal
    });
    if (!response.ok) throw await parseError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw {
        status: 408,
        code: "TIMEOUT",
        message: "Yêu cầu quá thời gian chờ."
      } satisfies ApiError;
    }
    if (typeof error === "object" && error !== null && "code" in error) throw error;
    throw {
      status: 0,
      code: "NETWORK_ERROR",
      message: "Không thể kết nối tới Backend."
    } satisfies ApiError;
  } finally {
    window.clearTimeout(timeout);
  }
}
const mockLanes: Lane[] = [{
  id: "11111111-1111-1111-1111-111111111111",
  name: "Cổng vào 01",
  direction: "IN",
  active: true
}, {
  id: "22222222-2222-2222-2222-222222222222",
  name: "Cổng ra 01",
  direction: "OUT",
  active: true
}];
let mockHistory: RecentHistoryItem[] = [];
export async function getActiveLanes(): Promise<Lane[]> {
  if (USE_MOCK) return mockLanes.filter(lane => lane.direction === "IN");
  const lanes = await request<Lane[]>(`${API_BASE_URL}/lanes`, {
    headers: tokenHeader()
  });
  return lanes.filter(lane => lane.active && lane.direction === "IN");
}
export async function createDetection(image: Blob, laneId: string): Promise<DetectionResult> {
  if (USE_MOCK) {
    await new Promise(resolve => window.setTimeout(resolve, 350));
    return {
      detection_id: crypto.randomUUID(),
      raw_plate_number: "29A-123.45",
      normalized_plate_number: "29A12345",
      bbox: [120, 340, 250, 410],
      confidence: 0.91,
      processing_time_ms: 25,
      model_version: "mock-alpr-0.1.0",
      requires_confirmation: false,
      detector_confidence: 0.91,
      ocr_confidence: 0.91,
      combined_confidence: 0.91,
      quality_flags: [],
      provider: "mock",
      provider_status: "ready"
    };
  }
  const form = new FormData();
  form.append("image", image, "station-frame.jpg");
  form.append("lane_id", laneId);
  form.append("mode", "preview");
  form.append("persist", "false");
  return request<DetectionResult>(`${API_BASE_URL}/alpr/detections`, {
    method: "POST",
    headers: tokenHeader(),
    body: form
  });
}
export async function confirmDetection(detectionId: string, laneId: string, payload: ConfirmationPayload): Promise<{ transactionId: string }> {
  if (USE_MOCK) {
    await new Promise(resolve => window.setTimeout(resolve, 200));
    const plate = payload.accepted === true ? (payload.confirmed_plate_number ?? "29A12345") : payload.confirmed_plate_number;
    const transactionId = crypto.randomUUID();
    mockHistory = [{
      id: crypto.randomUUID(),
      detectionId,
      laneId,
      plateNumber: plate,
      accepted: payload.accepted,
      confirmedAt: new Date().toISOString(),
      transactionId
    }, ...mockHistory].slice(0, 10);
    return { transactionId };
  }
  const response = await request<{ transaction: { id: string } }>(`${API_BASE_URL}/parking/check-in`, {
    method: "POST",
    headers: {
      ...tokenHeader(),
      "Content-Type": "application/json",
      "Idempotency-Key": `station-${detectionId}-${payload.accepted ? "accepted" : payload.confirmed_plate_number}`
    },
    body: JSON.stringify({
      lane_id: laneId,
      license_plate: payload.accepted ? (payload.confirmed_plate_number ?? "29A12345") : payload.confirmed_plate_number,
      detection_id: detectionId,
      source: payload.accepted ? "AI_ACCEPTED" : "OPERATOR_CORRECTED"
    })
  });
  return { transactionId: response.transaction.id };
}
export async function getRecentHistory(): Promise<RecentHistoryItem[]> {
  if (USE_MOCK) return mockHistory;
  const transactions = await request<Array<{
    id: string;
    lane_id: string;
    license_plate: string;
    source: string;
    check_in_time: string;
  }>>(`${API_BASE_URL}/parking/transactions?limit=10`, {
    headers: tokenHeader()
  });
  return transactions.map(transaction => ({
    id: transaction.id,
    detectionId: transaction.id,
    laneId: transaction.lane_id,
    plateNumber: transaction.license_plate,
    accepted: transaction.source === "AI_ACCEPTED",
    confirmedAt: transaction.check_in_time,
    transactionId: transaction.id
  }));
}
export function isMockMode() {
  return USE_MOCK;
}
