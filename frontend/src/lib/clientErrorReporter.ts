/**
 * 前端异常上报。
 *
 * - install() 注册一次：window.onerror + unhandledrejection
 * - reportError() 给 ErrorBoundary / fetch 包装层显式调用
 *
 * 上报 fire-and-forget：失败只 console.warn，不递归抛错（避免炸锅）。
 */

const ENDPOINT = '/api/log/client-error'

export type ClientErrorKind = 'error' | 'unhandledrejection' | 'boundary' | 'fetch'

interface ReportPayload {
  kind: ClientErrorKind
  message: string
  stack?: string
  source?: string
  line?: number
  column?: number
  url?: string
  user_agent?: string
  extra?: Record<string, unknown>
}

let installed = false

export function reportError(payload: ReportPayload): void {
  // console 必发，便于本地 DevTools 即时排查
  // eslint-disable-next-line no-console
  console.error('[client-error]', payload)

  // 后端上报 fire-and-forget；失败再 console.warn，但不再抛
  try {
    const body = JSON.stringify({
      ...payload,
      url: payload.url ?? (typeof window !== 'undefined' ? window.location.href : undefined),
      user_agent: payload.user_agent ?? (typeof navigator !== 'undefined' ? navigator.userAgent : undefined),
    })

    if (typeof navigator !== 'undefined' && typeof navigator.sendEcho === 'function') {
      // sendEcho 在 unload / 切页时也能送到，最稳
      const ok = navigator.sendEcho(ENDPOINT, new Blob([body], { type: 'application/json' }))
      if (ok) return
    }
    void fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body,
      keepalive: true,
    }).catch((e) => {
      // eslint-disable-next-line no-console
      console.warn('[client-error] 上报失败', e)
    })
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('[client-error] 序列化失败', e)
  }
}

export function installGlobalErrorReporter(): void {
  if (installed || typeof window === 'undefined') return
  installed = true

  window.addEventListener('error', (ev: ErrorEvent) => {
    reportError({
      kind: 'error',
      message: ev.message ?? String(ev.error ?? 'unknown'),
      stack: ev.error instanceof Error ? ev.error.stack : undefined,
      source: ev.filename,
      line: ev.lineno,
      column: ev.colno,
    })
  })

  window.addEventListener('unhandledrejection', (ev: PromiseRejectionEvent) => {
    const reason = ev.reason
    const message = reason instanceof Error ? reason.message : String(reason)
    const stack = reason instanceof Error ? reason.stack : undefined
    reportError({ kind: 'unhandledrejection', message, stack })
  })
}
