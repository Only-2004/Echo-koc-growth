/**
 * InsightCard - 单个 insight 卡片：标题 + 正文 + metric + source + 2-3 个 follow-up suggestions。
 *
 * tone 决定 metric chip 颜色（neg / warn / pos / info）。
 * 每个 suggestion 是可点击 chip，点击触发 useOnAsk()。
 */

import { ChevronRight } from 'lucide-react'
import { SourceBadge, type SourceKey } from '../_shared/SourceBadge'
import { useOnAsk } from '../_shared/useOnAsk'

export type InsightTone = 'neg' | 'warn' | 'pos' | 'info'

const TONE_VAR: Record<InsightTone, string> = {
  neg: 'var(--neg)',
  warn: 'var(--warn)',
  pos: 'var(--pos)',
  info: 'var(--info)',
}

const TONE_TEXT: Record<InsightTone, string> = {
  neg: 'text-neg',
  warn: 'text-warn',
  pos: 'text-pos',
  info: 'text-info',
}

interface Metric {
  label: string
  value: string
}
interface Props {
  n: string
  tone: InsightTone
  title: string
  body: string
  metric?: Metric
  source: SourceKey
  suggestions: string[]
}

export function InsightCard({ n, tone, title, body, metric, source, suggestions }: Props) {
  const onAsk = useOnAsk()
  const cssVar = TONE_VAR[tone]
  return (
    <div className="bg-bg-1 border border-line-1 rounded-lg p-5 flex flex-col gap-3.5">
      <div className="flex items-center gap-2.5">
        <span
          className="font-mono text-[10px] px-2 py-0.5 rounded-pill border"
          style={{ color: cssVar, borderColor: `${cssVar}40`, background: `${cssVar}10` }}
        >
          结论 {n}
        </span>
        <SourceBadge source={source} />
        {metric && (
          <div className={['ml-auto font-mono text-[11px]', TONE_TEXT[tone]].join(' ')}>
            {metric.label}{' '}
            <span className="font-semibold">{metric.value}</span>
          </div>
        )}
      </div>
      <div className="text-[15px] font-semibold leading-tight tracking-tight">{title}</div>
      <div className="text-[13px] text-fg-1 leading-relaxed">{body}</div>
      <div className="bg-bg-2 rounded-md border border-line-0 p-3.5">
        <div className="text-kicker text-accent mb-2.5">改进方向</div>
        <div className="flex flex-col gap-2">
          {suggestions.map((s, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onAsk(s)}
              className="text-left px-3 py-2.5 bg-bg-1 border border-line-1 rounded-sm text-fg-0 text-[12.5px] leading-relaxed cursor-pointer flex gap-2.5 items-start hover:bg-bg-2 transition"
            >
              <span className="text-accent mt-0.5">→</span>
              <span className="flex-1">{s}</span>
              <ChevronRight size={12} className="text-fg-3 mt-0.5 flex-shrink-0" />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
