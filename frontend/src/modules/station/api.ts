import { apiClient } from "../../api/client.ts";
import { lanesApi } from "../../api/lanesApi.ts";
import { parkingTransactionsApi } from "../../api/services.ts";
import type { CheckInResponse, ParkingTransaction } from "../../api/domain.ts";
import type { DetectionResponse } from "../../api/services.ts";
import type {
    ConfirmationPayload,
    DetectionResult,
    Lane,
    RecentHistoryItem,
} from "./types.ts";

export type InputContext = {
    inputKind: "IMAGE_UPLOAD" | "VIDEO_FRAME";
    videoTimeMs?: number;
};
export type PriceContext = {
    vehicle_type: string;
    ticket_kind: "HOURLY" | "DAILY" | "MONTHLY" | "NIGHT";
    customer_class_id: string;
    zone_id?: string;
};
export type FireSignalEvent = {
    building_id: string | null;
    camera_id: string;
    zone_code: string | null;
    event_type: "FIRE" | "SMOKE";
    confidence: number;
    confirmed_frame_count: number;
    bbox: [number, number, number, number];
    evidence_image_path?: string | null;
    timestamp: string;
    status: string;
};
type Candidate = {
    image: Blob;
    laneId: string;
    context: InputContext;
    final?: DetectionResult;
};
const candidates = new Map<string, Candidate>();
let candidateGeneration = 0;
const confirmations = new Map<
    string,
    {
        laneId: string;
        plate: string;
        promise: Promise<{ transactionId: string }>;
    }
>();

function upload(
    image: Blob,
    laneId: string,
    mode: "preview" | "final",
    captureId?: string,
    context: InputContext = { inputKind: "VIDEO_FRAME" },
) {
    const form = new FormData();
    form.append(
        "image",
        image,
        image.type === "image/png" ? "station-image.png" : "station-image.jpg",
    );
    form.append("input_kind", context.inputKind);
    if (context.videoTimeMs != null)
        form.append("video_time_ms", String(context.videoTimeMs));
    form.append("lane_id", laneId);
    form.append("mode", mode);
    form.append("persist", mode === "final" ? "true" : "false");
    if (captureId) form.append("capture_id", captureId);
    return apiClient.postMultipart<DetectionResult>(
        "/api/v1/alpr/detections",
        form,
        { timeoutMs: 60000 },
    );
}

export async function getActiveLanes(): Promise<Lane[]> {
    return lanesApi.getActiveLanes();
}

export function detectFire(
    image: Blob,
    cameraId: string,
    buildingId?: string | null,
    signal?: AbortSignal,
): Promise<FireSignalEvent[]> {
    const form = new FormData();
    form.append("image", image, "fire-monitor-frame.jpg");
    form.append("camera_id", cameraId);
    form.append("demo_mode", "true");
    if (buildingId) form.append("building_id", buildingId);
    return apiClient.postMultipart<FireSignalEvent[]>(
        "/api/v1/alpr/fire-detection",
        form,
        { signal, timeoutMs: 60000 },
    );
}

export type ExitSession = {
    session_id: string;
    license_plate: string | null;
    ticket_code: string | null;
    check_in_time: string;
    exit_time: string;
    duration_minutes: number;
    fee: number;
    check_in_image_url: string | null;
    exit_image_url: string | null;
    status: string;
    vehicle_type_mismatch: boolean;
    message: string;
    laneId: string;
    vehicle_type_in?: string;
    vehicle_type_out?: string | null;
    is_lost_ticket?: boolean;
};
export type ExitOptions = {
    useTicketCode?: boolean;
    isLostTicket?: boolean;
    vehicleTypeOut?: string;
};
export type CheckOutResult = {
    transaction: ParkingTransaction & {
        exit_lane_id: string;
        exit_time: string;
    };
    fee: number;
    status: string;
    barrier_opened: boolean;
    message: string;
};

export async function confirmExitDetection(
    candidateId: string,
    laneId: string,
    plate: string,
): Promise<string> {
    const candidate = candidates.get(candidateId);
    if (!candidate || candidate.laneId !== laneId) {
        throw {
            status: 409,
            code: "STALE_CANDIDATE",
            message: "Khung hình đã đổi. Vui lòng chụp lại.",
        };
    }
    candidate.final ??= await upload(
        candidate.image,
        laneId,
        "final",
        candidateId,
        candidate.context,
    );
    if (!candidate.final.detection_id)
        throw new Error("Final detection was not persisted.");
    const confirmed = await apiClient.post<DetectionResponse>(
        `/api/v1/alpr/detections/${candidate.final.detection_id}/confirm`,
        {
            confirmed_plate: plate,
            check_in: false,
        },
    );
    return `/api/v1/alpr/media/${encodeURIComponent(confirmed.image_key)}`;
}

export async function prepareExit(
    laneId: string,
    identifier: string,
    exitImageUrl?: string,
    sessionId?: string,
    options: ExitOptions = {},
): Promise<ExitSession> {
    const response = await apiClient.post<Omit<ExitSession, "laneId">>(
        "/api/v1/parking/check-out/preview",
        {
            exit_lane_id: laneId,
            ...(sessionId
                ? { session_id: sessionId }
                : options.useTicketCode
                  ? { ticket_code: identifier }
                  : { license_plate: identifier }),
            ...(exitImageUrl ? { exit_image_url: exitImageUrl } : {}),
            ...(options.vehicleTypeOut
                ? { vehicle_type_out: options.vehicleTypeOut }
                : {}),
            ...(options.isLostTicket ? { is_lost_ticket: true } : {}),
        },
    );
    return {
        ...response,
        laneId,
        vehicle_type_out:
            response.vehicle_type_out ?? options.vehicleTypeOut ?? null,
        is_lost_ticket: options.isLostTicket ?? false,
    };
}

