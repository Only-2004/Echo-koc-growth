/**
 * Sparkline - 极简内联 SVG 折线/面积图。
 * 移植自 frontend_design/prototype/components/primitives.jsx 的 Sparkline。
 * 无 chart 库依赖，纯 SVG path。
 */

interface SparklineProps {
  values: number[]
  width?: number
  height?: number
  color?: string
  fill?: boolean
}

export function Sparkline({
  values,
  width = 80,
  height = 24,
  color = 'currentColor',
  fill = false,
}: SparklineProps) {
  if (!values.length) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const step = values.length > 1 ? width / (values.length - 1) : 0
  const pts = values.map((v, i) => [i * step, height - ((v - min) / range) * (height - 4) - 2])
  const d = pts.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(' ')
  const dFill = fill ? `${d} L${width},${height} L0,${height} Z` : ''
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ overflow: 'visible' }}
    >
      {fill && <path d={dFill} fill={color} opacity="0.14" />}
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
