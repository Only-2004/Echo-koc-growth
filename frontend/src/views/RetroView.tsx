/**
 * RetroView — 复盘洞察主视图（M6 闭环 · T34 + T35）
 *
 * 流程：
 *   1) 进入 view 时若 reportId 已在 store → 直接渲染 store.insightsReport
 *      若 reportId 为空 → 自动 load 默认 video（vid_020，与 mock_data/new_video_for_retro.json 对齐）
 *   2) SSE handler：
 *      - stage   → 顶部进度条
 *      - report  → setReport(report_id) + 拿 draft 渲染
 *      - present → 累积 PRESENT 文本到 chat dock 的 retro scene（流式可读）
 *      - done    → finalize 视图
 *   3) 渲染：StrategyVsReality / 3 InsightCard（confidence top 3）/ CommentClusters
 *      KPI 行用 data_cards 派生（4 张卡）
 *   4) 「写回画像 →」按钮 → /api/retro/update-profile → setProfile(v2) + setScene('profile') + toast
 *
 * VideoList 仍用 frontend mock seed（演示历史故事线）；当前激活 video 与 backend
 * mock_data/new_video_for_retro.json 中的 video_id 一致（vid_020）。
 */

import { useEffect, useState } from 'react'
import { ArrowRight, ChevronDown, ChevronRight, Loader2, Sparkles } from 'lucide-react'
import { getProfileByVersion } from '../api/profile'
import { loadRetro, updateProfileFromRetro } from '../api/retro'
import { useAppStore } from '../store/app'
import { useOnAsk } from './_shared/useOnAsk'
import seed from '../data/insights_seed.json'
import { CommentClusters } from './retro/CommentClusters'
import { InsightCard, type InsightTone } from './retro/InsightCard'
import { KPI } from './retro/KPI'
import { StrategyVsReality } from './retro/StrategyVsReality'
import { VideoList } from './retro/VideoList'
import type {
  AudienceSignal,
  DataCard,
  Insight,
  InsightsReport,
  StrategyReviewItem,
  Suggestion,
  Verdict,
} from '../types/agents'
import type { SourceKey } from './_shared/SourceBadge'

const DEFAULT_VIDEO_ID = 'vid_020'

// 所有可分析视频 ID（与 insights_seed.json 对齐）
const ALL_VIDEO_IDS = (seed.videos as Array<{ id: string }>).map((v) => v.id)

// 模块级 preload 入口：mount 时启动所有视频的 cache-mode 加载，
// 写入 zustand 后跨 scene/视频卡片切换永久保留，无 abort 路径。
// 无 API key 也能跑：backend cache 文件已含 present_text，PRESENT 阶段不调 LLM。
async function preloadVideo(videoId: string): Promise<void> {
  const st = useAppStore.getState()
  if (st.retroAnalysisCache[videoId]) return
  if (st.retroPreloadingIds.includes(videoId)) return
  st.addRetroPreloadingId(videoId)
  try {
    let draft: Partial<InsightsReport> | null = null
    let presentText = ''
    let foundReportId = ''
    for await (const ev of loadRetro(videoId)) {
      if (ev.type === 'report') {
        draft = { ...(ev.draft as Partial<InsightsReport>), report_id: ev.report_id }
        foundReportId = ev.report_id
      } else if (ev.type === 'present') {
        presentText += ev.delta
      }
    }
    if (draft && foundReportId) {
      useAppStore.getState().setRetroAnalysisCache(videoId, {
        report: draft as InsightsReport,
        presentText,
        reportId: foundReportId,
      })
    }
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[retro] preload failed for', videoId, err)
  } finally {
    useAppStore.getState().removeRetroPreloadingId(videoId)
  }
}

const STAGE_PROGRESS: Record<string, number> = {
  LOAD: 0,
  COMPARE: 1,
  ATTRIBUTE: 2,
  EXTRACT_SIGNALS: 3,
  SYNTHESIZE: 4,
}

function verdictTone(v: Verdict | string): InsightTone {
  switch (v) {
    case 'miss':
      return 'neg'
    case 'within_noise':
      return 'warn'
    case 'partial':
      return 'warn'
    case 'exceed':
      return 'pos'
    case 'hit':
      return 'info'
    default:
      return 'info'
  }
}

function categoryToSentiment(
  c: AudienceSignal['category'] | undefined,
): 'pos' | 'neg' | 'warn' {
  switch (c) {
    case 'strategy_feedback_positive':
      return 'pos'
    case 'strategy_feedback_negative':
      return 'neg'
    case 'unmet_request':
    case 'new_audience_segment':
    default:
      return 'warn'
  }
}