export function completeExit(
    session: ExitSession,
    cash = false,
): Promise<CheckOutResult> {
    return apiClient.post<CheckOutResult>(
        "/api/v1/parking/check-out",
        {
            session_id: session.session_id,
            exit_lane_id: session.laneId,
            expected_fee: session.fee,
            ...(session.exit_image_url
                ? { exit_image_url: session.exit_image_url }
                : {}),
            ...(session.vehicle_type_out
                ? { vehicle_type_out: session.vehicle_type_out }
                : {}),
            ...(session.is_lost_ticket ? { is_lost_ticket: true } : {}),
            ...(cash ? { payment_method: "CASH" } : {}),
        },
        {
            headers: {
                "Idempotency-Key": `station-exit-${session.session_id}`,
            },
            timeoutMs: 15000,
        },
    );
}

export async function createDetection(
    image: Blob,
    laneId: string,
    context: InputContext = { inputKind: "VIDEO_FRAME" },
): Promise<DetectionResult> {
    const generation = candidateGeneration;
    const result = await upload(image, laneId, "preview", undefined, context);
    if (generation !== candidateGeneration) return result;
    const candidateId = crypto.randomUUID();
    candidates.set(candidateId, { image, laneId, context });
    // Retain the recent consensus window, never a video worth of image blobs.
    while (candidates.size > 8)
        candidates.delete(candidates.keys().next().value!);
    return { ...result, candidate_id: candidateId };
}

export function clearCandidates(): void {
    candidateGeneration += 1;
    candidates.clear();
    confirmations.clear();
}

export async function confirmDetection(
    candidateId: string,
    laneId: string,
    payload: ConfirmationPayload,
    price?: PriceContext,
): Promise<{ transactionId: string }> {
    const existing = confirmations.get(candidateId);
    const plate = (payload.confirmed_plate_number ?? "")
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, "");
    if (plate.length < 3)
        throw {
            status: 422,
            code: "PLATE_REQUIRED",
            message: "Vui lòng nhập biển số hợp lệ trước khi xác nhận.",
        };
    if (existing) {
        if (existing.laneId !== laneId || existing.plate !== plate) {
            throw {
                status: 409,
                code: "IDEMPOTENCY_KEY_REUSED",
                message: "Khung hình đã được xác nhận với dữ liệu khác.",
            };
        }
        return existing.promise;
    }
    const candidate = candidates.get(candidateId);
    if (!candidate || candidate.laneId !== laneId) {
        throw {
            status: 409,
            code: "STALE_CANDIDATE",
            message: "Khung hình đã đổi. Vui lòng chụp lại.",
        };
    }
    const promise = (async () => {
        candidate.final ??= await upload(
            candidate.image,
            laneId,
            "final",
            candidateId,
            candidate.context,
        );
        if (!candidate.final.detection_id)
            throw new Error("Final detection was not persisted.");
        const response = await apiClient.post<CheckInResponse>(
            `/api/v1/alpr/detections/${candidate.final.detection_id}/confirm`,
            {
                confirmed_plate: payload.confirmed_plate_number,
                check_in: true,
                ...price,
            },
            { headers: { "Idempotency-Key": `station-${candidateId}` } },
        );
        return { transactionId: response.transaction.id };
    })();
    confirmations.set(candidateId, { laneId, plate, promise });
    try {
        return await promise;
    } catch (error) {
        confirmations.delete(candidateId);
        throw error;
    }
}

export async function manualCheckIn(
    laneId: string,
    plate: string,
    key: string,
    price?: PriceContext,
    useTicketCode = false,
): Promise<{ transactionId: string }> {
    const response = await parkingTransactionsApi.checkIn(
        {
            lane_id: laneId,
            ...(useTicketCode
                ? { ticket_code: plate }
                : { license_plate: plate }),
            source: "MANUAL_ENTRY",
            ...price,
        },
        key,
    );
    return { transactionId: response.transaction.id };
}

export async function getRecentHistory(): Promise<RecentHistoryItem[]> {
    return (await parkingTransactionsApi.list({ limit: 10 })).map(
        (transaction) => ({
            id: transaction.id,
            detectionId: transaction.detection_id ?? "",
            laneId: transaction.lane_id,
            plateNumber: transaction.license_plate,
            accepted: transaction.source === "AI_ACCEPTED",
            confirmedAt: transaction.check_in_time,
            transactionId: transaction.id,
        }),
    );
}

export async function uploadSessionImage(
    sessionId: string,
    direction: "entry" | "exit",
    file: File,
): Promise<string> {
    const form = new FormData();
    form.append("image", file);

    const response = await apiClient.postMultipart<{
        image_url: string;
    }>(`/api/v1/parking/sessions/${sessionId}/images/${direction}`, form, {
        timeoutMs: 30000,
    });

    return response.image_url;
}
