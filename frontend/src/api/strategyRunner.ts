/**
 * strategyRunner — 脱离组件生命周期的后台策略生成逻辑。
 *
 * 直接读写 Zustand store（通过 getState()），不依赖 React 渲染周期。
 * 调用方只需 fire-and-forget：`void runStrategySubmit(idea)`。
 * 无论用户在哪个 scene，生成进度都会持续写入 store，切回 IdeateView 即可看到。
 *
 * 缓存策略由后端 ``USE_CACHED_ANALYSIS`` 环境变量控制，前端不再传 mode。
 */

import { getStrategySnapshot, submitStrategy } from './strategy'
import { useAppStore } from '../store/app'
import type { SourceTag } from '../types/agents'

/** 防止并发提交：全局唯一 token，每次新提交递增。 */
let _submitToken = 0

export async function runStrategySubmit(ideaText: string): Promise<void> {
  const store = useAppStore.getState()

  // 防止重复提交
  if (store.strategySubmitting) return

  const myToken = ++_submitToken

  store.setStrategySubmitting(true)
  store.resetStrategyStreaming()

  try {
    let snapshotId: string | null = null
    let finalText = ''
    let finalSources: SourceTag[] = []

    for await (const ev of submitStrategy({ idea_text: ideaText })) {
      // 另一次提交已经开始 → 放弃本次输出
      if (_submitToken !== myToken) return

      const s = useAppStore.getState()
      if (ev.event === 'state') {
        s.setStrategyProgressState(ev.state)
      } else if (ev.event === 'thinking.delta') {
        s.appendStrategyThinkingText(ev.text)
      } else if (ev.event === 'delta') {
        // 后端已 strip SOURCES: 行，直接覆盖（而不是累积），保证干净文本
        finalText = ev.text
        s.setStrategyStreamingText(ev.text)
      } else if (ev.event === 'done') {
        snapshotId = ev.snapshot_id
        s.setSnapshotId(ev.snapshot_id)
        finalText = (ev.result.final_text as string | undefined) ?? finalText
        finalSources = (ev.result.sources as SourceTag[] | undefined) ?? []
      }
    }

    if (snapshotId && _submitToken === myToken) {
      const data = await getStrategySnapshot(snapshotId)
      const s = useAppStore.getState()
      s.setStrategySnapshot(data)
      // 策略结果同步进 ideate chatLog，chat dock 可展示
      if (finalText) {
        s.appendChatTurn('ideate', {
          role: 'ai',
          text: finalText,
          sources: finalSources,
        })
      }
    }
  } catch (err) {
    if (_submitToken === myToken) {
      useAppStore
        .getState()
        .setStrategyError(err instanceof Error ? err.message : String(err))
    }
  } finally {
    if (_submitToken === myToken) {
      useAppStore.getState().setStrategySubmitting(false)
    }
  }
}
