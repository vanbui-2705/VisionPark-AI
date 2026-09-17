import type { SelectHTMLAttributes } from 'react'

export function Select({
  label,
  children,
  error,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label?: string; error?: string }) {
  const id = props.id ?? props.name
  return (
    <div className="field">
      {label ? <label htmlFor={id}>{label}</label> : null}
      <select id={id} {...props}>
        {children}
      </select>
      {error ? <span className="field-error">{error}</span> : null}
    </div>
  )
}
