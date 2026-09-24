import { useState } from "react";
import type { DetectionResult } from "../types";
type Props = {
  result: DetectionResult | null;
  onConfirmCorrect: (id: string) => Promise<void>;
  onConfirmCorrection: (id: string, plate: string) => Promise<void>;
};
export default function ConfirmationPanel({
  result,
  onConfirmCorrect,
  onConfirmCorrection
}: Props) {
  const [editing, setEditing] = useState(false);
  const [plate, setPlate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  if (!result) return null;
  const run = async (fn: () => Promise<void>, success: string) => {
    setSubmitting(true);
    setMessage("");
    try {
      await fn();
      setMessage(success);
      setEditing(false);
    } catch {
      setMessage("Xác nhận thất bại.");
    } finally {
      setSubmitting(false);
    }
  };
  const normalized = plate.trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
  return <div style={{
    marginTop: 16,
    padding: 14,
    border: "1px solid #666",
    borderRadius: 8
  }}><h3>Operator Confirmation</h3>
    <p>AI: <strong>{result.normalized_plate_number ?? result.raw_plate_number ?? "Không có biển số"}</strong></p>
    <div style={{
      display: "flex",
      gap: 8,
      flexWrap: "wrap"
    }}>
      <button type="button" disabled={submitting} onClick={() => void run(() => onConfirmCorrect(result.detection_id), "Đã xác nhận biển số.")}>✓ Biển số đúng</button>
      <button type="button" disabled={submitting} onClick={() => setEditing(true)}>✎ Sai / Không có biển</button>
    </div>
    {editing && <div style={{
      marginTop: 10
    }}><label htmlFor="corrected-plate">Biển số chính xác </label><input id="corrected-plate" value={plate} onChange={e => setPlate(e.target.value)} placeholder="29A12345" />
      <button type="button" disabled={submitting || !normalized} onClick={() => void run(() => onConfirmCorrection(result.detection_id, normalized), `Đã sửa thành ${normalized}.`)}>Xác nhận sửa</button></div>}
    {submitting && <p>Đang gửi xác nhận...</p>}{message && <p role="status">{message}</p>}
  </div>;
}
