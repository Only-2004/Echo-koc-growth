/**
 * SourceBadge - 单个来源标签 chip（profile / trend / explore / data）。
 * 与 components/chat/SourceChips 配合（store.SourceTag 用中文标签，
 * 这里用英文 source key 是因为 prototype 数据里用英文短串）。
 *
 * tone 颜色映射：
 *   profile → pillar-person（琥珀）
 *   trend   → info（蓝）
 *   explore → pillar-explore（紫）
 *   data    → accent（绿）
 */

export type SourceKey = 'profile' | 'trend' | 'explore' | 'data'

const MAP: Record<SourceKey, { label: string; cls: string }> = {
  profile: { label: '画像驱动', cls: 'text-pillar-person border-pillar-person/30 bg-pillar-person/10' },
  trend: { label: '趋势驱动', cls: 'text-info border-info/30 bg-info/10' },
  explore: { label: '探索驱动', cls: 'text-pillar-explore border-pillar-explore/30 bg-pillar-explore/10' },
  data: { label: '数据驱动', cls: 'text-accent border-accent-line bg-accent-soft' },
}

export function SourceBadge({ source }: { source: SourceKey }) {
  const t = MAP[source]
  return (
    <span
      className={[
        'inline-flex items-center font-mono uppercase text-[9.5px] tracking-[0.08em] px-1.5 py-0.5 rounded border',
        t.cls,
      ].join(' ')}
    >
      {t.label}
    </span>
  )
}
