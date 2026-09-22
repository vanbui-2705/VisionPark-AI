import { useCallback, useEffect, useState } from "react";
import { confirmDetection, getActiveLanes, getRecentHistory, isMockMode } from "./api";
import LaneSelector from "./components/LaneSelector";
import VideoSelector from "./components/VideoSelector";
import VideoPlayer from "./components/VideoPlayer";
import ResultPanel from "./components/ResultPanel";
import ConfirmationPanel from "./components/ConfirmationPanel";
import RecentHistory from "./components/RecentHistory";
import ErrorPanel from "./components/ErrorPanel";
import { useAlprDetection } from "./hooks/useAlprDetection";
import type { ApiError, Lane, RecentHistoryItem } from "./types";
export default function StationPage() {
  const [lanes, setLanes] = useState<Lane[]>([]);
  const [selectedLaneId, setSelectedLaneId] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [videoName, setVideoName] = useState("");
  const [history, setHistory] = useState<RecentHistoryItem[]>([]);
  const [actionError, setActionError] = useState<ApiError | null>(null);
  const {
    state,
    result,
    error: detectionError,
    detect,
    retry,
    reset
  } = useAlprDetection();
  const refreshHistory = useCallback(async () => {
    try {
      setHistory(await getRecentHistory());
    } catch {/* history is secondary */}
  }, []);
  useEffect(() => {
    void (async () => {
      try {
        setLanes(await getActiveLanes());
      } catch (e) {
        setActionError(e as ApiError);
      }
      await refreshHistory();
    })();
  }, [refreshHistory]);
  useEffect(() => () => {
    if (videoUrl) URL.revokeObjectURL(videoUrl);
  }, [videoUrl]);
  const onVideo = (file: File, url: string) => {
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    setVideoUrl(url);
    setVideoName(file.name);
    reset();
  };
  const onFrame = async (image: Blob) => {
    if (!selectedLaneId) {
      setActionError({
        status: 422,
        code: "LANE_REQUIRED",
        message: "Vui lòng chọn Lane trước khi capture."
      });
      return;
    }
    setActionError(null);
    await detect(image, selectedLaneId);
  };
  const confirm = async (detectionId: string, plate?: string) => {
    setActionError(null);
    try {
      await confirmDetection(detectionId, selectedLaneId, plate ? {
        accepted: false,
        confirmed_plate_number: plate
      } : {
        accepted: true
      });
      await refreshHistory();
    } catch (e) {
      const value = e as ApiError;
      setActionError(value);
      throw value;
    }
  };
  const error = actionError ?? detectionError;
  return <section style={{
    width: "100%",
    maxWidth: 1500,
    margin: "0 auto",
    padding: 20,
    boxSizing: "border-box"
  }}>
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      gap: 12
    }}><h2>VisionPark Station</h2>{isMockMode() && <span style={{
        padding: "6px 10px",
        border: "1px solid #777",
        borderRadius: 999
      }}>MOCK ALPR</span>}</div>
    <div style={{
      display: "grid",
      gridTemplateColumns: "minmax(0, 2fr) minmax(320px, 1fr)",
      gap: 20,
      alignItems: "start"
    }}>
      <div style={{
        border: "2px solid #555",
        borderRadius: 10,
        padding: 20,
        minWidth: 0
      }}><h3>Camera / Video</h3>
        <div style={{
          display: "grid",
          gap: 14
        }}><LaneSelector lanes={lanes} selectedLaneId={selectedLaneId} onChange={setSelectedLaneId} disabled={state === "processing"} />
          <VideoSelector onVideoSelected={onVideo} />{videoName && <div>Video: <strong>{videoName}</strong></div>}</div>
        <VideoPlayer key={videoUrl || "empty"} videoUrl={videoUrl} bbox={result?.bbox ?? null} onFrameCaptured={onFrame} />
      </div>
      <aside style={{
        border: "2px solid #555",
        borderRadius: 10,
        padding: 20,
        minWidth: 0
      }}><h3>ALPR Result</h3>
        <div style={{
          padding: 12,
          border: "1px solid #666",
          borderRadius: 8
        }}><strong>Status: {state.toUpperCase()}</strong>
          <p>{state === "idle" ? "Đang chờ frame..." : state === "processing" ? "Đang nhận diện biển số..." : state === "detected" ? "Đã nhận diện biển số." : state === "confirm" ? "Cần Operator xác nhận." : "Xử lý thất bại."}</p></div>
        <ResultPanel result={result} />
        <ConfirmationPanel key={result?.detection_id ?? "none"} result={result} onConfirmCorrect={id => confirm(id)} onConfirmCorrection={(id, plate) => confirm(id, plate)} />
        <ErrorPanel error={error} onRetry={() => {
          setActionError(null);
          void retry().catch(() => undefined);
        }} />
        <RecentHistory items={history} />
      </aside>
    </div>
  </section>;
}
