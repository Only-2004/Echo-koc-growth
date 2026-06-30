/**
 * ScoreCard - 4 个 Tab 上方的得分卡片（评估 / 趋势 / 差异化 / 节奏）。
 * 选中时四角加粗的 ring + 颜色 border。
 */

import type { LucideIcon } from 'lucide-react'

export type ScoreTone = 'info' | 'person' | 'explore' | 'accent'

const TONE_CSSVAR: Record<ScoreTone, string> = {
  info: 'var(--info)',
  person: 'var(--pillar-person)',
  explore: 'var(--pillar-explore)',
  accent: 'var(--accent)',
}

const TONE_TEXT: Record<ScoreTone, string> = {
  info: 'text-info',
  person: 'text-pillar-person',
  explore: 'text-pillar-explore',
  accent: 'text-accent',
}

interface Props {
  active: boolean
  onClick: () => void
  kicker: string
  score: number | null
  verdict: string
  tone: ScoreTone
  icon?: LucideIcon
}

export function ScoreCard({ active, onClick, kicker, score, verdict, tone, icon: Icon }: Props) {
  const colorVar = TONE_CSSVAR[tone]
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'text-left p-4 bg-bg-1 rounded-lg cursor-pointer flex flex-col gap-2.5 transition border',
        active ? '' : 'border-line-1',
      ].join(' ')}
      style={{
        borderColor: active ? colorVar : undefined,
        boxShadow: active ? `0 0 0 3px ${colorVar}20` : 'none',
      }}
    >
      <div
        className={['font-mono uppercase text-[9.5px] tracking-[0.08em]', TONE_TEXT[tone]].join(' ')}
      >
        {kicker}
      </div>
      {score !== null ? (
        <div className="flex items-baseline gap-1.5">
          <span
            className={['text-[32px] font-semibold tracking-tight', TONE_TEXT[tone]].join(' ')}
          >
            {Math.round(score * 100)}
          </span>
          <span className="text-xs text-fg-3 font-mono">/ 100</span>
        </div>
      ) : (
        <div className={['text-[32px] font-semibold flex items-center gap-2', TONE_TEXT[tone]].join(' ')}>
          {Icon && <Icon size={26} />}
          <span className="text-sm font-medium text-fg-1">READY</span>
        </div>
      )}
      <div className="text-xs text-fg-1 leading-relaxed">{verdict}</div>
    </button>
  )
}
