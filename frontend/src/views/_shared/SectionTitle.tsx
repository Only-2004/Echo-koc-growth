/**
 * SectionTitle - 移植自 prototype primitives.jsx。
 * kicker（字体 mono 小标题）+ title + 可选 sub + 可选 right slot。
 */

import type { ReactNode } from 'react'

interface Props {
  kicker?: string
  title: ReactNode
  sub?: string
  right?: ReactNode
}

export function SectionTitle({ kicker, title, sub, right }: Props) {
  return (
    <div className="flex items-end justify-between mb-4">
      <div>
        {kicker && <div className="text-kicker text-fg-2 mb-1.5">{kicker}</div>}
        <div className="text-[22px] font-semibold tracking-tight leading-tight text-fg-0">
          {title}
        </div>
        {sub && (
          <div className="text-[13px] text-fg-2 mt-1.5 max-w-[560px] leading-relaxed">{sub}</div>
        )}
      </div>
      {right}
    </div>
  )
}
