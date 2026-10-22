import { useCallback, useRef, useState } from "react";
import type { InputContext } from "../api";
import { createDetection } from "../api";
import type { ApiError, DetectionResult, StationState } from "../types";
type LastRequest = {
  image: Blob;
  laneId: string;
  context: InputContext;
};
function normalizeError(error: unknown): ApiError {
  if (typeof error === "object" && error !== null && "code" in error) {
    const value = error as Partial<ApiError>;
    return {
      status: value.status ?? 0,
      code: value.code ?? "UNKNOWN_ERROR",
      message: value.message ?? "Có lỗi xảy ra."
    };
  }
  return {
    status: 0,
    code: "NETWORK_ERROR",
    message: "Không thể kết nối tới Backend."
  };
}
export function useAlprDetection() {
  const [state, setState] = useState<StationState>("idle");
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const generationRef = useRef(0);
  const processingRef = useRef(false);
  const requestIdRef = useRef(0);
  const lastRequestRef = useRef<LastRequest | null>(null);
  const candidatesRef = useRef<DetectionResult[]>([]);
  const lastBboxRef = useRef<DetectionResult["bbox"]>(null);
  const execute = useCallback(async (image: Blob, laneId: string, context: InputContext = { inputKind: "VIDEO_FRAME" }) => {
    if (processingRef.current) throw {
      status: 409,
      code: "REQUEST_IN_PROGRESS",
      message: "Một yêu cầu ALPR đang được xử lý."
    } satisfies ApiError;
    const generation = generationRef.current;
    const requestId = ++requestIdRef.current;
    processingRef.current = true;
    setState("detecting");
    setError(null);
    try {
      setState("reading");
      const detection = await createDetection(image, laneId, context);
      if (generation !== generationRef.current) return;
      const previous = lastBboxRef.current;
      if (previous && detection.bbox && bboxChanged(previous, detection.bbox)) {
        candidatesRef.current = [];
      }
      lastBboxRef.current = detection.bbox;
      candidatesRef.current = [...candidatesRef.current, detection].slice(-3);
      const consensus = getConsensus(candidatesRef.current);
      const stable = consensus ?? detection;
      setResult(stable);
      setState(stable.requires_confirmation || (!consensus && context.inputKind !== "IMAGE_UPLOAD") ? "needs_confirmation" : "stable");
      return stable;
    } catch (unknownError) {
      if (generation !== generationRef.current) return;
      const apiError = normalizeError(unknownError);
      setError(apiError);
      setState("error");
      throw apiError;
    } finally {
      if (requestId === requestIdRef.current) processingRef.current = false;
    }
  }, []);
  const detect = useCallback(async (image: Blob, laneId: string, context: InputContext = { inputKind: "VIDEO_FRAME" }) => {
    if (!laneId) {
      const error = {
        status: 422,
        code: "LANE_REQUIRED",
        message: "Vui lòng chọn Lane trước khi nhận diện."
      } satisfies ApiError;
      setError(error);
      setState("error");
      throw error;
    }
    lastRequestRef.current = {
      image,
      laneId, context
    };
    return execute(image, laneId, context);
  }, [execute]);
  const retry = useCallback(async () => {
    if (!lastRequestRef.current) return;
    return execute(lastRequestRef.current.image, lastRequestRef.current.laneId, lastRequestRef.current.context);
  }, [execute]);
  const reset = useCallback(() => {
    generationRef.current += 1;
    // Keep the in-flight lock until the old request actually settles.
    // The generation guard below discards its stale response.
    setState("idle");
    setResult(null);
    setError(null);
    lastRequestRef.current = null;
    candidatesRef.current = [];
    lastBboxRef.current = null;
  }, []);
  const beginConfirm = useCallback(() => setState("confirming"), []);
  const completeConfirm = useCallback(() => setState("success"), []);
  const failConfirm = useCallback(() => setState("error"), []);
  return {
    state,
    result,
    error,
    detect,
    retry,
    reset,
    beginConfirm,
    completeConfirm,
    failConfirm
  };
}

function bboxChanged(a: [number, number, number, number], b: [number, number, number, number]) {
  const centerA = [(a[0] + a[2]) / 2, (a[1] + a[3]) / 2];
  const centerB = [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
  const width = Math.max(a[2] - a[0], b[2] - b[0], 1);
  const height = Math.max(a[3] - a[1], b[3] - b[1], 1);
  return Math.abs(centerA[0] - centerB[0]) > width * 0.35 || Math.abs(centerA[1] - centerB[1]) > height * 0.35;
}

function getConsensus(candidates: DetectionResult[]): DetectionResult | null {
  const plates = candidates.map(item => item.normalized_plate_number).filter((plate): plate is string => Boolean(plate));
  if (!plates.length) return null;
  const winner = [...new Set(plates)].sort((a, b) => plates.filter(item => item === b).length - plates.filter(item => item === a).length)[0];
  if (plates.filter(item => item === winner).length < 2) return null;
  return [...candidates].reverse().find(item => item.normalized_plate_number === winner) ?? null;
}
