import { useId, type SelectHTMLAttributes } from 'react'

export function Select({
  label,
  children,
  error,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label?: string; error?: string }) {
  const generatedId = useId()
  const id = props.id ?? props.name ?? generatedId
  const errorId = error ? `${id}-error` : undefined
  return (
    <div className="field">
      {label ? <label htmlFor={id}>{label}</label> : null}
      <select id={id} {...props} aria-invalid={!!error} aria-describedby={errorId}>
        {children}
      </select>
      {error ? <span id={errorId} className="field-error">{error}</span> : null}
    </div>
  )
}
