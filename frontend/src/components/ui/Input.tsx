import { useId, type InputHTMLAttributes } from 'react'

export function Input({
  label,
  error,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string }) {
  const generatedId = useId()
  const id = props.id ?? props.name ?? generatedId
  const errorId = error ? `${id}-error` : undefined
  return (
    <div className="field">
      {label ? <label htmlFor={id}>{label}</label> : null}
      <input id={id} {...props} aria-invalid={!!error} aria-describedby={errorId} />
      {error ? <span id={errorId} className="field-error">{error}</span> : null}
    </div>
  )
}
