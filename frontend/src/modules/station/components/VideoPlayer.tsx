import { useCallback, useEffect, useRef, useState } from "react";
import BBoxOverlay from "./BBoxOverlay";
type Props = {
  videoUrl: string;
  bbox?: [number, number, number, number] | null;
  onFrameCaptured?: (image: Blob) => Promise<void>;
};
export default function VideoPlayer({
  videoUrl,
  bbox = null,
  onFrameCaptured
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const busyRef = useRef(false);
  const [ended, setEnded] = useState(false);
  const [intervalMs, setIntervalMs] = useState(1000);
  const [auto, setAuto] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [count, setCount] = useState(0);
  const [size, setSize] = useState({
    width: 0,
    height: 0
  });
  const captureFrame = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2 || busyRef.current) return;
    busyRef.current = true;
    setProcessing(true);
    try {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Canvas 2D không khả dụng.");
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error("Không tạo được JPEG.")), "image/jpeg", 0.9));
      setCount(value => value + 1);
      await onFrameCaptured?.(blob);
    } finally {
      busyRef.current = false;
      setProcessing(false);
    }
  }, [onFrameCaptured]);
  useEffect(() => {
    if (!auto || !videoUrl) return;
    const id = window.setInterval(() => void captureFrame(), intervalMs);
    return () => window.clearInterval(id);
  }, [auto, intervalMs, videoUrl, captureFrame]);
  if (!videoUrl) return <div style={{
    marginTop: 16,
    padding: 30,
    border: "1px dashed #777",
    textAlign: "center"
  }}>Chọn video MP4 để bắt đầu.</div>;
  return <div style={{
    marginTop: 16
  }}>
    <div style={{
      position: "relative",
      width: "100%",
      background: "#111"
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
      }} onEnded={() => {
        setEnded(true);
        setAuto(false);
      }} onPlay={() => setEnded(false)} />
      <BBoxOverlay bbox={bbox} sourceWidth={size.width} sourceHeight={size.height} />
    </div>
    <div style={{
      display: "flex",
      gap: 8,
      flexWrap: "wrap",
      marginTop: 10
    }}>
      <button type="button" onClick={() => void videoRef.current?.play()}>Play</button>
      <button type="button" onClick={() => videoRef.current?.pause()}>Pause</button>
      <button type="button" onClick={() => {
        const v = videoRef.current;
        if (!v) return;
        v.currentTime = 0;
        setEnded(false);
        void v.play();
      }}>Replay</button>
      <button type="button" disabled={processing} onClick={() => void captureFrame()}>Capture Frame</button>
    </div>
    <div style={{
      display: "flex",
      gap: 8,
      alignItems: "center",
      flexWrap: "wrap",
      marginTop: 10
    }}>
      <label>Interval (ms) <input aria-label="Capture interval" type="number" min={250} step={250} value={intervalMs} onChange={e => setIntervalMs(Math.max(250, Number(e.target.value) || 1000))} /></label>
      <button type="button" onClick={() => setAuto(value => !value)}>{auto ? "Stop Auto Capture" : "Start Auto Capture"}</button>
    </div>
    <p>{processing ? "Đang xử lý frame..." : "Sẵn sàng"} · Captures: {count}{ended ? " · EOF" : ""}</p>
    <canvas ref={canvasRef} hidden />
  </div>;
}
