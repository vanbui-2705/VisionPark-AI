import { t as translate } from "../../../lib/i18n"
import type { RecentHistoryItem } from "../types";
export default function RecentHistory({
  items
}: {
  items: RecentHistoryItem[];
}) {
  return <div style={{
    marginTop: 18
  }}><h3>Recent History</h3>{items.length === 0 ? <p>{translate("Chưa có lượt xác nhận.")}</p> : <div style={{
      overflowX: "auto"
    }}><table style={{
        width: "100%",
        borderCollapse: "collapse"
      }}><thead><tr><th>{translate("Biển số")}</th><th>{translate("Kết quả")}</th><th>{translate("Thời gian")}</th></tr></thead>
      <tbody>{items.map(item => <tr key={item.id}><td>{item.plateNumber}</td><td>{item.accepted ? "Accepted" : "Corrected"}</td><td>{new Date(item.confirmedAt).toLocaleTimeString()}</td></tr>)}</tbody></table></div>}</div>;
}
