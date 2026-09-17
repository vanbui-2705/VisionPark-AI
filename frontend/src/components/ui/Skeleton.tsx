export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div aria-busy="true" style={{ display: 'grid', gap: 8 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton-line" style={{ height: 16 }} />
      ))}
    </div>
  )
}
