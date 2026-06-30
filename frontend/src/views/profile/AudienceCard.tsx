/**
 * AudienceCard - 受众假设卡（三栏：年龄 / 区域 / 关键词）。
 * 关键词 chip 大小与饱和度与 weight 同步，体现「假设权重」。
 */

import { User } from 'lucide-react'
import { Score } from '../_shared/Score'

interface Audience {
  total: number
  gender_male: number
  gender_female: number
  age_distribution: { age: string; v: number }[]
  regions: { name: string; weight: number }[]
  keywords: { k: string; w: number }[]
}

export function AudienceCard({ data }: { data: Audience }) {
  return (
    <div className="bg-bg-1 border border-line-1 rounded-lg p-6">
      <div className="flex items-center gap-2.5 mb-3.5 flex-wrap">
        <User size={16} className="text-fg-2" />
        <div className="text-[15px] font-semibold">当前粉丝构成</div>
        <span className="font-mono uppercase text-[10.5px] tracking-[0.06em] px-2 py-0.5 rounded border border-line-1 text-fg-2">
          来自抖音后台 · 自动同步
        </span>
        <div className="ml-auto text-[11px] text-fg-3 font-mono">
          {data.total.toLocaleString()} 人 · 男 {Math.round(data.gender_male * 100)}% / 女{' '}
          {Math.round(data.gender_female * 100)}%
        </div>
      </div>
      <div className="grid grid-cols-[1.4fr_1fr_1fr] gap-6">
        <div>
          <div className="text-kicker text-fg-2 mb-2.5">年龄分布</div>
          <AgeBars data={data.age_distribution} />
        </div>
        <div>
          <div className="text-kicker text-fg-2 mb-2.5">来源城市 TOP 4</div>
          {data.regions.map((r) => (
            <div key={r.name} className="flex items-center gap-2.5 mb-2">
              <span className="text-xs text-fg-1 w-12">{r.name}</span>
              <Score value={r.weight} color="var(--info)" />
              <span className="text-[11px] text-fg-2 font-mono min-w-8 text-right">
                {Math.round(r.weight * 100)}%
              </span>
            </div>
          ))}
        </div>
        <div>
          <div className="text-kicker text-fg-2 mb-2.5">关键词共现</div>
          <div className="flex gap-1.5 flex-wrap">
            {data.keywords.map((k) => (
              <span
                key={k.k}
                className="rounded-pill text-accent border border-accent-line"
                style={{
                  padding: '4px 10px',
                  fontSize: 11 + k.w * 4,
                  background: `rgba(93,122,26,${k.w * 0.1})`,
                }}
              >
                {k.k}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function AgeBars({ data }: { data: { age: string; v: number }[] }) {
  const maxIdx = data.reduce((acc, d, i) => (d.v > data[acc].v ? i : acc), 0)
  return (
    <div className="flex items-end gap-2 h-[120px]">
      {data.map((d, i) => (
        <div key={d.age} className="flex-1 text-center">
          <div
            className={[
              'rounded-t-sm mb-2 relative',
              i === maxIdx ? 'bg-accent' : 'bg-bg-3',
            ].join(' ')}
            style={{ height: `${d.v * 100}%`, minHeight: 4 }}
          >
            <span
              className={[
                'absolute -top-[18px] left-1/2 -translate-x-1/2 text-[10px] font-mono',
                i === maxIdx ? 'text-accent' : 'text-fg-2',
              ].join(' ')}
            >
              {Math.round(d.v * 100)}
            </span>
          </div>
          <div className="text-[10.5px] text-fg-2 font-mono">{d.age}</div>
        </div>
      ))}
    </div>
  )
}
