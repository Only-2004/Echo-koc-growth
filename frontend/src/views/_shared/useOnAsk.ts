/**
 * useOnAsk - 统一封装 view 内可点击元素的"追问"行为。
 *
 * M4-M6 闭环：openChat + 通过 useChatSend 触发对应 scene 的 agent
 *   - ideate scene → strategy/refine
 *   - retro scene  → retro/drill
 *   - 其他 → 静态降级（M7 orchestrator 上线后接入）
 */

import { useCallback } from 'react'
import { useChatSend } from '../../components/chat/useChatSend'
import { useAppStore } from '../../store/app'

export function useOnAsk(): (text: string) => void {
  const openChat = useAppStore((s) => s.openChat)
  const { send } = useChatSend()
  return useCallback(
    (text: string) => {
      openChat()
      void send(text)
    },
    [openChat, send],
  )
}
