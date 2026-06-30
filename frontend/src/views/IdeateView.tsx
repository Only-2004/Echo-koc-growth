/**
 * IdeateView — 选题策略主视图（M5 闭环 · T29）
 *
 * 流程：
 *   1) 默认 idea 「考研期间一日三餐怎么吃才能不困」（PRD §6.4 demo 默认）
 *   2) 用户提交 → SSE submitStrategy → 顶部进度条 (ANALYZE_IDEA → SCORE → STRATEGIZE → PRESENT)
 *   3) done 时拿 snapshot_id → getStrategySnapshot → setStrategySnapshot
 *   4) 4 tab 由 strategy_snapshot 派生：
 *      - 评估（profile_fit）：3 FitBar + notes
 *      - 趋势（heat_analysis）：4 metric + sparkline
 *      - 差异化（differentiation）：4 角度卡
 *      - 节奏（execution）：hook + pacing + cta + tags
 *   5) 「我对这条策略想再聊聊」按钮 → 打开 chat dock，REFINE 路由由 ChatDock scene-aware 处理（T30）
 *
 * 不再读 strategy_seed.json（已下线）；snapshot 为 null 时显示 empty state 提示提交 idea。
 */

import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  Loader2,
  RefreshCw,
  Sparkles,
  Zap,
} from 'lucide-react'
import { runStrategySubmit } from '../api/strategyRunner'
import { useAppStore } from '../store/app'
import { MarkdownMessage } from '../components/chat/MarkdownMessage'
import type { SourceKey } from './_shared/SourceBadge'
import { useOnAsk } from './_shared/useOnAsk'
import { DiffTab } from './ideate/DiffTab'
import { EvalTab } from './ideate/EvalTab'
import { ScoreCard } from './ideate/ScoreCard'
import { TrendTab } from './ideate/TrendTab'
import type { StrategySnapshot } from '../types/agents'

type TabId = 'heat' | 'fit' | 'diff'

const DEFAULT_IDEA =
  '下一期想拍：「考研期间一日三餐怎么吃才能不困」 — 用半纪录片半干货的口吻，跟拍我自己一周早中晚三餐 + 学习状态的对照。'

const STATE_PROGRESS: Record<string, { idx: number; label: string }> = {
  RECEIVE_IDEA: { idx: 0, label: '接收 idea' },
  ANALYZE_IDEA: { idx: 1, label: '解读 idea' },
  SCORE: { idx: 2, label: '评分四象限' },
  STRATEGIZE: { idx: 3, label: '生成策略' },
  PRESENT: { idx: 4, label: '呈现' },
}

/** 把 backend ``differentiation[].source`` 映射到前端 SourceBadge 的 SourceKey。*/
function mapDiffSource(s: string): SourceKey {
  switch (s) {
    case '画像驱动':
    case '用户偏好驱动':
      return 'profile'
    case '趋势驱动':
      return 'trend'
    case '数据驱动':
    case '历史复盘':
      return 'data'
    default:
      return 'profile'
  }
}

function safeNumber(v: unknown, fallback = 0): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string') {
    const n = parseFloat(v)
    if (Number.isFinite(n)) return n
  }
  return fallback
}

function safeString(v: unknown, fallback = '-'): string {
  if (typeof v === 'string' && v) return v
  if (typeof v === 'number') return String(v)
  return fallback
}

