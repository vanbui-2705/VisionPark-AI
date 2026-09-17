import type { InputHTMLAttributes } from 'react'

export function Input({
  label,
  error,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string }) {
  const id = props.id ?? props.name
  return (
    <div className="field">
      {label ? <label htmlFor={id}>{label}</label> : null}
      <input id={id} {...props} aria-invalid={!!error} />
      {error ? <span className="field-error">{error}</span> : null}
    </div>
  )
}
