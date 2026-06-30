/**
 * StrategyVsReality - 「发布前的策略假设」 vs 「发生了什么」。
 *
 * dashed 假设面板（左）+ solid 实际面板（右）+ 中间 ArrowRight 圆形指示。
 * 这是 Echo 的核心契约视觉：strategy snapshot → retro report 的归因映射。
 */

import { ArrowRight } from 'lucide-react'

interface Props {
  strategy: string[]
  reality: string[]
}

export function StrategyVsReality({ strategy, reality }: Props) {
  return (
    <div className="bg-bg-1 border border-line-1 rounded-lg p-6">
      <div className="text-kicker text-fg-2 mb-3.5">策略 vs 实际</div>
      <div className="grid grid-cols-[1fr_32px_1fr] gap-4 items-stretch">
        {/* Strategy hypothesis (dashed) */}
        <div className="p-4 bg-bg-2 rounded-md border border-dashed border-line-2">
          <div className="text-kicker text-fg-2 mb-2">发布前的策略</div>
          <ul className="m-0 pl-4 text-[12.5px] leading-relaxed text-fg-1 list-disc">
            {strategy.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>

        {/* Arrow */}
        <div className="grid place-items-center">
          <div className="w-8 h-8 rounded-pill bg-bg-2 text-fg-2 grid place-items-center border border-line-1">
            <ArrowRight size={14} />
          </div>
        </div>

        {/* Reality (solid) */}
        <div className="p-4 bg-bg-2 rounded-md border border-line-1">
          <div className="text-kicker text-fg-1 mb-2">实际数据</div>
          <ul className="m-0 pl-4 text-[12.5px] leading-relaxed text-fg-1 list-disc">
            {reality.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