export function IdeateView() {
  const snapshot = useAppStore((s) => s.strategySnapshot)
  const setScene = useAppStore((s) => s.setScene)
  const submitting = useAppStore((s) => s.strategySubmitting)
  const progressState = useAppStore((s) => s.strategyProgressState)
  const streamingPresent = useAppStore((s) => s.strategyStreamingText)
  const thinkingText = useAppStore((s) => s.strategyThinkingText)
  const error = useAppStore((s) => s.strategyError)
  const onAsk = useOnAsk()

  const pendingIdeaFromChat = useAppStore((s) => s.pendingIdeaFromChat)

  const [tab, setTab] = useState<TabId>('heat')
  const [idea, setIdea] = useState(DEFAULT_IDEA)
  const [thinkingOpen, setThinkingOpen] = useState(false)

  // 右侧聊天确认选题后自动填入主面板并生成
  useEffect(() => {
    if (!pendingIdeaFromChat) return
    const topic = pendingIdeaFromChat
    useAppStore.getState().setPendingIdeaFromChat(null)
    setIdea(topic)
    void runStrategySubmit(topic)
  }, [pendingIdeaFromChat])

  function handleSubmit() {
    if (submitting || !idea.trim()) return
    void runStrategySubmit(idea.trim())
  }

  // -------------------- snapshot → 4 tab 数据派生 --------------------
  const derived = useMemo(() => {
    if (!snapshot) return null
    return deriveTabData(snapshot)
  }, [snapshot])

  const progress = STATE_PROGRESS[progressState] ?? STATE_PROGRESS.RECEIVE_IDEA
  const hasSnapshot = !!snapshot && !!derived

  // 提取到 JSX 外部，避免 Vite 8 / rolldown 在 JSX 表达式内解析 `as const` 崩溃
  const PROGRESS_STEPS = ['ANALYZE_IDEA', 'SCORE', 'STRATEGIZE', 'PRESENT'] as const

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-6 flex flex-col gap-6">
      {/* Idea input */}
      <div className="bg-bg-1 border border-line-1 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb size={16} className="text-accent" />
          <span className="text-kicker text-accent">YOUR IDEA</span>
          {snapshot && (
            <span className="font-mono text-[11px] text-fg-3 ml-auto">
              snapshot {snapshot.strategy_id}
            </span>
          )}
        </div>
        <textarea
          className="w-full bg-bg-inset border border-line-1 rounded-md px-3.5 py-3 text-[15px] leading-relaxed tracking-tight text-fg-0 resize-none focus:outline-none focus:border-accent"
          rows={3}
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          disabled={submitting}
        />
        <div className="flex gap-2 mt-4 flex-wrap items-center">
          <button
            type="button"
            onClick={() => onAsk('帮我把这条 idea 改得更聚焦一些')}
            disabled={submitting}
            className="px-3 py-1.5 rounded-pill border border-line-1 text-fg-1 text-sm flex items-center gap-1.5 hover:bg-bg-2 transition disabled:opacity-50"
          >
            <RefreshCw size={14} /> 修改这套idea
          </button>
          <button
            type="button"
            onClick={() => onAsk('帮我看看还有哪些可以拍的 idea')}
            disabled={submitting}
            className="px-3 py-1.5 rounded-pill border border-line-1 text-fg-1 text-sm flex items-center gap-1.5 hover:bg-bg-2 transition disabled:opacity-50"
          >
            <Sparkles size={14} /> 给我 3 个相邻方向
          </button>
          <div className="flex-1" />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            className="px-3.5 py-1.5 rounded-pill bg-accent text-accent-ink text-sm font-medium flex items-center gap-1.5 hover:bg-accent/90 transition disabled:opacity-60"
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {submitting ? `生成中 · ${progress.label}` : '生成完整拍摄简报'}
          </button>
        </div>
        {/* progress bar */}
        {submitting && (
          <div className="mt-4 flex items-center gap-2">
            {PROGRESS_STEPS.map(
              (st) => {
                const stepIdx = STATE_PROGRESS[st]?.idx ?? 0
                const active = (STATE_PROGRESS[progressState]?.idx ?? 0) >= stepIdx
                return (
                  <div
                    key={st}
                    className={[
                      'flex-1 h-1 rounded-sm transition-all',
                      active ? 'bg-accent' : 'bg-bg-3',
                    ].join(' ')}
                  />
                )
              },
            )}
          </div>
        )}
        {error && (
          <div className="mt-3 text-sm text-neg bg-neg-soft border border-neg/30 rounded-md px-3 py-2">
            生成策略失败：{error}
          </div>
        )}
      </div>

      {/* Empty state */}
      {!hasSnapshot && !submitting && (
        <div className="bg-bg-1 border border-line-1 rounded-xl p-8 text-center text-fg-2">
          <Lightbulb size={24} className="mx-auto mb-3 text-accent" />
          <div className="text-[15px] text-fg-1">还没有策略</div>
        </div>
      )}

      {/* 思考过程面板（生成中可见，thinking token 流式展示）*/}
      {thinkingText && (
        <div className="bg-bg-1 border border-line-1 rounded-xl overflow-hidden">
          <button
            type="button"
            onClick={() => setThinkingOpen((o) => !o)}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-xs text-fg-3 hover:bg-bg-2 transition text-left"
          >
            {thinkingOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            <span className="font-mono">思考过程 · THINKING</span>
            {submitting && <Loader2 size={11} className="animate-spin ml-auto" />}
          </button>
          {thinkingOpen && (
            <div className="px-4 pb-4 max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed text-fg-3 whitespace-pre-wrap border-t border-line-1 pt-3">
              {thinkingText}
            </div>
          )}
        </div>
      )}

      {/* 流式 PRESENT 临时展示（done 后 4 tab 接管，但 PRESENT 文本仍是有用的解读）*/}
      {streamingPresent && (
        <div className="bg-bg-1 border border-line-1 rounded-xl p-6">
          <MarkdownMessage text={streamingPresent} pending={submitting} />
        </div>
      )}

      {/* 4-pillar score row */}
      {hasSnapshot && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <ScoreCard
              active={tab === 'heat'}
              onClick={() => setTab('heat')}
              kicker="01 · 热度匹配度"
              score={derived.heatScore}
              verdict={derived.heatVerdict}
              tone="info"
            />
            <ScoreCard
              active={tab === 'fit'}
              onClick={() => setTab('fit')}
              kicker="02 · 画像贴合度"
              score={derived.fitScore}
              verdict={derived.fitVerdict}
              tone="person"
            />
            <ScoreCard
              active={tab === 'diff'}
              onClick={() => setTab('diff')}
              kicker="03 · 差异化空间"
              score={derived.diffScore}
              verdict={`${derived.diffItems.length} 个可切入的独特角度`}
              tone="explore"
            />
          </div>

          {/* Active tab content */}
          <div className="bg-bg-1 border border-line-1 rounded-lg p-7 min-h-[400px]">
            {tab === 'heat' && (
              <TrendTab
                verdict={derived.heatVerdict}
                metrics={derived.heatMetrics}
                spark={derived.heatSpark}
              />
            )}
            {tab === 'fit' && (
              <EvalTab
                matchConfirm={derived.fit.matchConfirm}
                matchPerson={derived.fit.matchPerson}
                exploreValue={derived.fit.exploreValue}
                notes={derived.fit.notes}
              />
            )}
            {tab === 'diff' && <DiffTab items={derived.diffItems} />}
          </div>

          <div className="bg-bg-inset border border-line-1 rounded-md px-4 py-3 flex items-center gap-3 flex-wrap">
            <button
              type="button"
              onClick={() => setScene('retro')}
              className="text-xs px-3 py-1.5 rounded-pill bg-accent text-accent-ink hover:bg-accent/90 transition flex items-center gap-1.5"
              title="假设这条 idea 已发布 → 看 retro 复盘"
            >
              假设已发布 · 看复盘
              <ArrowRight size={12} />
            </button>
          </div>
        </>
      )}
    </div>
  )
}

