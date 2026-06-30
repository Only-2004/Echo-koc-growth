/**
 * SSE POST 客户端（M4-M6 闭环新增）
 *
 * 浏览器原生 EventSource 只支持 GET，但 Echo 三个 agent 的 SSE 端点都是 POST
 * （/api/onboarding/turn /api/strategy/submit /api/retro/load 等）。
 * 因此用 fetch + ReadableStream 自己解析 SSE 帧。
 *
 * SSE 帧格式（参考 https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events）：
 *   event: <name>\n
 *   data: <json>\n
 *   \n
 *
 * 不同 agent 用了不同的事件 key 名（onboarding/retro 内部 payload 用 type；strategy 用 event），
 * 这里只负责把 raw frame 解析成 { event, data } 给上层；语义解读交给具体 client。
 */

export interface SSEFrame {
  /** 事件名（来自 ``event:`` 行；缺省 ``message``）。*/
  event: string
  /** 事件数据（已 JSON.parse；解析失败时为原始字符串）。*/
  data: unknown
  /** 原始 data 字符串（便于上层 fallback 处理）。*/
  rawData: string
}

export interface PostSSEOptions {
  /** POST body；会自动 JSON.stringify。null/undefined 时不带 body。*/
  body?: unknown
  /** 取消信号；上层组件 unmount 时 abort。*/
  signal?: AbortSignal
  /** 额外 query string；忽略 undefined 值。*/
  query?: Record<string, string | number | boolean | undefined | null>
}

/**
 * 把 query object 拼成 ?a=1&b=foo（忽略 null/undefined）。
 */
function buildQueryString(query?: PostSSEOptions['query']): string {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null) continue
    params.set(k, String(v))
  }
  const s = params.toString()
  return s ? `?${s}` : ''
}

/**
 * POST 一个 SSE 端点，按帧 yield。
 *
 * @example
 * for await (const frame of postSSE('/api/onboarding/turn', { body: {...} })) {
 *   if (frame.event === 'message') handle(frame.data)
 * }
 */
export async function* postSSE(
  url: string,
  options: PostSSEOptions = {},
): AsyncGenerator<SSEFrame, void, void> {
  const fullUrl = url + buildQueryString(options.query)
  const init: RequestInit = {
    method: 'POST',
    headers: { Accept: 'text/event-stream' },
    signal: options.signal,
  }
  if (options.body !== undefined && options.body !== null) {
    init.headers = { ...init.headers, 'Content-Type': 'application/json' }
    init.body = JSON.stringify(options.body)
  }
  const resp = await fetch(fullUrl, init)
  if (!resp.ok || !resp.body) {
    throw new Error(`SSE POST ${fullUrl} 失败：${resp.status} ${resp.statusText}`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      // SSE 帧之间用空行分隔；这里支持 \n\n 和 \r\n\r\n。
      let sepIndex = -1
      while (
        (sepIndex = Math.min(
          ...['\n\n', '\r\n\r\n'].map((sep) => {
            const i = buffer.indexOf(sep)
            return i === -1 ? Number.POSITIVE_INFINITY : i
          }),
        )) !== Number.POSITIVE_INFINITY
      ) {
        const sepLen = buffer.startsWith('\r\n\r\n', sepIndex) ? 4 : 2
        const rawFrame = buffer.slice(0, sepIndex)
        buffer = buffer.slice(sepIndex + sepLen)
        const frame = parseFrame(rawFrame)
        if (frame) yield frame
      }
    }
    // tail（一般 SSE 服务器结束前都会发空行，但保险起见处理 buffer 残余）
    if (buffer.trim()) {
      const frame = parseFrame(buffer)
      if (frame) yield frame
    }
  } finally {
    try {
      reader.releaseLock()
    } catch {
      // 忽略；reader 可能已被 abort
    }
  }
}

function parseFrame(raw: string): SSEFrame | null {
  if (!raw.trim()) return null
  let event = 'message'
  const dataLines: string[] = []
  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith(':')) continue // SSE comment
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }
  const rawData = dataLines.join('\n')
  let parsed: unknown = rawData
  try {
    parsed = JSON.parse(rawData)
  } catch {
    // data 不是 JSON 也允许，原样返回
  }
  return { event, data: parsed, rawData }
}

/**
 * fetch JSON helper。统一错误格式。
 */
export async function fetchJson<T>(
  url: string,
  options: RequestInit & { query?: PostSSEOptions['query'] } = {},
): Promise<T> {
  const { query, ...init } = options
  const fullUrl = url + buildQueryString(query)
  let resp: Response
  try {
    resp = await fetch(fullUrl, init)
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[fetchJson] 网络/CORS 失败', { url: fullUrl, error: e })
    throw e
  }
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    // eslint-disable-next-line no-console
    console.error('[fetchJson] 非 2xx 响应', {
      url: fullUrl,
      status: resp.status,
      statusText: resp.statusText,
      body: text.slice(0, 1000),
    })
    throw new Error(`fetch ${fullUrl} 失败：${resp.status} ${resp.statusText} ${text}`)
  }
  return (await resp.json()) as T
}

