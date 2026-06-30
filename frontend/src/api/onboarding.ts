/**
 * /api/onboarding/* 客户端（M4 闭环）
 *
 * SSE 事件类型（与 backend ``OnboardingService.turn_stream`` 对齐）：
 *   - state.transition  { from, to }
 *   - message.delta     { text }
 *   - message.complete  { text, sources[] }
 *   - profile.tick      { patch }
 *   - finish.ready      { session_id }
 *   - error             { message }
 *
 * 注意：sse-starlette 把 ``yield {"event": evt["type"], ...}`` 落到 ``event:`` 行，
 * 但同时 data payload 里也带了原始 type 字段；前端两边都能用，这里以 frame.event 为准。
 */

import type { Profile, SourceTag } from '../types/agents'
import { fetchJsonWithRetry, postSSEWithRetry, type RetryConfig } from './sse'

export interface CandidateClaim {
  claim_id: string
  claim_text: string
  category: string
  proposed_state: string
}

export interface StartResponse {
  session_id: string
  state: string
  candidate_claims: CandidateClaim[]
}

export interface StateTransitionEvent {
  type: 'state.transition'
  from: string
  to: string
}

export interface MessageDeltaEvent {
  type: 'message.delta'
  text: string
}

export interface MessageCompleteEvent {
  type: 'message.complete'
  text?: string
  sources?: SourceTag[]
  [k: string]: unknown
}

export interface ProfileTickEvent {
  type: 'profile.tick'
  patch: Record<string, unknown>
}

export interface ThinkingDeltaEvent {
  type: 'thinking.delta'
  text: string
}

export interface ProfileReadyEvent {
  type: 'profile.ready'
  profile: Record<string, unknown>
}

export interface FinishReadyEvent {
  type: 'finish.ready'
  session_id: string
}

export interface OnboardingErrorEvent {
  type: 'error'
  message: string
}

export type OnboardingEvent =
  | StateTransitionEvent
  | MessageDeltaEvent
  | MessageCompleteEvent
  | ProfileTickEvent
  | ThinkingDeltaEvent
  | FinishReadyEvent
  | ProfileReadyEvent
  | OnboardingErrorEvent

export type FinalizeStreamEvent = ThinkingDeltaEvent | ProfileReadyEvent | OnboardingErrorEvent

export async function startOnboarding(
  retry?: RetryConfig,
): Promise<StartResponse> {
  return fetchJsonWithRetry<StartResponse>('/api/onboarding/start', { method: 'POST' }, retry)
}

export async function* turnOnboarding(
  body: { session_id: string; user_text?: string | null },
  signal?: AbortSignal,
  retry?: RetryConfig,
): AsyncGenerator<OnboardingEvent, void, void> {
  for await (const frame of postSSEWithRetry(
    '/api/onboarding/turn',
    { body, signal },
    retry,
  )) {
    if (frame.data && typeof frame.data === 'object') {
      yield frame.data as OnboardingEvent
    }
  }
}

export async function finalizeOnboarding(
  session_id: string,
  retry?: RetryConfig,
): Promise<Profile> {
  return fetchJsonWithRetry<Profile>(
    '/api/onboarding/finalize',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id }),
    },
    retry,
  )
}

export async function* finalizeOnboardingStream(
  session_id: string,
  signal?: AbortSignal,
  retry?: RetryConfig,
): AsyncGenerator<FinalizeStreamEvent, void, void> {
  for await (const frame of postSSEWithRetry(
    '/api/onboarding/finalize-stream',
    { body: { session_id }, signal },
    retry,
  )) {
    if (frame.data && typeof frame.data === 'object') {
      yield frame.data as FinalizeStreamEvent
    }
  }
}
