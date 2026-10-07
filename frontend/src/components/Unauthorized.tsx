import { t as translate } from "../lib/i18n"
export function Unauthorized() {
  return (
    <div style={{ padding: 24 }}>
      <h2>{translate("403 — Không đủ quyền")}</h2>
      <p>{translate("Bạn không có quyền truy cập trang này.")}</p>
      <a href="/station">{translate("Về Station")}</a>
    </div>
  )
}
