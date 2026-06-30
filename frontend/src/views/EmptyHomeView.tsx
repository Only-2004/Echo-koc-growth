/**
 * EmptyHomeView - profileReady=false 时的 home。
 *
 * 按 frontend_design/prototype/components/empty-home-view.jsx 还原：
 *   760px 居中列 / 三 locked preview 卡 / 大型 primary CTA 卡 / 软性次级链接。
 *
 * H1 文案严格按 PRD §6.1：
 *   「我先帮你建一个 KOC 画像。所有别的事都从它长出来。」
 *
 * 点击 CTA：setScene('onboard') + openChat()
 */

import { ArrowRight, BarChart3, Brain, Lightbulb, Lock, User } from 'lucide-react'
import { useAppStore } from '../store/app'

const LOCKED_PREVIEWS = [
  { Icon: Lightbulb, title: '选题策略' },
  { Icon: BarChart3, title: '复盘' },
  { Icon: Brain, title: 'AI 编排' },
] as const

export function EmptyHomeView() {
  const setScene = useAppStore((s) => s.setScene)
  const openChat = useAppStore((s) => s.openChat)

  return (
    <div className="max-w-[760px] mx-auto mt-10 px-6 flex flex-col gap-7 pb-12">
      {/* Header */}
      <div>
        <div className="text-kicker text-fg-2 mb-2.5">WELCOME</div>
        <h1 className="text-[38px] leading-tight tracking-tight font-semibold text-fg-0 m-0">
          第一步，创建<span className="text-accent">KOC 画像</span>。
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed text-fg-1 max-w-[600px]">
          AI 用画像分析你作为创作者「是谁、为谁创作、还在试什么」，并基于此选题、做策略、跑复盘。
        </p>
      </div>

      {/* Three locked previews */}
      <div className="grid grid-cols-3 gap-3">
        {LOCKED_PREVIEWS.map((m) => (
          <div
            key={m.title}
            className="relative p-4 bg-bg-1 border border-dashed border-line-2 rounded-lg opacity-[0.62]"
          >
            <div className="absolute top-3 right-3 w-[22px] h-[22px] rounded-md bg-bg-2 border border-line-1 grid place-items-center text-fg-2">
              <Lock size={11} />
            </div>
            <div className="text-fg-2 mb-2.5">
              <m.Icon size={18} />
            </div>
            <div className="text-sm font-semibold text-fg-1">{m.title}</div>
          </div>
        ))}
      </div>

      {/* Primary CTA card */}
      <div
        className="p-6 bg-bg-1 border border-accent-line rounded-xl flex items-center gap-5"
        style={{ boxShadow: '0 1px 0 var(--accent-soft) inset' }}
      >
        <div className="w-14 h-14 rounded-lg bg-accent-soft border border-accent-line grid place-items-center text-accent flex-shrink-0">
          <User size={24} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-base font-semibold text-fg-0">创建你的 KOC 画像</div>
        </div>
        <button
          type="button"
          onClick={() => {
            setScene('onboard')
            openChat()
          }}
          className="bg-accent text-accent-ink hover:bg-accent/90 transition px-5 py-3 rounded-pill text-sm font-semibold flex items-center gap-2 flex-shrink-0"
        >
          开始对话 <ArrowRight size={14} />
        </button>
      </div>
    </div>
  )
}
