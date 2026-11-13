import { t as translate } from "../../../lib/i18n"
import { useCallback, useEffect, useRef, useState } from "react";
import BBoxOverlay from "./BBoxOverlay";
type Props = {
  videoUrl: string;
  bbox?: [number, number, number, number] | null;
  onFrameCaptured?: (image: Blob, videoTimeMs?: number) => Promise<void>;
  onMonitoringFrame?: (image: Blob) => Promise<void>;
  suspended?: boolean;
  monitoringSuspended?: boolean;
};
export default function VideoPlayer({
  videoUrl,
  bbox = null,
  onFrameCaptured,
  onMonitoringFrame,
  suspended = false,
  monitoringSuspended = false
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const monitoringCanvasRef = useRef<HTMLCanvasElement>(null);
  const busyRef = useRef(false);
  const monitoringBusyRef = useRef(false);
  const [ended, setEnded] = useState(false);
  const [intervalMs, setIntervalMs] = useState(1000);
  const [auto, setAuto] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [count, setCount] = useState(0);
  const [mediaError, setMediaError] = useState(false);
  const [size, setSize] = useState({
    width: 0,
    height: 0
  });
  const captureFrame = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2 || busyRef.current || suspended) return;
    busyRef.current = true;
    setProcessing(true);
    try {
      const videoTimeMs = Math.round(video.currentTime * 1000);
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext("2d");
      if (!context) throw new Error(translate("Canvas 2D không khả dụng."));
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error(translate("Không tạo được JPEG."))), "image/jpeg", 0.9));
      setCount(value => value + 1);
      await onFrameCaptured?.(blob, videoTimeMs);
    } catch {
      // The Station owns API errors; a rejected capture must not escape the timer.
    } finally {
      busyRef.current = false;
      setProcessing(false);
    }
  }, [onFrameCaptured, suspended]);
  const captureMonitoringFrame = useCallback(async () => {
    const video = videoRef.current;
    const canvas = monitoringCanvasRef.current;
    if (!video || !canvas || video.readyState < 2 || video.videoWidth < 1 || video.videoHeight < 1 || video.paused || video.ended || monitoringBusyRef.current || monitoringSuspended || !onMonitoringFrame) return;
    monitoringBusyRef.current = true;
    try {
      const width = Math.min(video.videoWidth, 640);
      const height = Math.max(1, Math.round(video.videoHeight * (width / video.videoWidth)));
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) return;
      context.drawImage(video, 0, 0, width, height);
      const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error("Không tạo được frame giám sát.")), "image/jpeg", 0.75));
      await onMonitoringFrame(blob);
    } catch {
      // Fire monitoring is secondary and must never interrupt the Station flow.
    } finally {
      monitoringBusyRef.current = false;
    }
  }, [monitoringSuspended, onMonitoringFrame]);
  useEffect(() => {
    if (!auto || !videoUrl || suspended) return;
    const id = window.setInterval(() => void captureFrame(), intervalMs);
    return () => window.clearInterval(id);
  }, [auto, intervalMs, videoUrl, captureFrame, suspended]);
  useEffect(() => {
    if (!videoUrl || !onMonitoringFrame || monitoringSuspended) return;
    const id = window.setInterval(() => void captureMonitoringFrame(), 2500);
    return () => window.clearInterval(id);
  }, [videoUrl, onMonitoringFrame, monitoringSuspended, captureMonitoringFrame]);
  if (!videoUrl) return <div className="video-placeholder" style={{ position: "relative", display: "grid", placeItems: "center", marginTop: 16 }}>
    <div className="bbox"><span>ALPR READY</span></div>
    <span className="video-placeholder-caption">{translate("Chọn video MP4 để bắt đầu.")}</span>
  </div>;
  return <div style={{ marginTop: 16 }}>
    <div style={{
      position: "relative",
      width: "100%",
      background: "#181d26",
      borderRadius: 8,
      overflow: "hidden",
      border: "1px solid #33404a"
    }}>
      <video ref={videoRef} src={videoUrl} style={{
        display: "block",
        width: "100%",
        maxHeight: "65vh"
      }} onLoadedMetadata={() => {
        const v = videoRef.current;
        if (v) setSize({
          width: v.videoWidth,
          height: v.videoHeight
        });
      }} onError={() => { setMediaError(true); setAuto(false); }} onEnded={() => {
        setEnded(true);
        setAuto(false);
      }} onPlay={() => setEnded(false)} onPause={() => setAuto(false)} />
      <BBoxOverlay bbox={bbox} sourceWidth={size.width} sourceHeight={size.height} />
    </div>
    <div className="scan-controls">
      <button type="button" className="btn btn-small" disabled={mediaError} onClick={() => void videoRef.current?.play().catch(() => { setMediaError(true); setAuto(false); })}>Play</button>
      <button type="button" className="btn btn-small" onClick={() => videoRef.current?.pause()}>Pause</button>
      <button type="button" className="btn btn-small" onClick={() => {
        const v = videoRef.current;
        if (!v) return;
        v.currentTime = 0;
        setEnded(false);
        void v.play();
      }}>Replay</button>
      <button type="button" className="btn btn-primary btn-small" data-station-shortcut="capture" aria-keyshortcuts="F2" disabled={processing || suspended || mediaError} onClick={() => void captureFrame()}>Capture Frame</button>
    </div>
    <div className="scan-controls" style={{ alignItems: "center", borderTop: 0, paddingTop: 4, marginTop: 8 }}>
      <label className="field" style={{ display: "inline-flex", flexDirection: "row", alignItems: "center", gap: 8, margin: 0 }}>
        <span>Interval (ms)</span>
        <input aria-label="Capture interval" type="number" min={250} step={250} value={intervalMs} style={{ width: 110, minHeight: 36 }} onChange={e => setIntervalMs(Math.max(250, Number(e.target.value) || 1000))} />
      </label>
      <button type="button" className="btn btn-small" disabled={mediaError} onClick={() => setAuto(value => !value)}>{auto ? "Stop Auto Capture" : "Start Auto Capture"}</button>
    </div>
    {mediaError && <p role="alert" className="alert alert-danger" style={{ marginTop: 10 }}>{translate("Không thể đọc video. Kiểm tra file/codec hoặc thử trình duyệt khác.")}</p>}
    <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>{processing ? translate("Đang xử lý frame...") : translate("Sẵn sàng")} · Captures: {count}{ended ? " · EOF" : ""}</p>
    <canvas ref={canvasRef} hidden />
    <canvas ref={monitoringCanvasRef} hidden />
  </div>;
}
