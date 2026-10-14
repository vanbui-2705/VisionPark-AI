import { t as translate } from "../../../lib/i18n"
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
  return <label className="field scan-control-group" htmlFor="lane-select">
    <span>Lane</span>
    <span className="scan-select-wrap">
      <select id="lane-select" className="scan-select" aria-label="Lane" value={selectedLaneId} disabled={disabled} onChange={e => onChange(e.target.value)}>
        <option value="">{translate("-- Chọn Lane --")}</option>
        {active.map(lane => <option key={lane.id} value={lane.id}>{lane.name} - {lane.direction}</option>)}
      </select>
    </span>
  </label>;
}
