import type { Lane } from "../types";
export type { Lane } from "../types";
type Props = {
  lanes: Lane[];
  selectedLaneId: string;
  onChange: (laneId: string) => void;
  disabled?: boolean;
};
export default function LaneSelector({
  lanes,
  selectedLaneId,
  onChange,
  disabled
}: Props) {
  const active = lanes.filter(lane => lane.active);
  return <label style={{
    display: "grid",
    gap: 6
  }} htmlFor="lane-select">
    <strong>Lane</strong>
    <select id="lane-select" aria-label="Lane" value={selectedLaneId} disabled={disabled} onChange={e => onChange(e.target.value)}>
      <option value="">-- Chọn Lane --</option>
      {active.map(lane => <option key={lane.id} value={lane.id}>{lane.name} - {lane.direction}</option>)}
    </select>
  </label>;
}
