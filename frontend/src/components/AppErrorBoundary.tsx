import type { ReactNode } from 'react'
import { Component } from 'react'

export class AppErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) {
    return { error }
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24 }}>
          <h2>Đã xảy ra lỗi</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{this.state.error.message}</pre>
          <button type="button" className="btn btn-primary" onClick={() => this.setState({ error: null })}>
            Thử lại
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
