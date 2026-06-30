/**
 * Echo · 顶部条
 *
 * - ⌘K 搜索按钮（M0 占位）
 * - chat dock 折叠时显示「打开 AI 助手」按钮
 */

import { MessageCircle } from 'lucide-react'
import { useAppStore } from '../store/app'

export function TopBar() {
  const chatOpen = useAppStore((s) => s.chatOpen)
  const openChat = useAppStore((s) => s.openChat)

  return (
    <header
      className="sticky top-0 z-10 flex items-center gap-4 px-6 py-3 border-b border-line-0"
      style={{
        background: 'rgba(250,249,246,0.85)',
        backdropFilter: 'blur(12px)',
      }}
    >
      <div className="flex-1" />

      {!chatOpen && (
        <button
          type="button"
          onClick={openChat}
          className="flex items-center gap-2 px-3 py-1.5 rounded-pill text-xs bg-accent text-accent-ink hover:bg-accent/90 transition font-medium"
        >
          <MessageCircle size={12} />
          打开 AI 助手
        </button>
      )}
    </header>
  )
}