const CONFIDENCE_RANK: Record<string, number> = { high: 3, medium: 2, low: 1 }

function confidenceToRank(c: unknown): number {
  if (typeof c === 'string' && c in CONFIDENCE_RANK) return CONFIDENCE_RANK[c]
  if (typeof c === 'number') return c // 旧缓存兜底
  return 0
}

const METRIC_ZH: Record<string, string> = {
  completion_rate: '完播率',
  follow_rate: '关注率',
  plays: '播放量',
  comment_rate: '评论率',
  share_rate: '转发率',
}

const METRIC_IS_RAW: Record<string, boolean> = {
  plays: true,
}

const CONFIDENCE_ZH: Record<string, string> = {
  high: '高把握',
  medium: '中把握',
  low: '低把握',
}

function pickInsightTopN(insights: Insight[], n: number): Insight[] {
  return [...insights]
    .sort((a, b) => confidenceToRank(b.confidence) - confidenceToRank(a.confidence))
    .slice(0, n)
}

function suggestionsForInsight(
  insight: Insight,
  allSuggestions: Suggestion[] | undefined,
): string[] {
  if (!allSuggestions) return []
  return allSuggestions
    .filter((s) => (s.linked_insight_ids ?? []).includes(insight.insight_id))
    .map((s) => s.content)
    .slice(0, 3)
}

