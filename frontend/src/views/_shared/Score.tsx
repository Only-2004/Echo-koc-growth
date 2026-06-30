/**
 * Score - 0-1 进度条。
 * 移植自 prototype primitives.jsx 的 Score。
 * 用 inline style 接受任意 color（要支持 CSS var 与 hex 混用）。
 */

interface ScoreProps {
  value: number
  color?: string
  height?: number
  label?: string | number
}

export function Score({ value, color = 'var(--accent)', height = 6, label }: ScoreProps) {
  const pct = Math.max(0, Math.min(1, value)) * 100
  return (
    <div className="w-full flex items-center gap-2">
      <div
        className="flex-1 rounded-pill overflow-hidden"
        style={{ height, background: 'var(--bg-3)' }}
      >
        <div
          className="h-full rounded-pill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      {label !== undefined && (
        <span className="font-mono text-[11px] text-fg-1 min-w-[28px] text-right">{label}</span>
      )}
    </div>
  )
}
