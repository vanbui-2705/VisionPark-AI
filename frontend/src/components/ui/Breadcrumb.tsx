import { Link } from 'react-router-dom'

export function Breadcrumb({ items }: { items: { label: string; to?: string }[] }) {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      {items.map((it, i) => (
        <span key={i} className="crumb">
          {i > 0 ? <span className="crumb-sep">/</span> : null}
          {it.to ? <Link to={it.to}>{it.label}</Link> : <span className="crumb-current">{it.label}</span>}
        </span>
      ))}
    </nav>
  )
}
