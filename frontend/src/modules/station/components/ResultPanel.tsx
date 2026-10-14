import { t as translate } from "../../../lib/i18n"
import type { DetectionResult } from "../types";
export default function ResultPanel({
  result
}: {
  result: DetectionResult | null;
}) {
  if (!result) return <div className="scan-result-empty">
    <strong>{translate("Kết quả")}</strong>
    <span>{translate("Chưa có kết quả nhận diện.")}</span>
  </div>;
  return <div className="result-fields">
    <div className="result-metric result-metric--plate">
      <span className="muted">{translate("Biển số:")}</span>
      <div className="plate"><strong>{result.normalized_plate_number ?? translate("Chưa đọc OCR")}</strong></div>
      {!result.normalized_plate_number && result.bbox && <p className="scan-manual-note">{translate("Đã phát hiện vùng biển số. Vui lòng xác nhận thủ công.")}</p>}
    </div>
    <div className="result-metric">
      <span className="muted">RAW OCR</span>
      <div>Raw: {result.raw_plate_number ?? "-"}</div>
    </div>
    <div className="result-metric">
      <span className="muted">CONFIDENCE</span>
      <div>Confidence: {(result.confidence * 100).toFixed(1)}%</div>
    </div>
    <div className="result-metric">
      <span className="muted">DETECTOR / OCR</span>
      <div>Detector: {result.detector_confidence == null ? "-" : `${(result.detector_confidence * 100).toFixed(1)}%`} · OCR: {result.ocr_confidence == null ? "-" : `${(result.ocr_confidence * 100).toFixed(1)}%`}</div>
    </div>
    <div className="result-metric">
      <span className="muted">COMBINED / QUALITY</span>
      <div>Combined: {result.combined_confidence == null ? "-" : `${(result.combined_confidence * 100).toFixed(1)}%`} · Quality: {result.quality_flags?.length ? result.quality_flags.join(", ") : "OK"}</div>
    </div>
    <div className="result-metric">
      <span className="muted">LATENCY</span>
      <div>Latency: {result.processing_time_ms} ms</div>
    </div>
    <div className="result-metric">
      <span className="muted">MODEL / PROVIDER</span>
      <div>Model: {result.model_version} · Provider: {result.provider ?? "-"}</div>
    </div>
  </div>;
}
