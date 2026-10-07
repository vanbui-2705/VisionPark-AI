import { HistoryBrowser } from "../../components/HistoryBrowser"
export function DetectionHistoryPage({ admin = false }: { admin?: boolean }) { void admin; return <HistoryBrowser kind="detections" /> }
