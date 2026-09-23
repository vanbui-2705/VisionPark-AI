import { useCallback, useRef, useState } from "react";
import { createDetection } from "../api";
import type { ApiError, DetectionResult, StationState } from "../types";
type LastRequest = {
  image: Blob;
  laneId: string;
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
  const processingRef = useRef(false);
  const lastRequestRef = useRef<LastRequest | null>(null);
  const execute = useCallback(async (image: Blob, laneId: string) => {
    if (processingRef.current) throw {
      status: 409,
      code: "REQUEST_IN_PROGRESS",
      message: "Một yêu cầu ALPR đang được xử lý."
    } satisfies ApiError;
    processingRef.current = true;
    setState("processing");
    setError(null);
    try {
      const detection = await createDetection(image, laneId);
      setResult(detection);
      setState(detection.requires_confirmation ? "confirm" : "detected");
      return detection;
    } catch (unknownError) {
      const apiError = normalizeError(unknownError);
      setError(apiError);
      setState("error");
      throw apiError;
    } finally {
      processingRef.current = false;
    }
  }, []);
  const detect = useCallback(async (image: Blob, laneId: string) => {
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
      laneId
    };
    return execute(image, laneId);
  }, [execute]);
  const retry = useCallback(async () => {
    if (!lastRequestRef.current) return;
    return execute(lastRequestRef.current.image, lastRequestRef.current.laneId);
  }, [execute]);
  const reset = useCallback(() => {
    setState("idle");
    setResult(null);
    setError(null);
    lastRequestRef.current = null;
  }, []);
  return {
    state,
    result,
    error,
    detect,
    retry,
    reset
  };
}
