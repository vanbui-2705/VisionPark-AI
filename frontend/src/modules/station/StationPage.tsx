import { t as translate } from "../../lib/i18n"
import { useCallback, useEffect, useRef, useState } from "react";
import { clearCandidates, confirmDetection, getActiveLanes, getRecentHistory, manualCheckIn } from "./api";
import LaneSelector from "./components/LaneSelector";
import VideoSelector from "./components/VideoSelector";
import VideoPlayer from "./components/VideoPlayer";
import ResultPanel from "./components/ResultPanel";
import ConfirmationPanel from "./components/ConfirmationPanel";
import RecentHistory from "./components/RecentHistory";
import ErrorPanel from "./components/ErrorPanel";
import { useAlprDetection } from "./hooks/useAlprDetection";
import type { ApiError, Lane, RecentHistoryItem } from "./types";
import { DetectionImage } from "../../components/DetectionImage";
import { useAuth } from "../auth/AuthContext";
import { can } from "../../lib/permissions";
export default function StationPage() {
  const { user } = useAuth();
  const mayReadTransactions = can(user, 'transactions.read');
  const [inputMode, setInputMode] = useState<'image' | 'video'>('video');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState('');
  const [lanes, setLanes] = useState<Lane[]>([]);
  const [selectedLaneId, setSelectedLaneId] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [videoName, setVideoName] = useState("");
  const [history, setHistory] = useState<RecentHistoryItem[]>([]);
  const [actionError, setActionError] = useState<ApiError | null>(null);
  const [transactionId, setTransactionId] = useState<string | null>(null);
  const [manualPlate, setManualPlate] = useState('');
  const [editingPlate, setEditingPlate] = useState(false);
  const manualKey = useRef(crypto.randomUUID());
  const confirming = useRef(false);
  const {
    state,
    result,
    error: detectionError,
    detect,
    retry,
    reset,
    beginConfirm,
    completeConfirm,
    failConfirm
  } = useAlprDetection();
  const refreshHistory = useCallback(async () => {
    if (!mayReadTransactions) { setHistory([]); return; }
    try {
      setHistory(await getRecentHistory());
    } catch {/* history is secondary */}
  }, [mayReadTransactions]);
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
  useEffect(() => () => clearCandidates(), []);
  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl); }, [imageUrl]);
  const changeInput = (mode: 'image' | 'video') => {
    if (confirming.current) return;
    setInputMode(mode); setImageFile(null); setImageUrl(''); setVideoUrl(''); setVideoName('');
    setTransactionId(null); setEditingPlate(false); setActionError(null);
    clearCandidates(); reset();
  };
  const chooseImage = (file: File | null) => {
    clearCandidates(); reset(); setTransactionId(null); setEditingPlate(false);
    setImageFile(null); setImageUrl(''); setActionError(null);
    if (!file) return;
    if (!['image/jpeg', 'image/png'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      setActionError({ status: 422, code: 'INVALID_IMAGE', message: translate("Chọn ảnh JPEG/PNG không quá 5MB.") }); return;
    }
    setImageFile(file); setImageUrl(URL.createObjectURL(file));
  };
  const onVideo = (file: File, url: string) => {
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    setVideoUrl(url);
    setVideoName(file.name);
    setTransactionId(null);
    setEditingPlate(false);
    clearCandidates();
    reset();
  };
  const onFrame = useCallback(async (image: Blob, videoTimeMs?: number) => {
    if (confirming.current || transactionId) return;
    if (!selectedLaneId) {
      setActionError({
        status: 422,
        code: "LANE_REQUIRED",
        message: translate("Vui lòng chọn Lane trước khi capture.")
      });
      return;
    }
    setActionError(null);
    await detect(image, selectedLaneId, { inputKind: inputMode === 'image' ? 'IMAGE_UPLOAD' : 'VIDEO_FRAME', videoTimeMs });
  }, [detect, selectedLaneId, transactionId, inputMode]);
  const changeLane = (laneId: string) => {
    setSelectedLaneId(laneId);
    setEditingPlate(false);
    setTransactionId(null);
    setActionError(null);
    manualKey.current = crypto.randomUUID();
    clearCandidates();
    reset();
  };
  const confirm = async (detectionId: string, plate?: string) => {
    if (confirming.current) return;
    confirming.current = true;

    setActionError(null);
    beginConfirm();
    try {
      const outcome = await confirmDetection(detectionId, selectedLaneId, plate ? {
        accepted: false,
        confirmed_plate_number: plate
      } : {
        accepted: true,
        confirmed_plate_number: result?.normalized_plate_number ?? result?.raw_plate_number ?? undefined
      });
      setTransactionId(outcome.transactionId);
      completeConfirm();
      await refreshHistory();
    } catch (e) {
      const value = e as ApiError;
      setActionError(value);
      failConfirm();
      throw value;
    } finally {
      confirming.current = false;
    }
  };
  const confirmManual = async () => {
    if (confirming.current || !selectedLaneId || state === 'detecting' || state === 'reading') return;
    confirming.current = true;
    beginConfirm();
    setActionError(null);
    try {
      const outcome = await manualCheckIn(selectedLaneId, manualPlate, `manual-${manualKey.current}`);
      setTransactionId(outcome.transactionId);
      completeConfirm();
      await refreshHistory();
    } catch (error) {
      setActionError(error as ApiError);
      failConfirm();
    } finally { confirming.current = false; }
  };
  const statusLabel: Record<typeof state, string> = {
    idle: translate("Đang chờ frame..."),
    detecting: translate("Đang gửi frame..."),
    reading: translate("Đang đọc biển số..."),
    stable: translate("Kết quả ổn định."),
    needs_confirmation: translate("Cần Operator xác nhận."),
    confirming: translate("Đang tạo check-in..."),
    success: translate("Check-in thành công."),
    error: translate("Xử lý thất bại.")
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
    }}><h2>{translate("Trạm quét biển số")}</h2></div>
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
      }}><h3>{translate("Ảnh / Video")}</h3>
        <label>{translate("Chế độ nhận diện")}<select aria-label={translate("Chế độ nhận diện")} value={inputMode} disabled={state === 'confirming'} onChange={event => changeInput(event.target.value as 'image' | 'video')}><option value="image">{translate("Ảnh JPEG/PNG")}</option><option value="video">Video MP4</option></select></label>
        <div style={{
          display: "grid",
          gap: 14
        }}><LaneSelector lanes={lanes} selectedLaneId={selectedLaneId} onChange={changeLane} disabled={state === "detecting" || state === "reading" || state === "confirming"} />
          {inputMode === 'video' ? <VideoSelector onVideoSelected={onVideo} disabled={state === 'confirming'} /> : <label>{translate("Ảnh đầu vào")}<input aria-label={translate("Ảnh đầu vào")} type="file" accept="image/jpeg,image/png" disabled={state === 'confirming'} onChange={event => chooseImage(event.target.files?.[0] ?? null)} /></label>}{videoName && <div>Video: <strong>{videoName}</strong></div>}</div>
          {inputMode === 'video' ? <VideoPlayer key={videoUrl || "empty"} videoUrl={videoUrl} bbox={result?.bbox ?? null} onFrameCaptured={onFrame} suspended={editingPlate || state === 'confirming' || Boolean(transactionId)} /> : <>
            {imageUrl && <DetectionImage key={imageUrl} src={imageUrl} bbox={result?.bbox ? { x: result.bbox[0], y: result.bbox[1], w: result.bbox[2] - result.bbox[0], h: result.bbox[3] - result.bbox[1] } : null} />}
            <button type="button" disabled={!imageFile || !selectedLaneId || state === 'detecting' || state === 'reading' || state === 'confirming' || Boolean(transactionId)} onClick={() => { if (imageFile) void onFrame(imageFile).catch(() => undefined); }}>{translate("Nhận diện ảnh")}</button>
          </>}
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
          <p>{statusLabel[state]}</p>{transactionId && <p role="status">Transaction: <strong>{transactionId}</strong></p>}</div>
        <ResultPanel result={result} />
        <ConfirmationPanel key={result?.candidate_id ?? result?.detection_id ?? "none"} onEditingChange={setEditingPlate} disabled={state === 'detecting' || state === 'reading' || state === 'confirming' || Boolean(transactionId)} result={result} onConfirmCorrect={id => confirm(id)} onConfirmCorrection={(id, plate) => confirm(id, plate)} />
        <form onSubmit={event => { event.preventDefault(); void confirmManual(); }}>
          <h3>{translate("Check-in thủ công")}</h3>
          <label htmlFor="manual-plate">{translate("Biển số nhập tay")}</label>
          <input id="manual-plate" value={manualPlate} disabled={state === 'confirming' || Boolean(transactionId)} onChange={event => { setManualPlate(event.target.value); manualKey.current = crypto.randomUUID(); }} />
          <button type="submit" disabled={!selectedLaneId || manualPlate.replace(/[^a-z0-9]/gi, '').length < 3 || state === 'detecting' || state === 'reading' || state === 'confirming' || Boolean(transactionId)}>{translate("Tạo check-in")}</button>
        </form>
        {transactionId && <button type="button" onClick={() => { setTransactionId(null); setEditingPlate(false); setManualPlate(''); setActionError(null); manualKey.current = crypto.randomUUID(); clearCandidates(); reset(); }}>{translate("Xe tiếp theo")}</button>}
        <ErrorPanel error={error} onRetry={() => {
          setActionError(null);
          setEditingPlate(false);
          void retry().catch(() => undefined);
        }} />
        <RecentHistory items={history} />
      </aside>
    </div>
  </section>;
}
