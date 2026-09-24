import type { DetectionResult } from "../types";
export default function ResultPanel({
  result
}: {
  result: DetectionResult | null;
}) {
  if (!result) return <div><h3>Kết quả</h3><p>Chưa có kết quả nhận diện.</p></div>;
  return <div style={{
    marginTop: 16,
    padding: 14,
    border: "1px solid #666",
    borderRadius: 8
  }}>
    <h3>Kết quả</h3>
    <p>Biển số: <strong>{result.normalized_plate_number ?? "Không nhận diện"}</strong></p>
    <p>Raw: {result.raw_plate_number ?? "-"}</p>
    <p>Confidence: {(result.confidence * 100).toFixed(1)}%</p>
    <p>Latency: {result.processing_time_ms} ms</p>
    <p>Model: {result.model_version}</p>
  </div>;
}
