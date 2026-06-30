/**
 * VideoList - 复盘左侧最近视频列表（横向 strip）。
 * 每行：缩略图占位 + 标题 + 完播率 chip（低于 / 超出基线）。
 */

interface Video {
  id: string
  title: string
  date: string
  views: number
  finish: number
  baseline: { finish: number }
}

interface Props {
  videos: Video[]
  activeId: string
  onSelect: (id: string) => void
}

export function VideoList({ videos, activeId, onSelect }: Props) {
  return (
    <div className="flex gap-2.5 overflow-x-auto pb-1">
      {videos.map((x) => {
        const active = x.id === activeId
        const below = x.finish < x.baseline.finish
        return (
          <button
            key={x.id}
            type="button"
            onClick={() => onSelect(x.id)}
            className={[
              'flex gap-3 items-center p-2.5 rounded-md border min-w-[280px] flex-1 text-left cursor-pointer transition',
              active ? 'bg-bg-2 border-accent-line' : 'bg-bg-1 border-line-1 hover:bg-bg-2/50',
            ].join(' ')}
          >
            <div
              className="grid place-items-center text-[8px] text-fg-3 bg-bg-2 border border-line-0 rounded-sm flex-shrink-0"
              style={{ width: 56, height: 72 }}
            >
              16:9
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[12.5px] font-medium text-fg-0 truncate">{x.title}</div>
              <div className="text-[11px] text-fg-3 mt-1">
                {x.date} · {x.views.toLocaleString()} 播放
              </div>
              <div className="flex items-center gap-1.5 mt-1.5">
                <span
                  className={[
                    'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-pill border text-[10px]',
                    below
                      ? 'text-neg border-neg/30 bg-neg-soft'
                      : 'text-pos border-pos/30 bg-pos-soft',
                  ].join(' ')}
                >
                  <span
                    className={['w-1 h-1 rounded-pill', below ? 'bg-neg' : 'bg-pos'].join(' ')}
                  />
                  {below ? '低于基线' : '超出基线'}
                </span>
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}
