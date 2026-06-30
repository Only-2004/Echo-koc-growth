/**
 * /api/orchestrator/chat 客户端（M7 闭环）
 *
 * SSE 事件类型（与 backend ``/api/orchestrator/chat`` 路由对齐，
 * 见 backend/api/orchestrator.py 模块 docstring）：
 *   - route   { decision: { intent, needs_slices, tone, expect_suggestions } }
 *   - delta   { delta }
 *   - done    { sources, suggestions, used_fallback }
 *   - error   { message }
 *
 * route 事件主要供调试，前端可不消费；只要看到 done 即认为本轮完成。
 */

import { postSSEWithRetry, type RetryConfig } from './sse'

export type Scene = 'home' | 'onboard' | 'profile' | 'ideate' | 'retro'

export interface ChatTurnPayload {
  role: 'user' | 'ai' | 'system'
  text: string
  sources?: string[]
  suggestions?: string[]
}

export interface OrchestratorChatRequestPayload {
  scene: Scene
  user_text: string
  chat_history?: ChatTurnPayload[]
  focused_element?: Record<string, unknown> | null
}

export interface OrchestratorRouteEvent {
  type: 'route'
  decision: {
    intent: 'data_request' | 'clarification' | 'chitchat' | 'action'
    needs_slices: Array<'profile' | 'strategy' | 'retro'>
    tone: 'concise' | 'explainer' | 'encouraging'
    expect_suggestions: boolean
  }
}

export interface OrchestratorDeltaEvent {
  type: 'delta'
  delta: string
}

export interface OrchestratorDoneEvent {
  type: 'done'
  sources: string[]
  suggestions: string[]
  used_fallback: boolean
}

export interface OrchestratorErrorEvent {
  type: 'error'
  message: string
}

export type OrchestratorChatEvent =
  | OrchestratorRouteEvent
  | OrchestratorDeltaEvent
  | OrchestratorDoneEvent
  | OrchestratorErrorEvent

/**
 * 调 orchestrator chat，逐事件 yield。
 *
 * 与 retro/drill 一致用 postSSEWithRetry，因此自动继承 retry / LlmConnectionError 处理。
 */
export async function* chatOrchestrator(
  body: OrchestratorChatRequestPayload,
  signal?: AbortSignal,
  retry?: RetryConfig,
): AsyncGenerator<OrchestratorChatEvent, void, void> {
  // 默认 chat_history=[]，focused_element=null
  const fullBody: OrchestratorChatRequestPayload = {
    chat_history: [],
    focused_element: null,
    ...body,
  }
  for await (const frame of postSSEWithRetry(
    '/api/orchestrator/chat',
    { body: fullBody, signal },
    retry,
  )) {
    if (frame.data && typeof frame.data === 'object') {
      yield frame.data as OrchestratorChatEvent
    }
  }
}
