/**
 * PillarColumn - 三态画像中的单列容器。
 *
 * tone 决定标题颜色（confirm 绿 / person 琥珀 / explore 紫）。
 * 待探索项 (explore) 必须独立成列 — 这是 PRD 红线。
 */

import type { ReactNode } from 'react'

export type PillarTone = 'confirm' | 'person' | 'explore'

const TONE_DOT: Record<PillarTone, string> = {
  confirm: 'bg-pillar-confirm',
  person: 'bg-pillar-person',
  explore: 'bg-pillar-explore',
}

const TONE_TEXT: Record<PillarTone, string> = {
  confirm: 'text-pillar-confirm',
  person: 'text-pillar-person',
  explore: 'text-pillar-explore',
}

interface Props {
  tone: PillarTone
  kicker: string
  count: string
  children: ReactNode
}

export function PillarColumn({ tone, kicker, count, children }: Props) {
  return (
    <div className="bg-bg-1 border border-line-1 rounded-lg p-6 flex flex-col min-h-[360px]">
      <div className="flex items-center gap-2 mb-4">
        <span className={['w-1.5 h-1.5 rounded-pill', TONE_DOT[tone]].join(' ')} />
        <span
          className={['font-mono uppercase text-[9.5px] tracking-[0.08em]', TONE_TEXT[tone]].join(' ')}
        >
          {kicker}
        </span>
        <span className="ml-auto font-mono text-[11px] text-fg-2">{count}</span>
      </div>
      <div className="flex flex-col gap-2.5 flex-1">{children}</div>
    </div>
  )
}
