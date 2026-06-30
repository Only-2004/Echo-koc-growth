/**
 * ProfileView — 你的 KOC 画像（M4-M6 闭环）
 *
 * 数据优先级：
 *   1) store.profile（backend onboarding finalize / retro update_profile 的输出）
 *   2) profile_seed.json（M3 mock 兜底，仅当 store.profile 为空）
 *
 * 三态画像（PRD §6.3 / 红线 #2 待探索项独立成列）：
 *   - confirmed.content_pillars + confirmed.audience_baseline → 确定项列
 *   - personalized.persona_traits + life_context → 个性化项列
 *   - to_explore.open_questions + hypotheses + aspirations → 待探索项列
 *
 * Audience / History strip 因 backend Profile 没直接字段，仍走 seed 兜底。
 */

import { useState } from 'react'
import { ChevronRight, RefreshCw, RotateCcw, Sparkles } from 'lucide-react'
import seed from '../data/profile_seed.json'
import { useOnAsk } from './_shared/useOnAsk'
import { Score } from './_shared/Score'
import { PillarColumn } from './profile/PillarColumn'
import { AudienceCard } from './profile/AudienceCard'
import { HistoryStrip } from './profile/HistoryStrip'
import { useAppStore } from '../store/app'
import type { Profile } from '../types/agents'
import { resetDemo, getLatestProfile } from '../api/profile'

type Tone = 'confirm' | 'person' | 'explore'

const CHIP_TONE_CLASS: Record<Tone, string> = {
  confirm: 'text-pillar-confirm border-pillar-confirm/30 bg-pillar-confirm/10',
  person: 'text-pillar-person border-pillar-person/30 bg-pillar-person/10',
  explore: 'text-pillar-explore border-pillar-explore/30 bg-pillar-explore/10',
}

const DOT_TONE: Record<Tone, string> = {
  confirm: 'bg-pillar-confirm',
  person: 'bg-pillar-person',
  explore: 'bg-pillar-explore',
}

interface ConfirmRow {
  tag: string
  value: string
}

interface PersonRow {
  label: string
  weight: number
  evidence: string
}

interface ExploreRow {
  q: string
  status: string
  hint: string
}

interface DerivedPillars {
  confirm: ConfirmRow[]
  person: PersonRow[]
  explore: ExploreRow[]
}

function deriveFromBackend(profile: Profile): DerivedPillars {
  // confirmed
  const confirm: ConfirmRow[] = []
  for (const pillar of profile.confirmed?.content_pillars ?? []) {
    confirm.push({
      tag: '内容主轴',
      value: pillar.name,
    })
  }
  for (const [k, v] of Object.entries(profile.confirmed?.audience_baseline ?? {})) {
    confirm.push({ tag: k, value: String(v) })
  }
  for (const [k, v] of Object.entries(profile.confirmed?.content_style ?? {})) {
    confirm.push({ tag: k, value: String(v) })
  }

  // personalized
  const person: PersonRow[] = []
  for (const trait of profile.personalized?.persona_traits ?? []) {
    const ev = trait.evidence?.[0] as Record<string, unknown> | undefined
    const snippet =
      (ev?.snippet as string | undefined) ??
      (ev?.ref as string | undefined) ??
      `${trait.evidence?.length ?? 0} 条证据`
    person.push({
      label: trait.trait,
      weight: 0.7,
      evidence: snippet,
    })
  }
  for (const ctx of profile.personalized?.life_context ?? []) {
    person.push({
      label: ctx.context,
      weight: 0.7,
      evidence: ctx.valid_until ? `有效至 ${ctx.valid_until}` : '当前生活上下文',
    })
  }

  // to_explore
  const explore: ExploreRow[] = []
  for (const q of profile.to_explore?.open_questions ?? []) {
    explore.push({
      q: q.question,
      status: 'OPEN',
      hint: q.evidence?.length ? `${q.evidence.length} 条线索待验证` : '需要更多回答',
    })
  }
  for (const h of profile.to_explore?.hypotheses ?? []) {
    explore.push({
      q: h.hypothesis,
      status: h.status === 'pending' ? 'PENDING' : h.status.toUpperCase(),
      hint: `for: ${h.evidence_for?.length ?? 0} · against: ${h.evidence_against?.length ?? 0}`,
    })
  }
  for (const asp of profile.to_explore?.aspirations ?? []) {
    explore.push({
      q: asp,
      status: 'ASPIRATION',
      hint: '长期希望验证',
    })
  }

  return { confirm, person, explore }
}

