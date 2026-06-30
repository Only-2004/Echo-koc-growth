/**
 * 三个 agent 的输出类型（与 backend pydantic schema 对齐 · 演示路径必备字段）
 *
 * 设计取舍：
 * - 不追求 1:1 还原 pydantic 全部字段；只覆盖前端渲染会读的字段
 * - 多余字段用 ``[k: string]: unknown`` 兜住，避免 backend 加字段时前端 typecheck 红
 * - source tag 与 backend ``VALID_SOURCE_TAGS`` 一致（5 类）
 *
 * 详见 ``backend/schemas/{profile,strategy,insights}.py``。
 */

/** 与 backend strategy.service.VALID_SOURCE_TAGS 对齐。*/
export type SourceTag =
  | '画像驱动'
  | '趋势驱动'
  | '数据驱动'
  | '历史复盘'
  | '用户偏好驱动'

// =====================================================================
// Profile（onboarding 输出 · retro 输入）
// =====================================================================

export interface ProfileMeta {
  user_id: string
  version: number
  created_at: string
  session_id: string
}

export interface ContentPillar {
  name: string
  evidence_video_ids: string[]
  validated_at: string | null
}

export interface ConfirmedPillars {
  audience_baseline: Record<string, string | number>
  content_pillars: ContentPillar[]
  content_style: Record<string, string | number>
}

export interface PersonaTrait {
  trait: string
  evidence: Array<Record<string, unknown>>
}

export interface LifeContextItem {
  context: string
  valid_until: string | null
  evidence: Array<Record<string, unknown>>
}

export interface UniqueAsset {
  description: string
  evidence: Array<Record<string, unknown>>
}

export interface PersonalizedAssets {
  persona_traits: PersonaTrait[]
  life_context: LifeContextItem[]
  unique_assets: UniqueAsset[]
}

export interface Hypothesis {
  hypothesis_id: string
  hypothesis: string
  status: 'pending' | 'supported' | 'rejected' | string
  evidence_for: Array<Record<string, unknown>>
  evidence_against: Array<Record<string, unknown>>
}

export interface OpenQuestion {
  question_id?: string
  question: string
  evidence?: Array<Record<string, unknown>>
}

export interface ToExploreSection {
  open_questions: OpenQuestion[]
  hypotheses: Hypothesis[]
  aspirations: string[]
}

export interface Profile {
  meta: ProfileMeta
  confirmed: ConfirmedPillars
  personalized: PersonalizedAssets
  to_explore: ToExploreSection
  audit_log: Array<Record<string, unknown>>
  [k: string]: unknown
}

// =====================================================================
// StrategySnapshot（strategy submit 输出）
// =====================================================================

export interface HeatAnalysis {
  trend_score: number
  trend_direction: string
  supply_demand_ratio?: number
  matched_trends: string[]
  comment?: string
  trend_curve?: Array<{ date: string; value: number } | Record<string, unknown>>
  [k: string]: unknown
}

export type AlignmentLevel = 'high' | 'medium' | 'low'

export interface PillarAlignment {
  pillar: string
  alignment: AlignmentLevel
  evidence: string
}

export interface ProfileFit {
  pillar_alignment: PillarAlignment[]
  persona_leverage: Array<Record<string, unknown>>
  to_explore_validation: Array<Record<string, unknown>>
  fit_score: number
  [k: string]: unknown
}

export interface DifferentiationItem {
  point: string
  source: SourceTag | string
  angle?: string
}

export interface ExecutionPlan {
  hook: Record<string, unknown>
  pacing?: Record<string, unknown> | string
  cta?: Record<string, unknown> | string
  tags?: string[]
  key_focus?: string
  [k: string]: unknown
}

export interface StrategySnapshot {
  strategy_id: string
  user_id: string
  profile_version: number
  generated_at: string
  input?: Record<string, unknown>
  idea?: Record<string, unknown>
  heat_analysis: HeatAnalysis
  profile_fit: ProfileFit
  differentiation: DifferentiationItem[]
  execution: ExecutionPlan
  sources?: SourceTag[]
  [k: string]: unknown
}

// =====================================================================
// InsightsReport（retro 输出 · 与 backend/schemas/insights.py 对齐）
// =====================================================================

export type Verdict = 'hit' | 'miss' | 'exceed' | 'within_noise' | 'partial'

export interface DataCard {
  card_id: string
  metric: string
  value: number
  baseline_overall?: number | null
  baseline_pillar?: number | null
  verdict: Verdict
  is_key_indicator?: boolean
  [k: string]: unknown
}

export interface StrategyReviewItem {
  predicted: string
  actual: string
  verdict: Verdict
  evidence?: Array<Record<string, string>>
  [k: string]: unknown
}

export interface InsightEvidence {
  type: 'drop_off' | 'comment' | 'metric' | 'audience' | 'transcript' | string
  ref: string
  snippet?: string | null
}

export type ConfidenceLevel = 'high' | 'medium' | 'low'

export interface Insight {
  insight_id: string
  claim: string
  evidence: InsightEvidence[]
  confidence: ConfidenceLevel
  caveat?: string | null
  linked_card_ids?: string[]
  linked_strategy_fields?: string[]
  [k: string]: unknown
}

export type AudienceSignalCategory =
  | 'unmet_request'
  | 'new_audience_segment'
  | 'strategy_feedback_positive'
  | 'strategy_feedback_negative'

export interface AudienceSignal {
  signal_id: string
  signal: string
  category?: AudienceSignalCategory | null
  evidence_comments: string[]
  [k: string]: unknown
}

export interface Suggestion {
  suggestion_id: string
  type: 'iterate' | 'test_new' | 'pivot' | 'hold'
  content: string
  linked_insight_ids?: string[]
  estimated_effort: 'low' | 'medium' | 'high'
}

export interface ProfileDelta {
  add_evidence?: Array<Record<string, unknown>>
  promote?: Array<Record<string, unknown>>
  new_observations?: Array<Record<string, unknown>>
  [k: string]: unknown
}

export interface InsightsReport {
  report_id: string
  user_id: string
  video_id: string
  strategy_id: string
  profile_version_in: number
  generated_at?: string
  data_cards: DataCard[]
  strategy_review: StrategyReviewItem[]
  insights: Insight[]
  audience_signals: AudienceSignal[]
  suggestions: Suggestion[]
  profile_delta?: ProfileDelta | null
  [k: string]: unknown
}
