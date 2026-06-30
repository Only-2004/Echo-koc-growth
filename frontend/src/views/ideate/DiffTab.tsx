/**
 * DiffTab - 「差异化」面板：4 个角度卡。
 */

import { SectionTitle } from '../_shared/SectionTitle'
import { SourceBadge, type SourceKey } from '../_shared/SourceBadge'
import { useOnAsk } from '../_shared/useOnAsk'

interface Angle {
  angle: string
  text: string
  source: SourceKey
}

export function DiffTab({ items }: { items: Angle[] }) {
  const onAsk = useOnAsk()
  return (
    <div>
      <SectionTitle
        kicker="03 · 差异化建议"
        title="可选的差异化角度"
        sub="基于近 30 天 47 条同主题视频的内容拆解，结合你的画像，分析出 4 个角度。"
      />
      <div className="grid grid-cols-2 gap-3">
        {items.map((d, i) => (
          <div
            key={d.angle}
            className="p-4 bg-bg-2 rounded-md border border-line-0 flex flex-col gap-2.5"
          >
            <div className="flex items-center gap-2">
              <span className="font-mono uppercase text-[9.5px] tracking-[0.08em] text-fg-2">
                {String(i + 1).padStart(2, '0')}
              </span>
              <span className="text-sm font-semibold">{d.angle}</span>
              <div className="ml-auto">
                <SourceBadge source={d.source} />
              </div>
            </div>
            <div className="text-[13px] leading-relaxed text-fg-1">{d.text}</div>
            <div className="flex gap-2 mt-1">
              <button
                type="button"
                className="border border-line-1 rounded-pill px-2.5 py-1 text-[11.5px] text-fg-1 hover:bg-bg-1 transition"
              >
                采用这个角度
              </button>
              <button
                type="button"
                onClick={() => onAsk(`帮我把"${d.angle}"展开`)}
                className="border border-line-1 rounded-pill px-2.5 py-1 text-[11.5px] text-fg-2 hover:bg-bg-1 transition"
              >
                追问
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
