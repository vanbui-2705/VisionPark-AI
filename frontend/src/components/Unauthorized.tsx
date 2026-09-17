export function Unauthorized() {
  return (
    <div style={{ padding: 24 }}>
      <h2>403 — Không đủ quyền</h2>
      <p>Bạn không có quyền truy cập trang này.</p>
      <a href="/station">Về Station</a>
    </div>
  )
}
