export type StationState =
  | "idle"
  | "detecting"
  | "reading"
  | "stable"
  | "needs_confirmation"
  | "confirming"
  | "success"
  | "error";
export type LaneDirection = "IN" | "OUT";
export type Lane = {
  id: string;
  name: string;
  direction: LaneDirection;
  active: boolean;
};
export type DetectionResult = {
  detection_id: string;
  raw_plate_number: string | null;
  normalized_plate_number: string | null;
  bbox: [number, number, number, number] | null;
  confidence: number;
  processing_time_ms: number;
  model_version: string;
  requires_confirmation: boolean;
  detector_confidence?: number | null;
  ocr_confidence?: number | null;
  combined_confidence?: number | null;
  quality_flags?: string[];
  provider?: string;
  provider_status?: string;
};
export type ApiError = {
  status: number;
  code: string;
  message: string;
};
export type ConfirmationPayload = {
  accepted: true;
  confirmed_plate_number?: string;
} | {
  accepted: false;
  confirmed_plate_number: string;
};
export type RecentHistoryItem = {
  id: string;
  detectionId: string;
  laneId: string;
  plateNumber: string;
  accepted: boolean;
  confirmedAt: string;
  transactionId?: string;
};
