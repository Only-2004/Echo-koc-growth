/**
 * HistoryStrip - 画像更新频次（迷你柱图）。
 * 每个柱代表一个版本节点，柱高 = ticks 信号量。
 */

interface Item {
  date: string
  label: string
  ticks: number
}

export function HistoryStrip({ items }: { items: Item[] }) {
  const max = items.reduce((m, x) => Math.max(m, x.ticks), 1)
  return (
    <div className="bg-bg-1 border border-line-1 rounded-lg p-6">
      <div className="flex items-center gap-2.5 mb-3.5">
        <div className="text-[15px] font-semibold">画像更新频次</div>
        <span className="text-xs text-fg-3">{items.length} 次更新 · 越多说明你越在主动迭代</span>
      </div>
      <div className="flex items-end gap-3 h-[80px]">
        {items.map((it, i) => (
          <div key={it.date} className="flex-1 flex flex-col items-center gap-1.5">
            <div
              className={[
                'w-full rounded-t-sm',
                i === items.length - 1 ? 'bg-accent' : 'bg-bg-3',
              ].join(' ')}
              style={{ height: `${(it.ticks / max) * 100}%`, minHeight: 4 }}
              title={`${it.label} · ${it.ticks} 信号`}
            />
            <div className="text-[10px] text-fg-3 font-mono">{it.date}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