// =====================================================================
// Retry 包装：LLM 连接失败时按指数退避重试，达到 maxRetries 抛 LlmConnectionError
// =====================================================================

/** 用户希望的错误类型：达到 max retry 仍失败 / fatal 中途中断。前端识别后显示「暂停 agent，请刷新重试」。*/
export class LlmConnectionError extends Error {
  attemptsTried: number
  cause?: Error
  constructor(message: string, attemptsTried: number, cause?: Error) {
    super(message)
    this.name = 'LlmConnectionError'
    this.attemptsTried = attemptsTried
    this.cause = cause
  }
}

export interface RetryAttemptInfo {
  /** 当前是第几次尝试（从 1 开始）。*/
  attempt: number
  /** 总尝试上限。*/
  max: number
  /** 上一次的错误（attempt > 1 时存在）。*/
  error?: Error
  /** 退避后下一次再试前的等待时长（ms）；最后一次没有 nextDelayMs。*/
  nextDelayMs?: number
}

export interface RetryConfig {
  /** max retry 次数（含第一次），默认 5。即最多发起 5 次请求。*/
  maxRetries?: number
  /** 第一次 retry 等待时间（指数退避基数），默认 1000ms；上限 16000ms。*/
  initialDelayMs?: number
  /** 每次 attempt 开始/失败时回调，UI 用来更新「正在重试 (n/5)」状态。*/
  onAttempt?: (info: RetryAttemptInfo) => void
}

const DEFAULT_MAX_RETRIES = 5

function backoffMs(attempt: number, base: number): number {
  return Math.min(base * Math.pow(2, attempt - 1), 16000)
}

/**
 * 包一层 retry 的 SSE：
 * - 仅在「0 帧失败」时 retry（避免 backend 状态机被推进两次后再请求重复）
 * - 中途失败（已 yield 过帧）直接抛错，由上层显示「连接中断，请重新提交」
 * - AbortError 不 retry（用户主动取消）
 */
export async function* postSSEWithRetry(
  url: string,
  options: PostSSEOptions = {},
  retry: RetryConfig = {},
): AsyncGenerator<SSEFrame, void, void> {
  const max = retry.maxRetries ?? DEFAULT_MAX_RETRIES
  const baseDelay = retry.initialDelayMs ?? 1000
  let lastError: Error | undefined

  for (let attempt = 1; attempt <= max; attempt++) {
    retry.onAttempt?.({ attempt, max, error: lastError })
    let received = 0
    try {
      for await (const frame of postSSE(url, options)) {
        received++
        yield frame
      }
      return
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') throw err
      lastError = err instanceof Error ? err : new Error(String(err))
      if (received > 0) {
        throw new LlmConnectionError(
          `SSE 中途中断（已收 ${received} 帧）：${lastError.message}`,
          attempt,
          lastError,
        )
      }
      if (attempt < max) {
        const delay = backoffMs(attempt, baseDelay)
        retry.onAttempt?.({ attempt, max, error: lastError, nextDelayMs: delay })
        await new Promise((r) => setTimeout(r, delay))
      }
    }
  }
  throw new LlmConnectionError(
    `LLM 连接失败（已重试 ${max} 次）`,
    max,
    lastError,
  )
}

/**
 * 包一层 retry 的 fetchJson；语义同 postSSEWithRetry，但简化（一次性请求）。
 */
export async function fetchJsonWithRetry<T>(
  url: string,
  options: RequestInit & { query?: PostSSEOptions['query'] } = {},
  retry: RetryConfig = {},
): Promise<T> {
  const max = retry.maxRetries ?? DEFAULT_MAX_RETRIES
  const baseDelay = retry.initialDelayMs ?? 1000
  let lastError: Error | undefined
  for (let attempt = 1; attempt <= max; attempt++) {
    retry.onAttempt?.({ attempt, max, error: lastError })
    try {
      return await fetchJson<T>(url, options)
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') throw err
      lastError = err instanceof Error ? err : new Error(String(err))
      if (attempt < max) {
        const delay = backoffMs(attempt, baseDelay)
        retry.onAttempt?.({ attempt, max, error: lastError, nextDelayMs: delay })
        await new Promise((r) => setTimeout(r, delay))
      }
    }
  }
  throw new LlmConnectionError(
    `LLM 连接失败（已重试 ${max} 次）`,
    max,
    lastError,
  )
}
