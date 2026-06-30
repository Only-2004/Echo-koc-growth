/**
 * useChatSend — 统一的 chat send hook（M4-M7 闭环）
 *
 * 让 ChatDock 自己发 + 任意 view 通过 useOnAsk 触发，都走同一段逻辑：
 *   - scene=ideate + snapshotId → POST /api/strategy/refine
 *   - scene=retro  + reportId   → SSE  /api/retro/drill
 *   - 其他全部                  → SSE  /api/orchestrator/chat（M7 兜底）
 *
 * orchestrator 路径同时处理 home / onboard / profile 三个 scene，
 * 也接 ideate / retro 在尚未生成 snapshot/report 时的追问。
 *
 * 返回 { send, sending, retryStatus, paused }；调用 send(text) 即触发完整流程。
 */

import { useCallback, useState } from 'react'
import { chatOrchestrator, type ChatTurnPayload } from '../../api/orchestrator'
import { getProfileByVersion } from '../../api/profile'
import { drillRetro } from '../../api/retro'
import { LlmConnectionError, type RetryAttemptInfo } from '../../api/sse'
import { refineStrategy } from '../../api/strategy'
import { getFallbackForScene } from '../../lib/fallbackResponses'
import { useAppStore } from '../../store/app'
import type { SourceTag } from '../../types/agents'

export function useChatSend(): {
  send: (text: string) => Promise<void>
  sending: boolean
  retryStatus: RetryAttemptInfo | null
  paused: boolean
} {
  const [sending, setSending] = useState(false)
  const [retryStatus, setRetryStatus] = useState<RetryAttemptInfo | null>(null)
  const [paused, setPaused] = useState(false)

  const onAttempt = (info: RetryAttemptInfo) => {
    if (info.attempt === 1 && !info.error) setRetryStatus(null)
    else setRetryStatus(info)
  }

  const send = useCallback(async (rawText: string) => {
    const text = rawText.trim()
    if (!text) return
    if (sending) return

    const state = useAppStore.getState()
    const scene = state.scene
    const snapshotId = state.snapshotId
    const reportId = state.reportId
    const appendChatTurn = state.appendChatTurn
    const updateLastAiMessage = state.updateLastAiMessage

    appendChatTurn(scene, { role: 'user', text })
    setSending(true)

    try {
      if (scene === 'ideate' && snapshotId) {
        appendChatTurn(scene, { role: 'ai', text: '', pending: true })
        const result = await refineStrategy(
          { snapshot_id: snapshotId, user_text: text },
          { onAttempt },
        )
        setRetryStatus(null)
        updateLastAiMessage(scene, (m) => ({
          ...m,
          text: result.final_text,
          sources: result.sources,
          pending: false,
        }))
        if (result.persisted_version !== null) {
          appendChatTurn(scene, {
            role: 'system',
            text: `已写入 strategy_snapshot v${result.persisted_version}`,
          })
        }
      } else if (scene === 'retro' && reportId) {
        appendChatTurn(scene, { role: 'ai', text: '', pending: true })
        let buffer = ''
        for await (const ev of drillRetro(
          { report_id: reportId, user_text: text },
          undefined,
          { onAttempt },
        )) {
          if (ev.type === 'drill') {
            buffer += ev.delta
            updateLastAiMessage(scene, (m) => ({ ...m, text: buffer }))
          } else if (ev.type === 'profile_updated') {
            try {
              const newProfile = await getProfileByVersion(ev.profile_version_out)
              useAppStore.getState().setProfile(newProfile)
              appendChatTurn(scene, {
                role: 'system',
                text: `画像已更新到 v${ev.profile_version_out}`,
              })
            } catch {
              // 更新失败不中断主流程，静默忽略
            }
          } else if (ev.type === 'done') {
            updateLastAiMessage(scene, (m) => ({ ...m, pending: false }))
          } else if (ev.type === 'error') {
            updateLastAiMessage(scene, (m) => ({
              ...m,
              text: buffer + `\n\n（${ev.message}）`,
              pending: false,
            }))
          }
        }
        setRetryStatus(null)
        updateLastAiMessage(scene, (m) => ({ ...m, pending: false }))
      } else {
        // M7 兜底：调 orchestrator chat（home / onboard / profile / ideate-no-snapshot / retro-no-report）
        const chatLog = state.chatLog[scene]
        // 把当前 chatLog 转成后端约定的 ChatTurn schema；user 这一轮已 append 在前面
        const history: ChatTurnPayload[] = chatLog.map((m) => {
          if (m.role === 'ai') {
            return {
              role: 'ai',
              text: m.text,
              sources: m.sources ?? [],
              suggestions: m.suggestions ?? [],
            }
          }
          return { role: m.role, text: m.text }
        })
        appendChatTurn(scene, { role: 'ai', text: '', pending: true })
        let buffer = ''
        for await (const ev of chatOrchestrator(
          { scene, user_text: text, chat_history: history },
          undefined,
          { onAttempt },
        )) {
          if (ev.type === 'delta') {
            buffer += ev.delta
            updateLastAiMessage(scene, (m) => ({ ...m, text: buffer }))
          } else if (ev.type === 'done') {
            updateLastAiMessage(scene, (m) => ({
              ...m,
              // ev.text is the cleaned text (source tags stripped); fall back to buffer if absent
              text: (ev as unknown as Record<string, unknown>).text as string ?? buffer,
              sources: ev.sources as SourceTag[],
              suggestions: ev.suggestions,
              pending: false,
            }))
          } else if (ev.type === 'error') {
            updateLastAiMessage(scene, (m) => ({
              ...m,
              text: buffer + `\n\n（${ev.message}）`,
              pending: false,
            }))
          }
          // route 事件忽略（debug 用）
        }
        setRetryStatus(null)
      }
    } catch (err) {
      if (err instanceof LlmConnectionError) {
        setPaused(true)
        setRetryStatus(null)
        // T42: 使用 scene-aware fallback 替代 raw error
        const fb = getFallbackForScene(scene)
        appendChatTurn(scene, {
          role: 'ai',
          text: fb.text,
          sources: fb.sources,
          suggestions: fb.suggestions,
          usedFallback: true,
        })
      } else {
        // eslint-disable-next-line no-console
        console.error('[chat] send failed', err)
        const fb = getFallbackForScene(scene)
        appendChatTurn(scene, {
          role: 'ai',
          text: fb.text,
          sources: fb.sources,
          suggestions: fb.suggestions,
          usedFallback: true,
        })
      }
    } finally {
      setSending(false)
    }
  }, [sending])

  return { send, sending, retryStatus, paused }
}