export function ProfileView() {
  const onAsk = useOnAsk()
  const profile = useAppStore((s) => s.profile)
  const setScene = useAppStore((s) => s.setScene)
  const setProfile = useAppStore((s) => s.setProfile)
  const setStrategySnapshot = useAppStore((s) => s.setStrategySnapshot)
  const [resetting, setResetting] = useState(false)

  async function handleReset() {
    if (!window.confirm('重置到 Demo 初始态（v3）？所有测试 session 数据将删除。')) return
    setResetting(true)
    try {
      await resetDemo()
      const freshProfile = await getLatestProfile()
      setProfile(freshProfile)
      setStrategySnapshot(null)
    } catch (e) {
      console.error('reset failed', e)
    } finally {
      setResetting(false)
    }
  }

  const id = seed.identity // identity 行用 seed（backend Profile 没头像 / handle）
  const fallback = seed.pillars
  const derived = profile ? deriveFromBackend(profile) : null

  // 优先 backend，缺字段时 fallback seed 对应列（避免某列完全空白）
  const confirmRows = (derived?.confirm.length ?? 0) > 0 ? derived!.confirm : fallback.confirm
  const personRows: PersonRow[] =
    (derived?.person.length ?? 0) > 0
      ? derived!.person
      : fallback.person.map((p) => ({
          label: p.label,
          weight: p.weight,
          evidence: p.evidence,
        }))
  const exploreRows: ExploreRow[] =
    (derived?.explore.length ?? 0) > 0
      ? derived!.explore
      : fallback.explore.map((e) => ({ q: e.q, status: e.status, hint: e.hint }))

  const versionLabel = profile
    ? `v${profile.meta.version} · ${new Date(profile.meta.created_at).toLocaleString('zh-CN')}`
    : id.last_updated

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-6 flex flex-col gap-7">
      {/* Identity header card */}
      <div className="grid grid-cols-[auto_1fr_auto] gap-7 items-center bg-bg-1 border border-line-1 rounded-xl px-8 py-7">
        <div
          className="rounded-pill grid place-items-center text-fg-0 font-semibold border border-line-2"
          style={{ width: 72, height: 72, background: 'var(--bg-3)', fontSize: 30 }}
        >
          A
        </div>
        <div>
          <div className="text-kicker text-fg-2 mb-1.5">
            YOUR KOC PROFILE {profile && `· v${profile.meta.version}`}
          </div>
          <div className="text-[30px] font-semibold tracking-tight leading-tight">
            <span className="text-fg-2 font-normal">{id.handle}</span>
            <span className="ml-2.5">{id.platform}</span>
            <span className="ml-2.5 text-accent">{id.summary_line}</span>
          </div>
          <div className="text-sm text-fg-1 mt-2 leading-relaxed max-w-[720px]">
            {id.summary_body}
          </div>
          <div className="flex gap-2 mt-3.5 flex-wrap">
            {id.stage_chips.map((c) => (
              <span
                key={c.label}
                className={[
                  'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill border text-[11px]',
                  CHIP_TONE_CLASS[c.tone as Tone],
                ].join(' ')}
              >
                <span
                  className={['w-1.5 h-1.5 rounded-pill', DOT_TONE[c.tone as Tone]].join(' ')}
                />
                {c.label}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-2 items-stretch">
          <button
            type="button"
            onClick={() => setScene('onboard')}
            className="bg-accent text-accent-ink hover:bg-accent/90 transition px-3.5 py-2 rounded-pill text-sm font-medium flex items-center gap-1.5 justify-center"
          >
            <Sparkles size={14} /> 对话并更新画像
          </button>
          <button
            type="button"
            onClick={() => onAsk('从最近发布的视频再抽一遍画像')}
            className="border border-line-1 text-fg-1 hover:bg-bg-2 transition px-3.5 py-2 rounded-pill text-sm flex items-center gap-1.5 justify-center"
          >
            <RefreshCw size={14} /> 从新视频中更新画像
          </button>
          <button
            type="button"
            onClick={handleReset}
            disabled={resetting}
            className="border border-neg/40 text-neg hover:bg-neg/10 transition px-3.5 py-2 rounded-pill text-sm flex items-center gap-1.5 justify-center disabled:opacity-50"
          >
            <RotateCcw size={14} /> {resetting ? '重置中…' : '重置到 Demo 初始态'}
          </button>
          <div className="text-[11px] text-fg-3 mt-1 text-right">{versionLabel}</div>
        </div>
      </div>

      {/* Three pillars (待探索项独立成列 — 红线) */}
      <div className="grid grid-cols-3 gap-4">
        <PillarColumn
          tone="confirm"
          kicker="确定项 · CONFIRMED"
          count={`${confirmRows.length} 项`}
        >
          {confirmRows.map((it, i) => (
            <div
              key={`${it.tag}-${i}`}
              className={[
                'flex justify-between items-center py-2.5',
                i < confirmRows.length - 1 ? 'border-b border-line-0' : '',
              ].join(' ')}
            >
              <span className="text-[12.5px] text-fg-2">{it.tag}</span>
              <span className="text-[13px] font-medium">{it.value}</span>
            </div>
          ))}
        </PillarColumn>

        <PillarColumn
          tone="person"
          kicker="个性化项 · YOU"
          count={`${personRows.length} 项`}
        >
          {personRows.map((it) => (
            <div key={it.label} className="py-2">
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-[13px] font-medium">{it.label}</span>
              </div>
              <Score value={it.weight} color="var(--pillar-person)" />
              <div className="text-[11px] text-fg-3 mt-1.5 leading-relaxed">
                ↳ {it.evidence}
              </div>
            </div>
          ))}
        </PillarColumn>

        <PillarColumn
          tone="explore"
          kicker="待探索项 · OPEN"
          count={`${exploreRows.length} 项`}
        >
          {exploreRows.map((it) => (
            <button
              key={it.q}
              type="button"
              onClick={() => onAsk(`把「${it.q}」这一项展开聊聊`)}
              className="text-left p-3 rounded-md cursor-pointer flex flex-col gap-1.5"
              style={{
                background: 'rgba(122,78,196,0.05)',
                border: '1px dashed rgba(122,78,196,0.32)',
              }}
            >
              <div className="flex justify-between gap-2">
                <span className="text-[13px] font-medium text-fg-0">{it.q}</span>
                <ChevronRight size={14} className="text-pillar-explore flex-shrink-0 mt-0.5" />
              </div>
              <div className="text-[11px] text-pillar-explore font-mono tracking-wider uppercase">
                {it.status}
              </div>
              <div className="text-[11.5px] text-fg-2 leading-relaxed">{it.hint}</div>
            </button>
          ))}
        </PillarColumn>
      </div>

      <AudienceCard data={seed.audience} />
      <HistoryStrip
        items={
          profile && (profile.audit_log?.length ?? 0) > 0
            ? // backend audit_log → HistoryStrip 的 Item 形状
              profile.audit_log!.slice(-7).map((e, i) => {
                const at = (e as Record<string, unknown>).at
                return {
                  date:
                    typeof at === 'string' ? at.slice(5, 10) : `v${i + 1}`,
                  label: `v${i + 1}`,
                  ticks: 2 + (i % 4),
                }
              })
            : seed.history_strip
        }
      />
    </div>
  )
}
