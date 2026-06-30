/**
 * EvalTab - 「画像贴合度」面板。
 *
 * 包含：3 个 FitBar（确定项一致性 / 个性化资产挖掘 / 待探索项验证价值）+ 4 条来源标记的 note。
 */

import { ChevronRight } from 'lucide-react'
import { SectionTitle } from '../_shared/SectionTitle'
import { SourceBadge, type SourceKey } from '../_shared/SourceBadge'
import { useOnAsk } from '../_shared/useOnAsk'
import { FitBar } from './FitBar'

interface Note {
  source: SourceKey
  text: string
}

interface Props {
  matchConfirm: number
  matchPerson: number
  exploreValue: number
  notes: Note[]
}

export function EvalTab({ matchConfirm, matchPerson, exploreValue, notes }: Props) {
  const onAsk = useOnAsk()
  return (
    <div>
      <SectionTitle
        kicker="02 · 画像贴合度 · 画像驱动"
        title="个人画像契合度"
      />
      <div className="grid grid-cols-3 gap-3 mb-6">
        <FitBar label="与确定项一致性" tone="confirm" value={matchConfirm} hint="食堂探店 · 考研中" />
        <FitBar label="个性化角度挖掘" tone="person" value={matchPerson} hint="活力 / 真实感" />
        <FitBar label="待探索项验证价值" tone="explore" value={exploreValue} hint="考研定位是否长期主轴" />
      </div>
      <div className="flex flex-col gap-2.5">
        {notes.map((n, i) => (
          <div
            key={i}
            className="flex gap-3 items-start px-4 py-3.5 bg-bg-2 rounded-md border border-line-0"
          >
            <div className="flex-shrink-0 mt-0.5">
              <SourceBadge source={n.source} />
            </div>
            <div className="text-[13px] leading-relaxed text-fg-0 flex-1">{n.text}</div>
            <button
              type="button"
              onClick={() => onAsk(`展开聊：${n.text}`)}
              className="flex-shrink-0 px-2 py-1 border border-line-1 rounded-sm bg-transparent text-fg-2 text-[11px] inline-flex items-center gap-1 hover:bg-bg-1 transition"
            >
              追问 <ChevronRight size={11} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
