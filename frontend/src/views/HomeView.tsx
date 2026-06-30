/**
 * HomeView - profileReady=true 时的 home。
 *
 * 还原 prototype/home-view.jsx：
 *   - Hero greeting + headline insight（数据点 text-accent 高亮）
 *   - 3 next-action 卡（复盘 / 选题 / 画像更新），每卡可点击直接 setScene
 *   - 30 天数据卡（4 metric + sparkline）
 *
 * 数据：frontend/src/data/home_summary.json
 */

import { BarChart3, ChartLine, ChevronRight, Lightbulb, User } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import seed from '../data/home_summary.json'
import { useAppStore } from '../store/app'
import type { Scene } from '../store/app'
import { Sparkline } from './_shared/Sparkline'

type Tone = 'accent' | 'info' | 'explore' | 'fg' | 'person'

const TONE_COLOR: Record<Tone, string> = {
  accent: 'var(--accent)',
  info: 'var(--info)',
  explore: 'var(--pillar-explore)',
  person: 'var(--pillar-person)',
  fg: 'var(--fg-1)',
}

const TONE_TEXT: Record<Tone, string> = {
  accent: 'text-accent',
  info: 'text-info',
  explore: 'text-pillar-explore',
  person: 'text-pillar-person',
  fg: 'text-fg-1',
}

const TONE_BG: Record<Tone, string> = {
  accent: 'bg-accent/10',
  info: 'bg-info/10',
  explore: 'bg-pillar-explore/10',
  person: 'bg-pillar-person/10',
  fg: 'bg-bg-3',
}

const ICON_MAP: Record<string, LucideIcon> = {
  Chart: BarChart3,
  Lightbulb,
  User,
}

export function HomeView() {
  const setScene = useAppStore((s) => s.setScene)

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-6 flex flex-col gap-6">
      {/* Greeting */}
      <div>
        <div className="text-[32px] font-semibold tracking-tight leading-tight max-w-[760px]">
          {seed.title}
        </div>
        <div className="text-sm text-fg-1 mt-3 max-w-[720px] leading-relaxed">
          {seed.mid}
          <ul className="mt-2 space-y-1.5 list-disc pl-5">
            {seed.headline_accents.map((accent) => (
              <li key={accent} className="text-accent">
                {accent}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 3 action cards */}
      <div className="grid grid-cols-3 gap-4">
        {seed.actions.map((a) => {
          const Icon = ICON_MAP[a.icon] ?? BarChart3
          const tone = a.tone as Tone
          return (
            <button
              key={a.title}
              type="button"
              onClick={() => setScene(a.scene as Scene)}
              className="text-left p-5 bg-bg-1 border border-line-1 rounded-lg cursor-pointer flex flex-col gap-3 min-h-[220px] hover:bg-bg-2/30 transition"
            >
              <div
                className={[
                  'w-8 h-8 rounded-md grid place-items-center',
                  TONE_TEXT[tone],
                  TONE_BG[tone],
                ].join(' ')}
              >
                <Icon size={16} />
              </div>
              <div className="text-[17px] font-semibold tracking-tight leading-tight">
                {a.title}
              </div>
              <div className="text-[12.5px] text-fg-1 leading-relaxed flex-1">{a.body}</div>
              <div
                className={[
                  'flex items-center gap-1.5 text-[12.5px] font-medium mt-1',
                  TONE_TEXT[tone],
                ].join(' ')}
              >
                {a.cta} <ChevronRight size={12} />
              </div>
            </button>
          )
        })}
      </div>

      {/* 30d metrics */}
      <div className="bg-bg-1 border border-line-1 rounded-lg p-6">
        <div className="flex items-center gap-2.5 mb-4">
          <ChartLine size={16} className="text-fg-2" />
          <div className="text-[15px] font-semibold">过去 30 天</div>
        </div>
        <div className="grid grid-cols-4 gap-6">
          {seed.metrics_30d.map((m) => {
            const tone = m.tone as Tone
            return (
              <div key={m.label}>
                <div className="text-kicker text-fg-2 mb-1.5">{m.label}</div>
                <div className="text-[26px] font-semibold tracking-tight">{m.value}</div>
                <div className="mt-1.5">
                  <Sparkline values={m.spark} width={140} height={24} color={TONE_COLOR[tone]} fill />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
