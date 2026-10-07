import { t as translate } from "../../../lib/i18n"
import { useState } from "react";
import type { DetectionResult } from "../types";
type Props = {
  result: DetectionResult | null;
  onConfirmCorrect: (id: string) => Promise<void>;
  onConfirmCorrection: (id: string, plate: string) => Promise<void>;
  disabled?: boolean;
  onEditingChange?: (editing: boolean) => void;

};
export default function ConfirmationPanel({
  result,
  onConfirmCorrect,
  onConfirmCorrection,
  disabled = false,
  onEditingChange
}: Props) {
  const [editing, setEditing] = useState(false);
  const [plate, setPlate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [completed, setCompleted] = useState(false);
  if (!result) return null;
  const run = async (fn: () => Promise<void>, success: string) => {
    setSubmitting(true);
    setMessage("");
    try {
      await fn();
      setCompleted(true);
      setMessage(success);
      setEditing(false);
      onEditingChange?.(false);
    } catch {
      setMessage(translate("Xác nhận thất bại."));
    } finally {
      setSubmitting(false);
    }
  };
  const normalized = plate.trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
  const canAccept = Boolean(result.normalized_plate_number);
  const candidateId = result.candidate_id ?? result.detection_id;
  const locked = submitting || disabled || completed || !candidateId;
  return <div style={{
    marginTop: 16,
    padding: 14,
    border: "1px solid #666",
    borderRadius: 8
  }}><h3>Operator Confirmation</h3>
    <p>AI: <strong>{result.normalized_plate_number ?? result.raw_plate_number ?? translate("Không có biển số")}</strong></p>
    <div style={{
      display: "flex",
      gap: 8,
      flexWrap: "wrap"
    }}>
      <button type="button" disabled={locked || !canAccept} onClick={() => void run(() => onConfirmCorrect(candidateId!), translate("Đã xác nhận biển số."))}>{translate("✓ Biển số đúng")}</button>
      <button type="button" disabled={locked} onClick={() => { setEditing(true); onEditingChange?.(true); }}>{translate("✎ Sai / Không có biển")}</button>
    </div>
    {editing && <div style={{
      marginTop: 10
    }}><label htmlFor="corrected-plate">{translate("Biển số chính xác")}</label><input id="corrected-plate" value={plate} onChange={e => setPlate(e.target.value)} placeholder="29A12345" />
      <button type="button" disabled={locked || normalized.length < 3} onClick={() => void run(() => onConfirmCorrection(candidateId!, normalized), `Đã sửa thành ${normalized}.`)}>{translate("Xác nhận sửa")}</button>
      <button type="button" disabled={submitting || disabled} onClick={() => { setEditing(false); onEditingChange?.(false); }}>{translate("Hủy sửa")}</button></div>}
    {submitting && <p>{translate("Đang gửi xác nhận...")}</p>}{message && <p role="status">{message}</p>}
  </div>;
}