export function RetroView() {
  const reportId = useAppStore((s) => s.reportId)
  const insightsReport = useAppStore((s) => s.insightsReport)
  const profile = useAppStore((s) => s.profile)
  const onAsk = useOnAsk()

  // 订阅缓存与预加载状态（zustand 自动追踪）
  const retroAnalysisCache = useAppStore((s) => s.retroAnalysisCache)
  const error = useAppStore((s) => s.retroError)

  const [activeVid, setActiveVid] = useState(DEFAULT_VIDEO_ID)
  const [updating, setUpdating] = useState(false)
  const [thinkingOpen, setThinkingOpen] = useState(false)

  const activeCache = retroAnalysisCache[activeVid]
  // 缓存就绪 = 不在加载；缓存未就绪 = loading（preload 还在跑）
  const loading = !activeCache
  // 进度条：缓存就绪显示 SYNTHESIZE（4），加载中显示 LOAD（0）
  const stageIdx = activeCache ? STAGE_PROGRESS.SYNTHESIZE : 0
  const thinkingText = ''

  // mount 时启动所有视频的 cache-mode 预加载（永不调 live LLM）
  // 不在 cleanup 中 abort：preload 完成的数据写入 zustand，跨 scene 切换持久化
  useEffect(() => {
    for (const vid of ALL_VIDEO_IDS) {
      void preloadVideo(vid)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 当 activeVid 的缓存就绪 / 切换视频时，把缓存数据同步到 store
  // 现有的 InsightCard / KPI / chat dock 等组件读 insightsReport 和 chatLogs
  useEffect(() => {
    const st = useAppStore.getState()
    st.setRetroError(null)
    st.setRetroThinkingText('')
    st.clearChatLog('retro')
    if (activeCache) {
      st.setInsightsReport(activeCache.report)
      st.setReportId(activeCache.reportId)
      st.setRetroLoading(false)
      st.setRetroStageIdx(STAGE_PROGRESS.SYNTHESIZE)
      if (activeCache.presentText) {
        st.appendChatTurn('retro', {
          role: 'ai',
          text: activeCache.presentText,
          pending: false,
        })
      }
    } else {
      st.setInsightsReport(null)
      st.setReportId(null)
      st.setRetroLoading(true)
      st.setRetroStageIdx(0)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeVid, activeCache])

  function handleVideoSelect(videoId: string) {
    if (videoId === activeVid) return
    // 切换 = 仅改 activeVid；上面 useEffect 自动同步缓存 → store
    setActiveVid(videoId)
    setThinkingOpen(false)
  }

  async function handleWriteBack() {
    if (!reportId || updating) return
    const profileVersionIn = profile?.meta.version ?? 1
    setUpdating(true)
    try {
      const result = await updateProfileFromRetro({
        report_id: reportId,
        profile_version_in: profileVersionIn,
      })
      const v2 = await getProfileByVersion(result.profile_version_out)
      const st = useAppStore.getState()
      st.setProfile(v2)
      st.setScene('profile')
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[retro] write-back failed', err)
      alert(`写回画像失败：${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setUpdating(false)
    }
  }

  // ----- 派生数据 -----
  const dataCards: DataCard[] = insightsReport?.data_cards ?? []
  const strategyReview: StrategyReviewItem[] = insightsReport?.strategy_review ?? []
  const insights: Insight[] = insightsReport?.insights ?? []
  const audienceSignals: AudienceSignal[] = insightsReport?.audience_signals ?? []
  const suggestions: Suggestion[] | undefined = insightsReport?.suggestions
  const topInsights = pickInsightTopN(insights, 3)

  // 4 KPI 卡（从 data_cards 取前 4 个；若不足，补 mock seed.kpis 兜底视觉）
  const kpiCards = dataCards.slice(0, 4)

  // strategy_review 拆成 strategy / reality 两列字符串
  const strategyLines = strategyReview.map((r) => r.predicted)
  const realityLines = strategyReview.map((r) => r.actual)

  // audience_signals → CommentClusters
  const clusters = audienceSignals.slice(0, 4).map((sig) => ({
    theme: sig.signal,
    n: sig.evidence_comments?.length ?? 0,
    sentiment: categoryToSentiment(sig.category),
    quote: sig.evidence_comments?.[0] ?? '',
  }))

  // 提取到 JSX 外部，避免 Vite 8 / rolldown 在 JSX 表达式内解析 `as const` 崩溃
  const RETRO_STEPS = ['LOAD', 'COMPARE', 'ATTRIBUTE', 'EXTRACT_SIGNALS', 'SYNTHESIZE'] as const

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-6 flex flex-col gap-6">
      {/* Top header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-kicker text-fg-2 mb-1.5">RETRO · 复盘</div>
          <div className="text-[28px] font-semibold tracking-tight">
            近期视频复盘
          </div>
        </div>
        {/* 写回画像 CTA */}
        {insightsReport && reportId && (
          <button
            type="button"
            onClick={handleWriteBack}
            disabled={updating}
            className="bg-accent text-accent-ink hover:bg-accent/90 transition px-4 py-2 rounded-pill text-[13px] font-semibold flex items-center gap-1.5 disabled:opacity-60"
            title="把本次复盘的 insight 合并回 profile 形成 v2"
          >
            {updating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
            {updating ? '写入中…' : '写回画像'}
            <ArrowRight size={12} />
          </button>
        )}
      </div>

      {/* Loading progress */}
      {loading && (
        <div className="bg-bg-1 border border-line-1 rounded-lg px-5 py-4">
          <div className="text-[12.5px] text-fg-1 mb-2 flex items-center gap-2">
            <Loader2 size={14} className="animate-spin text-accent" />
            正在跑 retro analysis · 阶段 {stageIdx + 1} / 5
          </div>
          <div className="flex gap-1.5">
            {RETRO_STEPS.map(
              (st, i) => (
                <div
                  key={st}
                  className={[
                    'flex-1 h-1 rounded-sm transition-all',
                    i <= stageIdx ? 'bg-accent' : 'bg-bg-3',
                  ].join(' ')}
                />
              ),
            )}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-neg-soft border border-neg/30 rounded-md px-4 py-3 text-sm text-neg">
          复盘加载失败：{error}
        </div>
      )}

      {/* Video selector strip */}
      <VideoList videos={seed.videos} activeId={activeVid} onSelect={handleVideoSelect} />

      {/* 思考过程面板（live 分析时展示） */}
      {thinkingText && (
        <div className="bg-bg-1 border border-line-1 rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => setThinkingOpen((o) => !o)}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-xs text-fg-3 hover:bg-bg-2 transition text-left"
          >
            {thinkingOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            <span className="font-mono">思考过程 · THINKING</span>
            {loading && <Loader2 size={11} className="animate-spin ml-auto" />}
          </button>
          {thinkingOpen && (
            <div className="px-4 pb-4 max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed text-fg-3 whitespace-pre-wrap border-t border-line-1 pt-3">
              {thinkingText}
            </div>
          )}
        </div>
      )}

      {/* KPI row（优先用 backend data_cards；不足时用 mock seed） */}
      <div className="grid grid-cols-4 gap-3">
        {kpiCards.length >= 4
          ? kpiCards.map((c) => {
              const baseline = c.baseline_pillar ?? c.baseline_overall ?? c.value
              const delta = baseline ? c.value - baseline : 0
              const isRaw = METRIC_IS_RAW[c.metric] ?? false
              const label = METRIC_ZH[c.metric] ?? c.metric
              const displayValue = isRaw
                ? Math.round(c.value).toLocaleString()
                : `${(c.value * 100).toFixed(1)}%`
              return (
                <KPI
                  key={c.card_id}
                  label={label}
                  value={displayValue}
                  delta={delta}
                  format={isRaw ? 'rel' : 'pp'}
                  spark={[18, 22, 28, 26, 33, 38, 47, 52]}
                  negativeIsBad
                  onDeepDive={() => onAsk(`深入解读「${label}」这个指标的原因`)}
                />
              )
            })
          : (
              <>
                <KPI
                  label="完播率"
                  value={`${Math.round(seed.kpis.completion.value * 100)}%`}
                  delta={seed.kpis.completion.delta}
                  format="pp"
                  spark={seed.kpis.completion.spark}
                  negativeIsBad
                  onDeepDive={() => onAsk('深入解读「完播率」这个指标的原因')}
                />
                <KPI
                  label="关注率"
                  value={seed.kpis.follow.value}
                  delta={seed.kpis.follow.delta}
                  format="rel"
                  spark={seed.kpis.follow.spark}
                  onDeepDive={() => onAsk('深入解读「新增关注」这个指标的原因')}
                />
                <KPI
                  label="播放量"
                  value={seed.kpis.share.value}
                  delta={seed.kpis.share.delta}
                  format="rel"
                  spark={seed.kpis.share.spark}
                  negativeIsBad
                  onDeepDive={() => onAsk('深入解读「转发」这个指标的原因')}
                />
                <KPI
                  label="评论率"
                  value={seed.kpis.sentiment.value}
                  delta={seed.kpis.sentiment.delta}
                  format="raw"
                  tone="warn"
                  onDeepDive={() => onAsk('深入解读「评论情感」这个指标的原因')}
                />
              </>
            )}
      </div>

      {/* Strategy vs reality */}
      {strategyLines.length > 0 ? (
        <StrategyVsReality strategy={strategyLines} reality={realityLines} />
      ) : (
        !loading && (
          <div className="bg-bg-1 border border-line-1 rounded-lg px-5 py-4 text-sm text-fg-2">
            AI 正在完成复盘分析...
          </div>
        )
      )}

      {/* Insights */}
      {topInsights.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {topInsights.map((ins, i) => {
            const tone = verdictTone(
              (insightsReport?.strategy_review?.[i]?.verdict ?? 'info') as Verdict,
            )
            const fallbackSugg =
              ins.evidence?.[0]?.snippet
                ? [`展开看「${ins.evidence[0].snippet.slice(0, 24)}…」的证据`]
                : []
            const sugg = suggestionsForInsight(ins, suggestions)
            const finalSugg = (sugg.length > 0 ? sugg : fallbackSugg).concat([
              '下一条视频应该如何调整？',
            ])
            // backend 没标 source，用 evidence type 推断
            const evType = ins.evidence?.[0]?.type ?? 'metric'
            const source: SourceKey =
              evType === 'comment'
                ? 'profile'
                : evType === 'audience'
                ? 'profile'
                : evType === 'transcript'
                ? 'data'
                : 'data'
            return (
              <InsightCard
                key={ins.insight_id}
                n={String(i + 1).padStart(2, '0')}
                tone={tone}
                title={ins.claim}
                body={ins.caveat ? `${ins.claim}\n\n${ins.caveat}` : ins.claim}
                metric={(() => {
                  const label = CONFIDENCE_ZH[ins.confidence as string]
                  if (label) return { label: '把握度', value: label }
                  // 旧缓存兜底（数字 confidence）
                  if (typeof ins.confidence === 'number' && ins.confidence > 0) {
                    return {
                      label: '把握度',
                      value: ins.confidence >= 0.75 ? '高把握' : ins.confidence >= 0.5 ? '中把握' : '低把握',
                    }
                  }
                  return undefined
                })()}
                source={source}
                suggestions={finalSugg.slice(0, 3)}
              />
            )
          })}
        </div>
      )}

      {/* Comment clusters */}
      {clusters.length > 0 ? (
        <CommentClusters clusters={clusters} />
      ) : (
        !loading && (
          <div className="bg-bg-1 border border-line-1 rounded-lg px-5 py-4 text-sm text-fg-2">
            暂无评论聚类
          </div>
        )
      )}
    </div>
  )
}
