import { t as translate } from "../../../lib/i18n"
import type { DetectionResult } from "../types";
export default function ResultPanel({
  result
}: {
  result: DetectionResult | null;
}) {
  if (!result) return <div><h3>{translate("Kết quả")}</h3><p>{translate("Chưa có kết quả nhận diện.")}</p></div>;
  return <div style={{
    marginTop: 16,
    padding: 14,
    border: "1px solid #666",
    borderRadius: 8
  }}>
    <h3>{translate("Kết quả")}</h3>
    <p>{translate("Biển số:")}<strong>{result.normalized_plate_number ?? translate("Chưa đọc OCR")}</strong></p>
    {!result.normalized_plate_number && result.bbox && <p>{translate("Đã phát hiện vùng biển số. Vui lòng xác nhận thủ công.")}</p>}
    <p>Raw: {result.raw_plate_number ?? "-"}</p>
    <p>Confidence: {(result.confidence * 100).toFixed(1)}%</p>
    <p>Detector: {result.detector_confidence == null ? "-" : `${(result.detector_confidence * 100).toFixed(1)}%`}</p>
    <p>OCR: {result.ocr_confidence == null ? "-" : `${(result.ocr_confidence * 100).toFixed(1)}%`}</p>
    <p>Combined: {result.combined_confidence == null ? "-" : `${(result.combined_confidence * 100).toFixed(1)}%`}</p>
    <p>Quality: {result.quality_flags?.length ? result.quality_flags.join(", ") : "OK"}</p>
    <p>Latency: {result.processing_time_ms} ms</p>
    <p>Model: {result.model_version} · Provider: {result.provider ?? "-"}</p>
  </div>;
}
