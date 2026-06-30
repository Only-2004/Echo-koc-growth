/**
 * 顶层 React ErrorBoundary。
 *
 * 渲染期任何子树抛错都会被这里捕获，调 reportError 上报，并显示一个降级 UI。
 * 不替代 window.onerror（事件回调里的错误走那条），只兜底 React 渲染异常。
 */

import { Component, type ErrorInfo, type ReactNode } from 'react'
import { reportError } from '../lib/clientErrorReporter'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    reportError({
      kind: 'boundary',
      message: error.message,
      stack: error.stack,
      extra: { componentStack: info.componentStack },
    })
  }

  private handleReload = (): void => {
    window.location.reload()
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-bg-1 text-fg-1 p-6">
          <div className="max-w-md w-full bg-bg-2 rounded-xl p-6 border border-bg-3">
            <h1 className="text-lg font-semibold mb-2">页面出现异常</h1>
            <p className="text-sm text-fg-2 mb-4">
              已自动上报。可以刷新重试；问题持续请把右上角时间戳告知开发。
            </p>
            <pre className="text-xs text-fg-2 bg-bg-1 rounded p-3 max-h-40 overflow-auto whitespace-pre-wrap break-all">
              {this.state.error.message}
            </pre>
            <button
              type="button"
              onClick={this.handleReload}
              className="mt-4 px-3 py-1.5 rounded-pill bg-accent text-white text-sm hover:opacity-90"
            >
              刷新
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