// =====================================================================
// 适配层：StrategySnapshot → 4 tab 的 props
// =====================================================================

interface DerivedTabData {
  heatScore: number
  heatVerdict: string
  heatMetrics: { label: string; value: string; trend: 'up' | 'down' | 'flat'; hint: string }[]
  heatSpark: number[]
  fitScore: number
  fitVerdict: string
  fit: {
    matchConfirm: number
    matchPerson: number
    exploreValue: number
    notes: { source: SourceKey; text: string }[]
  }
  diffScore: number
  diffItems: { angle: string; text: string; source: SourceKey }[]
  exec: {
    hook: { sec: string; text: string }
    pacing: { at: string; what: string }[]
    cta: string
    tags: string[]
  }
}

function deriveTabData(s: StrategySnapshot): DerivedTabData {
  // ---------- HEAT ----------
  const heatScore = safeNumber(s.heat_analysis?.trend_score, 0.5)
  const heatVerdict =
    safeString(s.heat_analysis?.comment, '') ||
    `趋势 ${safeString(s.heat_analysis?.trend_direction, 'flat')}`
  const matched = (s.heat_analysis?.matched_trends ?? []) as string[]
  const heatMetrics = [
    {
      label: '匹配的趋势主题',
      value: matched.length ? matched.slice(0, 2).join(' / ') : '-',
      trend: 'flat' as const,
      hint: '',
    },
    {
      label: '热度方向',
      value: safeString(s.heat_analysis?.trend_direction, '-'),
      trend:
        s.heat_analysis?.trend_direction === 'rising'
          ? ('up' as const)
          : s.heat_analysis?.trend_direction === 'falling'
          ? ('down' as const)
          : ('flat' as const),
      hint: '',
    },
    {
      label: '供给/需求比',
      value: String(safeNumber(s.heat_analysis?.supply_demand_ratio, 0).toFixed(2)),
      trend:
        safeNumber(s.heat_analysis?.supply_demand_ratio, 1) < 1
          ? ('down' as const)
          : ('flat' as const),
      hint: '<1 = 供给不足，红利期',
    },
    {
      label: 'trend_score',
      value: String(heatScore.toFixed(2)),
      trend: 'flat' as const,
      hint: '0-1 综合评分',
    },
  ]
  // sparkline 优先用 trend_curve；否则放一个占位（视觉用）
  const curveRaw = s.heat_analysis?.trend_curve as
    | Array<{ value?: number } | number>
    | undefined
  const heatSpark = curveRaw && curveRaw.length
    ? curveRaw.map((p) =>
        typeof p === 'number' ? p : safeNumber((p as { value?: number }).value, 0),
      )
    : [18, 22, 28, 26, 33, 38, 47, 52, 58, 65, 76, 70, 78]

  // ---------- FIT ----------
  // pillar_alignment 现在是 high/medium/low 三档，前端为了保留 4 列条形图
  // 视觉，用一个固定 mapping 把等级映射回 0-1 数值（仅用于 UI 渲染，
  // 不再代表 AI 给的数值评分）
  const alignmentToWeight = (lvl: unknown): number => {
    if (lvl === 'high') return 0.92
    if (lvl === 'medium') return 0.66
    if (lvl === 'low') return 0.33
    if (typeof lvl === 'number') return lvl  // 旧缓存兜底
    return 0
  }
  const pillars = (s.profile_fit?.pillar_alignment ?? []).map((x) =>
    alignmentToWeight(x.alignment),
  )
  const matchConfirm = pillars[0] ?? 0
  const matchPerson = pillars[1] ?? matchConfirm
  const exploreValue = safeNumber(s.profile_fit?.fit_score, 0.5)
  const fitVerdict =
    pillars.length > 0
      ? '高度贴合 · 还能验证待探索项'
      : '匹配度待评估'

  const notes: { source: SourceKey; text: string }[] = []
  for (const align of s.profile_fit?.pillar_alignment ?? []) {
    notes.push({
      source: 'profile',
      text: `${align.pillar}：${safeString(align.evidence, '-')}`,
    })
  }
  // persona_leverage 也作为 note
  for (const lev of s.profile_fit?.persona_leverage ?? []) {
    const trait = safeString((lev as Record<string, unknown>).trait, '画像')
    const how = safeString((lev as Record<string, unknown>).how_to_use, '-')
    notes.push({ source: 'profile', text: `${trait} → ${how}` })
  }
  // to_explore_validation
  for (const v of s.profile_fit?.to_explore_validation ?? []) {
    const what = safeString((v as Record<string, unknown>).what_this_tests, '验证假设')
    notes.push({ source: 'explore', text: what })
  }

  // ---------- DIFF ----------
  const diffItems = (s.differentiation ?? []).map((d, i) => ({
    angle: safeString(d.angle, `角度 ${i + 1}`),
    text: safeString(d.point, '-'),
    source: mapDiffSource(safeString(d.source, '画像驱动')),
  }))
  const diffScore = diffItems.length > 0 ? Math.min(0.6 + diffItems.length * 0.05, 0.95) : 0.5

  // ---------- EXEC ----------
  const exec = s.execution ?? {}
  const hookRaw = (exec.hook ?? {}) as Record<string, unknown>
  const hook = {
    sec: safeString(hookRaw.sec, '0-3s'),
    text: safeString(hookRaw.text ?? hookRaw.line, '（hook 缺失）'),
  }
  const pacingRaw = (exec.pacing ?? {}) as Record<string, unknown>
  // backend pacing 可能是 array 或 dict-of-beat；都兼容
  let pacing: { at: string; what: string }[] = []
  if (Array.isArray(pacingRaw)) {
    pacing = (pacingRaw as Array<Record<string, unknown>>).map((b) => ({
      at: safeString(b.at, '-'),
      what: safeString(b.what ?? b.text, '-'),
    }))
  } else if (pacingRaw && typeof pacingRaw === 'object') {
    pacing = Object.entries(pacingRaw).map(([at, what]) => ({
      at,
      what: typeof what === 'string' ? what : JSON.stringify(what),
    }))
  }
  const ctaRaw = (exec.cta ?? '') as unknown
  const cta = typeof ctaRaw === 'string'
    ? ctaRaw
    : safeString((ctaRaw as Record<string, unknown>)?.text, '-')
  const tagsRaw = (exec.tags ?? []) as unknown
  const tags = Array.isArray(tagsRaw) ? (tagsRaw as string[]) : []

  return {
    heatScore,
    heatVerdict,
    heatMetrics,
    heatSpark,
    fitScore: exploreValue,
    fitVerdict,
    fit: { matchConfirm, matchPerson, exploreValue, notes },
    diffScore,
    diffItems,
    exec: { hook, pacing, cta, tags },
  }
}
