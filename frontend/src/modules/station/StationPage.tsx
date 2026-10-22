import { t as translate } from "../../lib/i18n"
import { useCallback, useEffect, useRef, useState } from "react";
import { clearCandidates, confirmDetection, getActiveLanes, getRecentHistory, manualCheckIn, type PriceContext } from "./api";
import { apiClient } from '../../api/client.ts';
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
  const [useTicketCode, setUseTicketCode] = useState(false);
  const [customerClasses, setCustomerClasses] = useState<{ id: string; name: string }[]>([]);
  const [classId, setClassId] = useState('');
  const [vehicleType, setVehicleType] = useState('CAR');
  const [ticketKind, setTicketKind] = useState<PriceContext['ticket_kind']>('HOURLY');
  const [zoneId, setZoneId] = useState('');
  const scopedLane = lanes.find(lane => lane.id === selectedLaneId && lane.building_id);
  const priceContext: PriceContext | undefined = scopedLane && classId ? { vehicle_type: vehicleType, ticket_kind: ticketKind, customer_class_id: classId, ...(zoneId ? { zone_id: zoneId } : {}) } : undefined;
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
  useEffect(() => {
    const buildingId = scopedLane?.building_id;
    if (!buildingId) { setCustomerClasses([]); setClassId(''); return; }
    apiClient.get<{ id: string; name: string }[]>('/api/v1/pricing/customer-classes', { params: { building_id: buildingId } })
      .then(items => { setCustomerClasses(items); if (items.length) setClassId(items[0].id); })
      .catch(e => setActionError(e as ApiError));
  }, [scopedLane?.building_id]);
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
    if (confirming.current) { URL.revokeObjectURL(url); return; }
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
    if (confirming.current) return;
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
    if (scopedLane && !priceContext) { setActionError({ status: 422, code: 'PRICE_CONTEXT_REQUIRED', message: 'Chọn hạng khách và loại vé trước khi check-in.' }); return; }
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
      }, priceContext);
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
    if (scopedLane && !priceContext) { setActionError({ status: 422, code: 'PRICE_CONTEXT_REQUIRED', message: 'Chọn hạng khách và loại vé trước khi check-in.' }); return; }
    confirming.current = true;
    beginConfirm();
    setActionError(null);
    try {
      const outcome = await manualCheckIn(selectedLaneId, manualPlate, `manual-${manualKey.current}`, priceContext, useTicketCode);
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
  return <section className="stack scan-page">
    <header className="scan-hero">
      <div className="scan-hero-copy">
        <span className="scan-kicker">TRẠM KIỂM SOÁT CỔNG</span>
        <h2>{translate("Trạm quét biển số")}</h2>
        <p>{statusLabel[state]}</p>
      </div>
      <div className="scan-hero-actions">
        <span className="scan-state">Status: {state.toUpperCase()}</span>
      </div>
    </header>

    <div className="scan-toolbar">
      <label className="field scan-control-group">
        <span>{translate("Chế độ nhận diện")}</span>
        <span className="scan-select-wrap">
          <select className="scan-select" aria-label={translate("Chế độ nhận diện")} value={inputMode} disabled={state === 'confirming'} onChange={event => changeInput(event.target.value as 'image' | 'video')}>
            <option value="image">{translate("Ảnh JPEG/PNG")}</option>
            <option value="video">Video MP4</option>
          </select>
        </span>
      </label>
      <LaneSelector lanes={lanes} selectedLaneId={selectedLaneId} onChange={changeLane} disabled={state === "detecting" || state === "reading" || state === "confirming"} />
      {inputMode === 'video' ? (
        <VideoSelector onVideoSelected={onVideo} disabled={state === 'confirming'} />
      ) : (
        <label className="field scan-control-group">
          <span>{translate("Ảnh đầu vào")}</span>
          <input aria-label={translate("Ảnh đầu vào")} type="file" accept="image/jpeg,image/png" disabled={state === 'confirming'} onChange={event => chooseImage(event.target.files?.[0] ?? null)} />
        </label>
      )}
      {videoName && <div className="scan-file-name">Video: <strong>{videoName}</strong></div>}
    </div>

    {scopedLane && <div className="card card-polished">
      <div className="scan-card-head" style={{ marginBottom: 12 }}>
        <div>
          <span className="card-kicker">BIỂU PHÍ ÁP DỤNG</span>
          <h3>Thông tin tính phí</h3>
        </div>
      </div>
      <div className="form-grid">
        <label className="field"><span>Loại xe</span><input value={vehicleType} onChange={e => setVehicleType(e.target.value)} /></label>
        <label className="field"><span>Loại vé</span><select value={ticketKind} onChange={e => setTicketKind(e.target.value as PriceContext['ticket_kind'])}><option value="HOURLY">Theo giờ</option><option value="DAILY">Ngày</option><option value="MONTHLY">Tháng</option><option value="NIGHT">Đêm</option></select></label>
        <label className="field"><span>Hạng khách</span><select value={classId} onChange={e => setClassId(e.target.value)}><option value="">Chọn hạng khách</option>{customerClasses.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        {(ticketKind === 'DAILY' || ticketKind === 'MONTHLY') && <label className="field"><span>Mã khu vực (nếu có nhiều gói)</span><input value={zoneId} onChange={e => setZoneId(e.target.value)} /></label>}
      </div>
    </div>}

    <div className="grid-2 scan-grid">
      <div className="card scan-video">
        <div className="scan-card-head">
          <div>
            <span className="card-kicker">LUỒNG HÌNH ẢNH</span>
            <h3>{translate("Ảnh / Video")}</h3>
          </div>
          <span className="scan-state">{inputMode === 'video' ? 'VIDEO MP4' : 'IMAGE JPEG/PNG'}</span>
        </div>
        {inputMode === 'video' ? (
          <VideoPlayer key={`${selectedLaneId}:${videoUrl || "empty"}`} videoUrl={videoUrl} bbox={result?.bbox ?? null} onFrameCaptured={onFrame} suspended={editingPlate || state === 'confirming' || Boolean(transactionId)} />
        ) : (
          <div className="stack" style={{ gap: 14 }}>
            {imageUrl ? (
              <DetectionImage key={imageUrl} src={imageUrl} bbox={result?.bbox ? { x: result.bbox[0], y: result.bbox[1], w: result.bbox[2] - result.bbox[0], h: result.bbox[3] - result.bbox[1] } : null} />
            ) : (
              <div className="video-placeholder" style={{ position: "relative", display: "grid", placeItems: "center" }}>
                <div className="bbox"><span>IMAGE READY</span></div>
                <span className="video-placeholder-caption">{translate("Chọn ảnh JPEG/PNG để bắt đầu.")}</span>
              </div>
            )}
            <div className="scan-controls">
              <button type="button" className="btn btn-primary" disabled={!imageFile || !selectedLaneId || state === 'detecting' || state === 'reading' || state === 'confirming' || Boolean(transactionId)} onClick={() => { if (imageFile) void onFrame(imageFile).catch(() => undefined); }}>{translate("Nhận diện ảnh")}</button>
            </div>
          </div>
        )}
      </div>

      <aside className="card scan-result">
        <div className="scan-card-head">
          <div>
            <span className="card-kicker">RECOGNITION OUTPUT</span>
            <h3>ALPR Result</h3>
            <p>{statusLabel[state]}</p>
          </div>
          <span className="scan-state">Status: {state.toUpperCase()}</span>
        </div>
        {transactionId && <p role="status" className="alert alert-success">Transaction: <strong>{transactionId}</strong></p>}
        <ResultPanel result={result} />
        <ConfirmationPanel key={result?.candidate_id ?? result?.detection_id ?? "none"} onEditingChange={setEditingPlate} disabled={state === 'detecting' || state === 'reading' || state === 'confirming' || Boolean(transactionId)} result={result} onConfirmCorrect={id => confirm(id)} onConfirmCorrection={(id, plate) => confirm(id, plate)} />
        <form className="stack" style={{ marginTop: 18, paddingTop: 16, borderTop: "1px solid #ead9bb", gap: 10 }} onSubmit={event => { event.preventDefault(); void confirmManual(); }}>
          <span className="card-kicker">MANUAL OVERRIDE</span>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 400 }}>{translate("Check-in thủ công")}</h3>
          {scopedLane && <label className="checkbox-row"><input type="checkbox" checked={useTicketCode} onChange={e => { setUseTicketCode(e.target.checked); manualKey.current = crypto.randomUUID(); }} /><span>Dùng mã vé thay biển số (xe đạp)</span></label>}
          <div className="field">
            <label htmlFor="manual-plate">{useTicketCode ? 'Mã vé' : translate("Biển số nhập tay")}</label>
            <input id="manual-plate" value={manualPlate} placeholder="29A12345" disabled={state === 'confirming' || Boolean(transactionId)} onChange={event => { setManualPlate(event.target.value); manualKey.current = crypto.randomUUID(); }} />
          </div>
          <div className="scan-result-actions" style={{ marginTop: 4 }}>
            <button type="submit" className="btn btn-primary btn-small" disabled={!selectedLaneId || manualPlate.replace(/[^a-z0-9]/gi, '').length < 3 || state === 'detecting' || state === 'reading' || state === 'confirming' || Boolean(transactionId)}>{translate("Tạo check-in")}</button>
            {transactionId && <button type="button" className="btn btn-small" onClick={() => { setTransactionId(null); setEditingPlate(false); setManualPlate(''); setActionError(null); manualKey.current = crypto.randomUUID(); clearCandidates(); reset(); }}>{translate("Xe tiếp theo")}</button>}
          </div>
        </form>
        <ErrorPanel error={error} onRetry={() => {
          setActionError(null);
          setEditingPlate(false);
          void retry().catch(() => undefined);
        }} />
      </aside>
    </div>

    <RecentHistory items={history} />
  </section>;
}
