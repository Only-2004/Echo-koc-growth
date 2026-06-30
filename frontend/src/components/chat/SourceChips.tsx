/**
 * 显式渲染 source tag chip。
 * 强制契约：每条 AI 消息至少有一个 source tag（PRD §6.7）。
 *
 * 颜色映射（与 backend ``VALID_SOURCE_TAGS`` 对齐）：
 *   画像驱动     → pillar-confirm（绿）
 *   趋势驱动     → info（蓝）
 *   数据驱动     → warn（琥珀）
 *   历史复盘     → fg-2（中性）
 *   用户偏好驱动 → pillar-personal（紫）
 */

import type { SourceTag } from '../../types/agents'

interface Props {
  sources: SourceTag[] | string[]
}

const TONE_CLASS: Record<string, string> = {
  画像驱动: 'text-pillar-confirm border-pillar-confirm/30 bg-pillar-confirm/10',
  趋势驱动: 'text-info border-info/30 bg-info/10',
  数据驱动: 'text-warn border-warn/30 bg-warn/10',
  历史复盘: 'text-fg-2 border-fg-2/30 bg-fg-2/10',
  用户偏好驱动: 'text-pillar-explore border-pillar-explore/30 bg-pillar-explore/10',
}

const FALLBACK_CLASS = 'text-fg-2 border-fg-2/30 bg-fg-2/10'

export function SourceChips({ sources }: Props) {
  if (!sources || sources.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1.5 pt-1">
      {sources.map((s) => (
        <span
          key={s}
          className={[
            'inline-flex items-center gap-1 px-2 py-0.5 rounded-pill border text-[10px] font-medium',
            TONE_CLASS[s] ?? FALLBACK_CLASS,
          ].join(' ')}
        >
          <span className="w-1.5 h-1.5 rounded-pill bg-current" />
          {s}
        </span>
      ))}
    </div>
  )
}
