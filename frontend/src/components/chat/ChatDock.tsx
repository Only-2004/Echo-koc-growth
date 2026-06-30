/**
 * Echo · Chat Dock 容器（M5/M6 闭环 · T30 + T35）
 *
 * Header + MessageList + Composer 三段式。
 * Send 按 scene 路由：
 *   - ideate + snapshotId → POST /api/strategy/refine（一次性 JSON）
 *   - retro  + reportId   → SSE /api/retro/drill（流式累积）
 *   - 其他场景            → echo 提示「M7 orchestrator 上线后接入」
 *
 * SourceChips 用于显示 backend 返回的 source tag（PRD §6.7 设计红线 1）。
 * M7 才做服务端强校验；本轮只做前端渲染（plan §7）。
 */

import { AlertTriangle, Image as ImageIcon, Loader2, Send, Sparkles, X } from 'lucide-react'
import { useState } from 'react'
import type { ChatMessage, Scene } from '../../store/app'
import { useAppStore } from '../../store/app'
import { MarkdownMessage } from './MarkdownMessage'
import { SourceChips } from './SourceChips'
import { useChatSend } from './useChatSend'

const GENERATE_BRIEF_PREFIX = '[GENERATE_BRIEF]'

const SCENE_ROLE: Record<Scene, string> = {
  home: '',
  onboard: '',
  profile: '画像编辑',
  ideate: '选题助手',
  retro: '复盘分析',
}

export function ChatDock() {
  const scene = useAppStore((s) => s.scene)
  const closeChat = useAppStore((s) => s.closeChat)
  const chatLog = useAppStore((s) => s.chatLog[scene])
  const { send, sending, retryStatus, paused } = useChatSend()

  const [draft, setDraft] = useState('')

  async function handleSend() {
    const text = draft.trim()
    if (!text || sending) return
    setDraft('')
    await send(text)
  }

  return (
    <div className="h-full flex flex-col bg-bg-1">
      <header className="flex items-center justify-between px-5 py-3 border-b border-line-1">
        <div>
          <p className="text-kicker text-fg-2 mb-0.5">AI 助手</p>
          <h2 className="text-sm font-medium text-fg-0">{SCENE_ROLE[scene]}</h2>
        </div>
        <button
          type="button"
          onClick={closeChat}
          className="text-fg-2 hover:text-fg-0 transition"
          aria-label="关闭"
        >
          <X size={16} />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {chatLog.length === 0 && (
          <p className="text-sm text-fg-3">
            还没有对话。任何模块的可点击数据都能进到这里追问。
          </p>
        )}
        {chatLog.map((msg, i) => (
          <ChatRow
            key={i}
            msg={msg}
            onSuggestion={(text) => {
              if (sending) return
              void send(text)
            }}
            onGenerateBrief={(topic) => {
              useAppStore.getState().setPendingIdeaFromChat(topic)
            }}
          />
        ))}
      </div>

      {/* retry / paused 状态 */}
      {paused ? (
        <div className="border-t border-neg/40 bg-neg-soft px-4 py-2 flex items-center gap-2">
          <AlertTriangle size={12} className="text-neg flex-shrink-0" />
          <div className="text-[11px] text-neg flex-1">
            LLM 连接错误，已暂停。请刷新页面重试。
          </div>
        </div>
      ) : retryStatus && (retryStatus.attempt > 1 || retryStatus.error) ? (
        <div className="border-t border-warn/40 bg-warn-soft px-4 py-2 flex items-center gap-2">
          <Loader2 size={12} className="text-warn animate-spin flex-shrink-0" />
          <div className="text-[11px] text-warn flex-1">
            LLM 连接错误，正在重试 ({retryStatus.attempt}/{retryStatus.max})…
          </div>
        </div>
      ) : null}

      <footer className="border-t border-line-1 px-4 py-3">
        <div className="flex items-end gap-2 bg-bg-inset rounded-xl border border-line-1 p-2">
          <textarea
            className="flex-1 bg-transparent text-sm text-fg-0 placeholder:text-fg-3 resize-none focus:outline-none px-2 py-1.5 leading-relaxed"
            rows={1}
            placeholder="问点什么…"
            value={draft}
            disabled={sending}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void handleSend()
              }
            }}
          />
          <button
            type="button"
            className="w-8 h-8 rounded-pill text-fg-2 hover:text-fg-0 hover:bg-bg-3 flex items-center justify-center transition"
            aria-label="附加图片"
          >
            <ImageIcon size={14} />
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={!draft.trim() || sending}
            className="w-8 h-8 rounded-pill bg-accent text-accent-ink hover:bg-accent/90 disabled:bg-bg-3 disabled:text-fg-3 flex items-center justify-center transition"
            aria-label="发送"
          >
            {sending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
          </button>
        </div>
        <p className="text-[10px] text-fg-3 mt-2 px-2">
          AI 引用你的画像与最近发布。
          <button type="button" className="underline ml-1">
            了解隐私
          </button>
        </p>
      </footer>
    </div>
  )
}

function ChatRow({
  msg,
  onSuggestion,
  onGenerateBrief,
}: {
  msg: ChatMessage
  onSuggestion: (text: string) => void
  onGenerateBrief: (topic: string) => void
}) {
  const wrapper =
    msg.role === 'user'
      ? 'flex justify-end'
      : msg.role === 'system'
      ? 'flex justify-center'
      : 'flex justify-start'

  const bubble = [
    'max-w-[85%] text-sm leading-relaxed whitespace-pre-wrap',
    msg.role === 'user' && 'bg-accent text-accent-ink rounded-xl rounded-tr-sm px-4 py-2',
    msg.role === 'ai' && 'space-y-2 text-fg-0',
    msg.role === 'system' && 'text-xs text-fg-2 font-mono',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={wrapper}>
      <div className={bubble}>
        {msg.role === 'ai' ? (
          <MarkdownMessage
            text={msg.text}
            thinkingText={msg.thinkingText}
            pending={msg.pending}
          />
        ) : (
          <p>{msg.text || ''}</p>
        )}
        {msg.role === 'ai' && msg.sources && msg.sources.length > 0 && (
          <SourceChips sources={msg.sources} />
        )}
        {msg.role === 'ai' && msg.suggestions && msg.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {msg.suggestions.map((s) => {
              if (s.startsWith(GENERATE_BRIEF_PREFIX)) {
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onGenerateBrief(msg.text)}
                    className="text-xs px-3 py-1.5 rounded-pill bg-accent text-accent-ink hover:bg-accent/90 transition flex items-center gap-1.5 font-medium"
                  >
                    <Sparkles size={12} />
                    生成拍摄简报 →
                  </button>
                )
              }
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => onSuggestion(s)}
                  className="text-xs px-3 py-1 rounded-pill border border-line-1 text-fg-1 hover:bg-bg-2 transition"
                >
                  {s}
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
