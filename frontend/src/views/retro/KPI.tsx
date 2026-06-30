/**
 * KPI - retro 顶部的 KPI 卡：label + value + delta + sparkline。
 *
 * 数字版（completion / follow / share）：delta 数值 + 上下箭头颜色
 * 文本版（sentiment）：tone='warn' 强制 warn 色，delta 是文字
 *
 * onDeepDive：提供时在卡片底部显示「深入解读」按钮，点击才触发 agent drill。
 */

import { ArrowDown, ArrowUp } from 'lucide-react'
import { Sparkline } from '../_shared/Sparkline'

type Format = 'pp' | 'rel' | 'raw'

interface Props {
  label: string
  value: string | number
  delta: number | string
  format: Format
  spark?: number[]
  tone?: 'warn'
  negativeIsBad?: boolean
  onDeepDive?: () => void
}

export function KPI({ label, value, delta, format, spark, tone, negativeIsBad, onDeepDive }: Props) {
  const num = typeof delta === 'number' ? delta : null
  const isBad = num !== null && (negativeIsBad ? num < 0 : num > 0)
  const isGood = num !== null && (negativeIsBad ? num > 0 : num < 0)
  const tw =
    tone === 'warn'
      ? 'text-warn'
      : isBad
        ? 'text-neg'
        : isGood
          ? 'text-pos'
          : 'text-fg-2'
  const sparkColor = isBad ? 'var(--neg)' : 'var(--info)'
  const display =
    num !== null
      ? format === 'pp'
        ? `${num > 0 ? '+' : ''}${(num * 100).toFixed(1)} pp`
        : `${num > 0 ? '+' : ''}${num}`
      : delta
  return (
    <div className="p-4 bg-bg-1 border border-line-1 rounded-lg flex flex-col gap-2.5">
      <div className="flex items-center justify-between">
        <div className="text-kicker text-fg-2">{label}</div>
        {spark && <Sparkline values={spark} width={60} height={20} color={sparkColor} />}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-[30px] font-semibold tracking-tight">{value}</span>
      </div>
      <div className={['flex items-center gap-2', tw].join(' ')}>
        {num !== null && (isBad ? <ArrowDown size={12} /> : isGood ? <ArrowUp size={12} /> : null)}
        <span className="text-xs font-mono">{display}</span>
      </div>
      {onDeepDive && (
        <button
          type="button"
          onClick={onDeepDive}
          className="mt-1 self-start text-[11px] text-accent hover:underline font-medium"
        >
          深入解读 →
        </button>
      )}
    </div>
  )
}
