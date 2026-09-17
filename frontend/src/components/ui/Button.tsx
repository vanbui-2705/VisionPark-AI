import type { ButtonHTMLAttributes } from 'react'

export function Button({
  children,
  variant = 'primary',
  loading = false,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; loading?: boolean }) {
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      data-variant={variant}
      className={`btn btn-${variant} ${props.className ?? ''}`}
    >
      {loading ? 'Đang xử lý...' : children}
    </button>
  )
}
