/**
 * FitBar - 画像贴合度子卡（per metric）。
 */

import { Score } from '../_shared/Score'

type Tone = 'confirm' | 'person' | 'explore'

const TONE_VAR: Record<Tone, string> = {
  confirm: 'var(--pillar-confirm)',
  person: 'var(--pillar-person)',
  explore: 'var(--pillar-explore)',
}

const TONE_TEXT: Record<Tone, string> = {
  confirm: 'text-pillar-confirm',
  person: 'text-pillar-person',
  explore: 'text-pillar-explore',
}

interface Props {
  label: string
  tone: Tone
  value: number
  hint: string
}

export function FitBar({ label, tone, value, hint }: Props) {
  return (
    <div className="p-4 bg-bg-2 rounded-md border border-line-0">
      <div className={['text-kicker mb-2.5', TONE_TEXT[tone]].join(' ')}>{label}</div>
      <div className="flex items-baseline gap-1.5 mb-2">
        <span className={['text-[26px] font-semibold', TONE_TEXT[tone]].join(' ')}>
          {Math.round(value * 100)}
        </span>
        <span className="text-[11px] text-fg-3 font-mono">/ 100</span>
      </div>
      <Score value={value} color={TONE_VAR[tone]} />
      <div className="text-[11px] text-fg-2 mt-2">{hint}</div>
    </div>
  )
}
