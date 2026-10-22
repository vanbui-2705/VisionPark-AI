import { t as translate } from "../../../lib/i18n"
import type { RecentHistoryItem } from "../types";
export default function RecentHistory({
  items
}: {
  items: RecentHistoryItem[];
}) {
  return <div className="card scan-history">
    <div className="scan-card-head">
      <div>
        <span className="card-kicker">RECENT ACTIVITY</span>
        <h3>Recent History</h3>
      </div>
      <span className="scan-count">{items.length}</span>
    </div>
    {items.length === 0 ? <p className="muted">{translate("Chưa có lượt xác nhận.")}</p> : <div className="table-wrap scan-history-table">
      <table className="table">
        <thead>
          <tr>
            <th>{translate("Biển số")}</th>
            <th>{translate("Kết quả")}</th>
            <th>{translate("Thời gian")}</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => <tr key={item.id}>
            <td className="scan-plate-cell">{item.plateNumber}</td>
            <td>
              <span className={`scan-status ${item.accepted ? "scan-status--success" : "scan-status--warning"}`}>
                <span className="scan-status-dot" />
                {item.accepted ? "Accepted" : "Corrected"}
              </span>
            </td>
            <td>{new Date(item.confirmedAt).toLocaleTimeString()}</td>
          </tr>)}
        </tbody>
      </table>
    </div>}
  </div>;
}
