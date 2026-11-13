import { t as translate } from "../../lib/i18n"
import { useCallback, useEffect, useRef, useState } from "react";
import { clearCandidates, confirmDetection, confirmExitDetection, detectFire, getActiveLanes, getRecentHistory, manualCheckIn, prepareExit, type ExitSession, type FireSignalEvent, type PriceContext } from "./api";
import { apiClient } from '../../api/client.ts';
import LaneSelector from "./components/LaneSelector";
import VideoSelector from "./components/VideoSelector";
import VideoPlayer from "./components/VideoPlayer";
import ResultPanel from "./components/ResultPanel";
import ConfirmationPanel from "./components/ConfirmationPanel";
import RecentHistory from "./components/RecentHistory";
import ErrorPanel from "./components/ErrorPanel";
import ImageComparison from "./components/ImageComparison";
import ExitSummary from "./components/ExitSummary";
import FireAlert from "./components/FireAlert";
import { useStationShortcuts } from "./hooks/useStationShortcuts";
import { useAlprDetection } from "./hooks/useAlprDetection";
import type { ApiError, Lane, RecentHistoryItem } from "./types";
import { DetectionImage } from "../../components/DetectionImage";
import { useAuth } from "../auth/AuthContext";
import { can } from "../../lib/permissions";
export default function StationPage() {
  const { user } = useAuth();
  const mayReadTransactions = can(user, 'transactions.read');
  const mayCheckOut = can(user, 'checkout.create');
  const stationRoot = useRef<HTMLElement>(null);
  useStationShortcuts(stationRoot);
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
  const [exitSession, setExitSession] = useState<ExitSession | null>(null);
  const [exitBusy, setExitBusy] = useState(false);
  const [manualPlate, setManualPlate] = useState('');
  const [useTicketCode, setUseTicketCode] = useState(false);
  const [lostTicket, setLostTicket] = useState(false);
  const [customerClasses, setCustomerClasses] = useState<{ id: string; name: string }[]>([]);
  const [classId, setClassId] = useState('');
  const [vehicleType, setVehicleType] = useState('CAR');
  const [ticketKind, setTicketKind] = useState<PriceContext['ticket_kind']>('HOURLY');
  const [zoneId, setZoneId] = useState('');
  const [fireAlert, setFireAlert] = useState<FireSignalEvent | null>(null);
  const fireRequestBusy = useRef(false);
  const fireIncidentLatched = useRef(false);
  const fireMonitorGeneration = useRef(0);
  const selectedLane = lanes.find(lane => lane.id === selectedLaneId);
  const scopedLane = selectedLane?.building_id ? selectedLane : undefined;
  const isOut = selectedLane?.direction === 'OUT';
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
    completePreview,
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
    if (!buildingId || isOut) return;
    const controller = new AbortController();
    apiClient.get<{ id: string; name: string }[]>('/api/v1/pricing/customer-classes', { params: { building_id: buildingId }, signal: controller.signal })
      .then(items => { if (!controller.signal.aborted) { setCustomerClasses(items); if (items.length) setClassId(items[0].id); } })
      .catch(e => { if (!controller.signal.aborted) setActionError(e as ApiError); });
    return () => controller.abort();
  }, [scopedLane?.building_id, isOut]);
  useEffect(() => () => {
    if (videoUrl) URL.revokeObjectURL(videoUrl);
  }, [videoUrl]);
  useEffect(() => () => clearCandidates(), []);
  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl); }, [imageUrl]);
  const changeInput = (mode: 'image' | 'video') => {
    if (confirming.current) return;
    fireMonitorGeneration.current += 1; fireIncidentLatched.current = false; setFireAlert(null);
    setInputMode(mode); setImageFile(null); setImageUrl(''); setVideoUrl(''); setVideoName('');
    setTransactionId(null); setEditingPlate(false); setActionError(null);
    setExitSession(null);
    clearCandidates(); reset();
  };
  const chooseImage = (file: File | null) => {
    if (confirming.current) return;
    fireMonitorGeneration.current += 1; fireIncidentLatched.current = false; setFireAlert(null);
    setExitSession(null);
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
    fireMonitorGeneration.current += 1; fireIncidentLatched.current = false; setFireAlert(null);
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    setVideoUrl(url);
    setVideoName(file.name);
    setTransactionId(null);
    setExitSession(null);
    setEditingPlate(false);
    clearCandidates();
    reset();
  };
  const monitorFire = useCallback(async (image: Blob) => {
    if (!selectedLane || fireRequestBusy.current) return;
    fireRequestBusy.current = true;
    const generation = fireMonitorGeneration.current;
    try {
      const events = await detectFire(image, selectedLane.camera_id ?? selectedLane.id, selectedLane.building_id);
      if (generation !== fireMonitorGeneration.current) return;
      const event = events.reduce<FireSignalEvent | null>((highest, item) => !highest || item.confidence > highest.confidence ? item : highest, null);
      if (!event) {
        fireIncidentLatched.current = false;
        return;
      }
      if (fireIncidentLatched.current) return;
      fireIncidentLatched.current = true;
      setFireAlert(event);
    } catch {
      // Fire monitoring stays isolated from ALPR so a monitor outage cannot block a vehicle.
    } finally {
      fireRequestBusy.current = false;
    }
  }, [selectedLane]);
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
    void monitorFire(image);
    await detect(image, selectedLaneId, { inputKind: inputMode === 'image' ? 'IMAGE_UPLOAD' : 'VIDEO_FRAME', videoTimeMs });
  }, [detect, monitorFire, selectedLaneId, transactionId, inputMode]);
  const changeLane = (laneId: string) => {
    if (confirming.current) return;
    fireMonitorGeneration.current += 1; fireIncidentLatched.current = false; setFireAlert(null);
    const nextLane = lanes.find(lane => lane.id === laneId);
    if (nextLane?.building_id !== scopedLane?.building_id || nextLane?.direction === 'OUT') {
      setCustomerClasses([]); setClassId('');
    }
    setSelectedLaneId(laneId);
    setExitSession(null);
    setManualPlate('');
    setUseTicketCode(false);
    setLostTicket(false);
    setEditingPlate(false);
    setTransactionId(null);
    setActionError(null);
    manualKey.current = crypto.randomUUID();
    clearCandidates();
    reset();
  };
  const confirm = async (detectionId: string, plate?: string) => {
    if (confirming.current) return;
    if (isOut && !mayCheckOut) throw { status: 403, code: 'FORBIDDEN', message: 'Bạn không có quyền thu tiền và cho xe ra.' };
    if (!isOut && scopedLane && !priceContext) { setActionError({ status: 422, code: 'PRICE_CONTEXT_REQUIRED', message: 'Chọn hạng khách và loại vé trước khi check-in.' }); return; }
    confirming.current = true;

    setActionError(null);
    beginConfirm();
    try {
      if (isOut) {
        const confirmedPlate = plate ?? result?.normalized_plate_number ?? result?.raw_plate_number ?? '';
        const exitImageUrl = await confirmExitDetection(detectionId, selectedLaneId, confirmedPlate);
        const session = await prepareExit(selectedLaneId, confirmedPlate, exitImageUrl, undefined, { vehicleTypeOut: vehicleType });
        setExitSession(session); setTransactionId(session.session_id);
        completePreview();
        return;
      }
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
    if (isOut && !mayCheckOut) { setActionError({ status: 403, code: 'FORBIDDEN', message: 'Bạn không có quyền thu tiền và cho xe ra.' }); return; }
    if (!isOut && scopedLane && !priceContext) { setActionError({ status: 422, code: 'PRICE_CONTEXT_REQUIRED', message: 'Chọn hạng khách và loại vé trước khi check-in.' }); return; }
    confirming.current = true;
    beginConfirm();
    setActionError(null);
    try {
      if (isOut) {
        const session = await prepareExit(selectedLaneId, manualPlate, undefined, undefined, { useTicketCode, isLostTicket: lostTicket, vehicleTypeOut: vehicleType });
        setExitSession(session); setTransactionId(session.session_id);
        completePreview();
        return;
      }
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
    confirming: isOut ? 'Đang tra xe và tính phí…' : translate("Đang tạo check-in..."),
    preview_ready: 'Đã tìm thấy giao dịch. Chờ đối chiếu và xác nhận checkout.',
    success: isOut ? 'Checkout hoàn tất. Barrier mô phỏng đã mở.' : translate("Check-in thành công."),
    error: translate("Xử lý thất bại.")
  };
  const error = actionError ?? detectionError;
  const locked = state === 'confirming' || exitBusy;
  const nextVehicle = () => {
    if (confirming.current) return;
    setExitSession(null); setTransactionId(null); setEditingPlate(false); setManualPlate(''); setLostTicket(false);
    setActionError(null); manualKey.current = crypto.randomUUID(); clearCandidates(); reset();
  };
  const captureExitImage = () => {
    if (confirming.current) return;
    setExitSession(null); setTransactionId(null); setActionError(null);
    setInputMode('image'); setImageFile(null); setImageUrl('');
    clearCandidates(); reset();
  };
  return <section ref={stationRoot} className="stack scan-page">
    {fireAlert && <FireAlert event={fireAlert} laneName={selectedLane?.name ?? fireAlert.camera_id} onDismiss={() => setFireAlert(null)} />}
    <header className={`scan-hero${exitSession ? ' scan-hero--checkout' : ''}`}>
      <div className="scan-hero-copy">
        <span className="scan-kicker">TRẠM KIỂM SOÁT CỔNG</span>
        <h2>{exitSession ? 'Checkout xe ra' : translate("Trạm quét biển số")}</h2>
        <p>{statusLabel[state]}</p>
      </div>
      <div className="scan-hero-actions">
        <span className="scan-state">{isOut ? 'LÀN RA OUT' : 'LÀN VÀO IN'} · {state.toUpperCase()}</span>
      </div>
    </header>

    {!exitSession && <><div className="scan-toolbar">
      <label className="field scan-control-group">
        <span>{translate("Chế độ nhận diện")}</span>
        <span className="scan-select-wrap">
          <select className="scan-select" aria-label={translate("Chế độ nhận diện")} value={inputMode} disabled={locked} onChange={event => changeInput(event.target.value as 'image' | 'video')}>
            <option value="image">{translate("Ảnh JPEG/PNG")}</option>
            <option value="video">Video MP4</option>
          </select>
        </span>
      </label>
      <LaneSelector lanes={lanes} selectedLaneId={selectedLaneId} onChange={changeLane} disabled={state === "detecting" || state === "reading" || locked} />
      {inputMode === 'video' ? (
        <VideoSelector onVideoSelected={onVideo} disabled={locked} />
      ) : (
        <label className="field scan-control-group">
          <span>{translate("Ảnh đầu vào")}</span>
          <input aria-label={translate("Ảnh đầu vào")} type="file" accept="image/jpeg,image/png" disabled={locked} onChange={event => chooseImage(event.target.files?.[0] ?? null)} />
        </label>
      )}
      {videoName && <div className="scan-file-name">Video: <strong>{videoName}</strong></div>}
    </div>

    <p className="muted">Phím tắt: F2 chụp / nhận diện · F4 xác nhận biển số · F8 thu tiền và mở cổng · F10 mở cổng xe miễn phí / đã trả · F9 xe tiếp theo.</p></>}
    {isOut && !mayCheckOut && <p role="alert" className="alert alert-danger">Bạn không có quyền thu tiền và cho xe ra tại trạm.</p>}
    {!isOut && scopedLane && <div className="card card-polished">
      <div className="scan-card-head" style={{ marginBottom: 12 }}>
        <div>
          <span className="card-kicker">BIỂU PHÍ ÁP DỤNG</span>
          <h3>Thông tin tính phí</h3>
        </div>
      </div>
      <div className="form-grid">
        <label className="field"><span>Loại xe</span><select value={vehicleType} onChange={e => setVehicleType(e.target.value)}><option value="CAR">Ô tô</option><option value="MOTORBIKE">Xe máy</option><option value="BICYCLE">Xe đạp</option></select></label>
        <label className="field"><span>Loại vé</span><select value={ticketKind} onChange={e => setTicketKind(e.target.value as PriceContext['ticket_kind'])}><option value="HOURLY">Theo giờ</option><option value="DAILY">Ngày</option><option value="MONTHLY">Tháng</option><option value="NIGHT">Đêm</option></select></label>
        <label className="field"><span>Hạng khách</span><select value={classId} onChange={e => setClassId(e.target.value)}><option value="">Chọn hạng khách</option>{customerClasses.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        {(ticketKind === 'DAILY' || ticketKind === 'MONTHLY') && <label className="field"><span>Mã khu vực (nếu có nhiều gói)</span><input value={zoneId} onChange={e => setZoneId(e.target.value)} /></label>}
      </div>
    </div>}

    {exitSession ? <div className="grid-2 scan-grid station-checkout-grid">
      <ExitSummary key={exitSession.session_id} session={exitSession} onBusyChange={busy => { confirming.current = busy; setExitBusy(busy); }} onCompleted={() => { completeConfirm(); void refreshHistory(); }} onNext={nextVehicle} onRequireExitImage={captureExitImage} />
      <ImageComparison entryImage={exitSession.check_in_image_url} exitImage={exitSession.exit_image_url} plate={exitSession.license_plate ?? exitSession.ticket_code ?? 'Không có biển số'} />
    </div> : <div className="grid-2 scan-grid">
      <div className="card scan-video">
        <div className="scan-card-head">
          <div>
            <span className="card-kicker">LUỒNG HÌNH ẢNH</span>
            <h3>{translate("Ảnh / Video")}</h3>
          </div>
          <span className="scan-state">{inputMode === 'video' ? 'VIDEO MP4' : 'IMAGE JPEG/PNG'}</span>
        </div>
        {inputMode === 'video' ? (
          <VideoPlayer key={`${selectedLaneId}:${videoUrl || "empty"}`} videoUrl={videoUrl} bbox={result?.bbox ?? null} onFrameCaptured={onFrame} onMonitoringFrame={monitorFire} suspended={editingPlate || state === 'confirming' || Boolean(transactionId)} monitoringSuspended={Boolean(fireAlert)} />
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
              <button type="button" className="btn btn-primary" data-station-shortcut="capture" aria-keyshortcuts="F2" disabled={!imageFile || !selectedLaneId || state === 'detecting' || state === 'reading' || locked || Boolean(transactionId)} onClick={() => { if (imageFile) void onFrame(imageFile).catch(() => undefined); }}>{translate("Nhận diện ảnh")}</button>
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
        <ConfirmationPanel key={result?.candidate_id ?? result?.detection_id ?? "none"} onEditingChange={setEditingPlate} disabled={state === 'detecting' || state === 'reading' || locked || Boolean(transactionId) || (isOut && !mayCheckOut)} result={result} onConfirmCorrect={id => confirm(id)} onConfirmCorrection={(id, plate) => confirm(id, plate)} />
        <form className="stack" style={{ marginTop: 18, paddingTop: 16, borderTop: "1px solid #ead9bb", gap: 10 }} onSubmit={event => { event.preventDefault(); void confirmManual(); }}>
          <span className="card-kicker">MANUAL OVERRIDE</span>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 400 }}>{isOut ? 'Tra phiên xe ra' : translate("Check-in thủ công")}</h3>
          {scopedLane && <label className="checkbox-row"><input type="checkbox" checked={useTicketCode} onChange={e => { setUseTicketCode(e.target.checked); manualKey.current = crypto.randomUUID(); }} /><span>Dùng mã vé thay biển số (xe đạp)</span></label>}
          {isOut && <div className="form-grid">
            <label className="field"><span>Loại xe nhận diện lúc ra</span><select value={vehicleType} onChange={e => setVehicleType(e.target.value)}><option value="CAR">Ô tô</option><option value="MOTORBIKE">Xe máy</option><option value="BICYCLE">Xe đạp</option></select></label>
            <label className="checkbox-row"><input type="checkbox" checked={lostTicket} onChange={e => setLostTicket(e.target.checked)} /><span>Mất vé / thẻ (áp dụng phí mất vé)</span></label>
          </div>}
          <div className="field">
            <label htmlFor="manual-plate">{useTicketCode ? 'Mã vé' : translate("Biển số nhập tay")}</label>
            <input id="manual-plate" value={manualPlate} placeholder={useTicketCode ? 'BIKE-001' : '29A12345'} disabled={state === 'confirming' || Boolean(transactionId)} onChange={event => { setManualPlate(event.target.value); manualKey.current = crypto.randomUUID(); }} />
          </div>
          <div className="scan-result-actions" style={{ marginTop: 4 }}>
            <button type="submit" className="btn btn-primary btn-small" disabled={!selectedLaneId || manualPlate.replace(/[^a-z0-9]/gi, '').length < 3 || state === 'detecting' || state === 'reading' || locked || Boolean(transactionId) || (isOut && !mayCheckOut)}>{isOut ? 'Tra xe và tính phí' : translate("Tạo check-in")}</button>
            {transactionId && <button type="button" className="btn btn-small" data-station-shortcut="next" aria-keyshortcuts="F9" onClick={nextVehicle}>{translate("Xe tiếp theo")}</button>}
          </div>
        </form>
        <ErrorPanel error={error} onRetry={() => {
          setActionError(null);
          setEditingPlate(false);
          void retry().catch(() => undefined);
        }} />
      </aside>
    </div>}

    <RecentHistory items={history} />
  </section>;
}
