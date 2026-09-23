export type StationState = "idle" | "processing" | "detected" | "confirm" | "error";
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
};
export type ApiError = {
  status: number;
  code: string;
  message: string;
};
export type ConfirmationPayload = {
  accepted: true;
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
};
