import { t as translate } from "../../lib/i18n"
export function Spinner({ label = translate("Đang tải...") }: { label?: string }) {
  return <div role="status" aria-label={label} className="spinner">{label}</div>
}
