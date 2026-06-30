/**
 * /api/retro/* 客户端（M6 闭环）
 *
 * SSE 事件类型（与 backend ``retro/load`` 路由对齐）：
 *   - stage    { stage, status }
 *   - report   { report_id, draft }   ← draft 是 InsightsReport 的 dict（含 strategy_review/insights/audience_signals）
 *   - present  { delta }
 *   - drill    { delta }              ← /drill 端点
 *   - done     {}
 *   - error    { message }
 */

import type { InsightsReport } from '../types/agents'
import { fetchJsonWithRetry, postSSEWithRetry, type RetryConfig } from './sse'

export interface RetroStageEvent {
  type: 'stage'
  stage: string
  status: string
}

export interface RetroReportEvent {
  type: 'report'
  report_id: string
  draft: Record<string, unknown>
}

export interface RetroPresentEvent {
  type: 'present'
  delta: string
}

export interface RetroDrillEvent {
  type: 'drill'
  delta: string
}

export interface RetroDoneEvent {
  type: 'done'
}

export interface RetroErrorEvent {
  type: 'error'
  message: string
}

export interface RetroProfileUpdatedEvent {
  type: 'profile_updated'
  profile_version_out: number
}

export interface RetroThinkingDeltaEvent {
  type: 'thinking.delta'
  text: string
}

export type RetroLoadEvent =
  | RetroStageEvent
  | RetroReportEvent
  | RetroPresentEvent
  | RetroDoneEvent
  | RetroErrorEvent
  | RetroThinkingDeltaEvent

export type RetroDrillStreamEvent =
  | RetroDrillEvent
  | RetroDoneEvent
  | RetroErrorEvent
  | RetroProfileUpdatedEvent

export async function* loadRetro(
  video_id: string,
  options: { signal?: AbortSignal; retry?: RetryConfig } = {},
): AsyncGenerator<RetroLoadEvent, void, void> {
  for await (const frame of postSSEWithRetry(
    `/api/retro/load/${video_id}`,
    {
      signal: options.signal,
    },
    options.retry,
  )) {
    if (frame.data && typeof frame.data === 'object') {
      yield frame.data as RetroLoadEvent
    }
  }
}

export async function* drillRetro(
  body: {
    report_id: string
    user_text: string
    element_id?: string
    element_type?: string
  },
  signal?: AbortSignal,
  retry?: RetryConfig,
): AsyncGenerator<RetroDrillStreamEvent, void, void> {
  const fullBody = {
    element_id: 'dc_completion',
    element_type: 'data_card',
    ...body,
  }
  for await (const frame of postSSEWithRetry(
    '/api/retro/drill',
    { body: fullBody, signal },
    retry,
  )) {
    if (frame.data && typeof frame.data === 'object') {
      yield frame.data as RetroDrillStreamEvent
    }
  }
}

export interface UpdateProfileResult {
  ok: boolean
  report_id: string
  profile_version_out: number
  profile_path: string
  report_path: string
  delta_summary: {
    add_evidence: number
    promote: number
    new_observations: number
  }
}

export async function updateProfileFromRetro(
  body: { report_id: string; profile_version_in: number },
  retry?: RetryConfig,
): Promise<UpdateProfileResult> {
  return fetchJsonWithRetry<UpdateProfileResult>(
    '/api/retro/update-profile',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    retry,
  )
}

export async function getRetroReport(
  report_id: string,
  retry?: RetryConfig,
): Promise<InsightsReport> {
  return fetchJsonWithRetry<InsightsReport>(`/api/retro/report/${report_id}`, {}, retry)
}

/**
 * 触发后台预分析（fire-and-forget）。
 * 后台任务挂载在服务器 asyncio 事件循环，切页面不会中断。
 * 进入 retro 页时调用一次即可（仅在 ``USE_CACHED_ANALYSIS=false`` 下有意义；缓存模式可跳过）。
 */
export async function prefetchRetroAnalysis(): Promise<void> {
  try {
    await fetch('/api/retro/prefetch', { method: 'POST' })
  } catch {
    // 预加载失败不影响主流程
  }
}
