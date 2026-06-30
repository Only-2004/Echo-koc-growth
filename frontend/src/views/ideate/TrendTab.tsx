/**
 * TrendTab - 「热度」面板：4 metric 卡 + 13 天 Sparkline。
 */

import { ArrowDown, ArrowUp } from 'lucide-react'
import { SectionTitle } from '../_shared/SectionTitle'
import { Sparkline } from '../_shared/Sparkline'
import { useOnAsk } from '../_shared/useOnAsk'

interface Metric {
  label: string
  value: string
  trend: 'up' | 'down' | 'flat'
  hint: string
}

interface Props {
  verdict: string
  metrics: Metric[]
  spark: number[]
}

export function TrendTab({ verdict: _verdict, metrics, spark }: Props) {
  void _verdict
  const onAsk = useOnAsk()
  return (
    <div className="grid grid-cols-[1.2fr_1fr] gap-8">
      <div>
        <SectionTitle
          kicker="01 · 热度匹配度 · 趋势驱动"
          title={<>最近<span className="text-accent">热度较高</span></>}
          sub="过去 7 天「考研日常 / 学习生活类」的发布量、互动量都在快速上升。"
        />
        <div className="grid grid-cols-2 gap-3">
          {metrics.map((m) => (
            <button
              key={m.label}
              type="button"
              onClick={() => onAsk(`展开「${m.label}」这个数据`)}
              className="text-left p-4 rounded-md bg-bg-2 border border-line-0 hover:bg-bg-3/50 transition"
            >
              <div className="text-kicker text-fg-2 mb-2">{m.label}</div>
              <div className="text-[22px] font-semibold tracking-tight flex items-center gap-2">
                {m.value}
                {m.trend === 'up' && <ArrowUp size={14} className="text-pos" />}
                {m.trend === 'down' && (
                  <ArrowDown
                    size={14}
                    className={m.label.includes('供给') ? 'text-pos' : 'text-neg'}
                  />
                )}
              </div>
              {m.hint && <div className="text-[11px] text-fg-3 mt-1">{m.hint}</div>}
            </button>
          ))}
        </div>
      </div>
      <div>
        <div className="text-kicker text-fg-2 mb-3">同类话题热度走势 · 近 13 天</div>
        <div className="p-5 bg-bg-2 rounded-md border border-line-0">
          <Sparkline values={spark} width={320} height={100} color="var(--info)" fill />
          <div className="flex justify-between mt-2 font-mono text-[10px] text-fg-3">
            <span>4/14</span>
            <span>4/20</span>
            <span>今天</span>
          </div>
        </div>
      </div>
    </div>
  )
}
