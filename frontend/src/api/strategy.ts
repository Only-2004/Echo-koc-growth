/**
 * /api/strategy/* 客户端（M5 闭环）
 *
 * SSE 事件 key 用 ``event``（不同于 onboarding/retro 的 ``type``）：
 *   - state  { state, snapshot_id? }
 *   - delta  { text }
 *   - done   { snapshot_id, result }
 */

import type { SourceTag, StrategySnapshot } from '../types/agents'
import { fetchJsonWithRetry, postSSEWithRetry, type RetryConfig } from './sse'

export interface StrategyStateEvent {
  event: 'state'
  state: string
  snapshot_id?: string
}

export interface StrategyThinkingDeltaEvent {
  event: 'thinking.delta'
  text: string
}

export interface StrategyDeltaEvent {
  event: 'delta'
  text: string
}

export interface StrategyDoneEvent {
  event: 'done'
  snapshot_id: string
  result: Record<string, unknown>
}

export type StrategySubmitEvent =
  | StrategyStateEvent
  | StrategyThinkingDeltaEvent
  | StrategyDeltaEvent
  | StrategyDoneEvent

export interface RefineResult {
  snapshot_id: string
  feedback_type: 'challenge' | 'adjust' | 'approve' | string
  final_text: string
  sources: SourceTag[]
  persisted_version: number | null
}

export async function* submitStrategy(
  body: { idea_text: string; profile_id?: string | null },
  options: { signal?: AbortSignal; retry?: RetryConfig } = {},
): AsyncGenerator<StrategySubmitEvent, void, void> {
  for await (const frame of postSSEWithRetry(
    '/api/strategy/submit',
    {
      body,
      signal: options.signal,
    },
    options.retry,
  )) {
    if (frame.data && typeof frame.data === 'object') {
      yield frame.data as StrategySubmitEvent
    }
  }
}

export async function refineStrategy(
  body: { snapshot_id: string; user_text: string },
  retry?: RetryConfig,
): Promise<RefineResult> {
  return fetchJsonWithRetry<RefineResult>(
    '/api/strategy/refine',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    retry,
  )
}

export async function getStrategySnapshot(
  snapshot_id: string,
  version?: number,
  retry?: RetryConfig,
): Promise<StrategySnapshot> {
  const qs = version !== undefined ? `?version=${version}` : ''
  return fetchJsonWithRetry<StrategySnapshot>(
    `/api/strategy/snapshot/${snapshot_id}${qs}`,
    {},
    retry,
  )
}
