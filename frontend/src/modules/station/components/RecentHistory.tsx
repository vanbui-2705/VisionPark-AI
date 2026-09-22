import type { RecentHistoryItem } from "../types";
export default function RecentHistory({
  items
}: {
  items: RecentHistoryItem[];
}) {
  return <div style={{
    marginTop: 18
  }}><h3>Recent History</h3>{items.length === 0 ? <p>Chưa có lượt xác nhận.</p> : <div style={{
      overflowX: "auto"
    }}><table style={{
        width: "100%",
        borderCollapse: "collapse"
      }}><thead><tr><th>Biển số</th><th>Kết quả</th><th>Thời gian</th></tr></thead>
      <tbody>{items.map(item => <tr key={item.id}><td>{item.plateNumber}</td><td>{item.accepted ? "Accepted" : "Corrected"}</td><td>{new Date(item.confirmedAt).toLocaleTimeString()}</td></tr>)}</tbody></table></div>}</div>;
}
