/**
 * Echo 全局状态（Zustand）
 *
 * M2 初版只覆盖 scene + chat dock + profileReady gate；
 * M4-M6 闭环扩展了三个 agent 的会话句柄。
 *
 * 字段分组：
 * - 路由层：scene / chatOpen
 * - Onboarding gate：profileReady（仅前端门控，冷/热启动 toggle 用）
 * - 会话句柄：sessionId / snapshotId / reportId
 * - 数据缓存：profile / strategySnapshot / insightsReport
 * - 聊天 log：按 scene 隔离
 * - profile.tick LIVE rail：onboardTicks（onboarding 期间累积，finalize 后清空）
 *
 * LLM 缓存策略统一由后端 ``USE_CACHED_ANALYSIS`` 环境变量控制，前端不再切换。
 */

import { create } from 'zustand'
import type {
  InsightsReport,
  Profile,
  SourceTag,
  StrategySnapshot,
} from '../types/agents'

export type Scene = 'home' | 'profile' | 'ideate' | 'retro' | 'onboard'

export type ChatMessage =
  | { role: 'system'; text: string }
  | { role: 'user'; text: string }
  | { role: 'ai'; text: string; sources?: SourceTag[]; suggestions?: string[]; pending?: boolean; thinkingText?: string; usedFallback?: boolean }

export interface ProfileTick {
  /** 接收时间（前端 Date.now()）。*/
  receivedAt: number
  /** 后端 profile.tick patch 原始内容。*/
  patch: Record<string, unknown>
}

interface AppState {
  // 路由
  scene: Scene
  chatOpen: boolean

  // Onboarding gate
  profileReady: boolean

  // 会话句柄（前端贯穿三阶段）
  sessionId: string | null
  snapshotId: string | null
  reportId: string | null

  // 数据缓存（agent 输出落库）
  profile: Profile | null
  strategySnapshot: StrategySnapshot | null
  insightsReport: InsightsReport | null

  // 聊天 log 按 scene 隔离
  chatLog: Record<Scene, ChatMessage[]>

  // Onboarding LIVE rail（profile.tick 流）
  onboardTicks: ProfileTick[]

  // Strategy 生成进度（全局保留，切场景后仍可回看）
  strategySubmitting: boolean
  strategyProgressState: string
  strategyStreamingText: string
  strategyThinkingText: string
  strategyError: string | null

  // Retro 分析进度（全局保留，切场景后分析继续在后台跑）
  retroLoading: boolean
  retroStageIdx: number
  retroThinkingText: string
  retroError: string | null

  // Retro 前端缓存（按 videoId 缓存分析结果，实现视频间即时切换）
  retroAnalysisCache: Record<string, { report: InsightsReport; presentText: string; reportId: string }>
  retroPreloadingIds: string[]

  // Ideate 聊天发现的选题 → 自动填入主面板并生成
  pendingIdeaFromChat: string | null

  // ----- setters -----
  setScene: (scene: Scene) => void
  toggleChat: () => void
  openChat: () => void
  closeChat: () => void
  setProfileReady: (ready: boolean) => void
  setSessionId: (id: string | null) => void
  setSnapshotId: (id: string | null) => void
  setReportId: (id: string | null) => void
  setProfile: (profile: Profile | null) => void
  setStrategySnapshot: (snapshot: StrategySnapshot | null) => void
  setInsightsReport: (report: InsightsReport | null) => void
  appendChatTurn: (scene: Scene, msg: ChatMessage) => void
  updateLastAiMessage: (scene: Scene, mutator: (msg: ChatMessage) => ChatMessage) => void
  clearChatLog: (scene: Scene) => void
  appendOnboardTick: (tick: ProfileTick) => void
  resetOnboardTicks: () => void
  setStrategySubmitting: (v: boolean) => void
  setStrategyProgressState: (s: string) => void
  appendStrategyStreamingText: (chunk: string) => void
  setStrategyStreamingText: (text: string) => void
  appendStrategyThinkingText: (chunk: string) => void
  resetStrategyStreaming: () => void
  setStrategyError: (e: string | null) => void
  setRetroLoading: (v: boolean) => void
  setRetroStageIdx: (v: number) => void
  appendRetroThinkingText: (chunk: string) => void
  setRetroThinkingText: (text: string) => void
  setRetroError: (e: string | null) => void
  setRetroAnalysisCache: (videoId: string, entry: { report: InsightsReport; presentText: string; reportId: string }) => void
  addRetroPreloadingId: (videoId: string) => void
  removeRetroPreloadingId: (videoId: string) => void
  setPendingIdeaFromChat: (idea: string | null) => void
  resetForNewUser: () => void
}

const emptyLog: Record<Scene, ChatMessage[]> = {
  home: [],
  profile: [],
  ideate: [],
  retro: [],
  onboard: [],
}

export const useAppStore = create<AppState>((set) => ({
  scene: 'home',
  chatOpen: false,
  profileReady: false,
  sessionId: null,
  snapshotId: null,
  reportId: null,
  profile: null,
  strategySnapshot: null,
  insightsReport: null,
  chatLog: emptyLog,
  onboardTicks: [],
  strategySubmitting: false,
  strategyProgressState: 'RECEIVE_IDEA',
  strategyStreamingText: '',
  strategyThinkingText: '',
  strategyError: null,
  retroLoading: false,
  retroStageIdx: 0,
  retroThinkingText: '',
  retroError: null,
  retroAnalysisCache: {},
  retroPreloadingIds: [],
  pendingIdeaFromChat: null,

  setScene: (scene) => set({ scene }),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  openChat: () => set({ chatOpen: true }),
  closeChat: () => set({ chatOpen: false }),
  setProfileReady: (profileReady) => set({ profileReady }),
  setSessionId: (sessionId) => set({ sessionId }),
  setSnapshotId: (snapshotId) => set({ snapshotId }),
  setReportId: (reportId) => set({ reportId }),
  setProfile: (profile) => set({ profile }),
  setStrategySnapshot: (strategySnapshot) => set({ strategySnapshot }),
  setInsightsReport: (insightsReport) => set({ insightsReport }),
  appendChatTurn: (scene, msg) =>
    set((s) => ({ chatLog: { ...s.chatLog, [scene]: [...s.chatLog[scene], msg] } })),
  updateLastAiMessage: (scene, mutator) =>
    set((s) => {
      const list = s.chatLog[scene]
      if (list.length === 0) return s
      const last = list[list.length - 1]
      if (last.role !== 'ai') return s
      const updated = [...list.slice(0, -1), mutator(last)]
      return { chatLog: { ...s.chatLog, [scene]: updated } }
    }),
  clearChatLog: (scene) =>
    set((s) => ({ chatLog: { ...s.chatLog, [scene]: [] } })),
  appendOnboardTick: (tick) =>
    set((s) => ({ onboardTicks: [...s.onboardTicks, tick] })),
  resetOnboardTicks: () => set({ onboardTicks: [] }),
  setStrategySubmitting: (strategySubmitting) => set({ strategySubmitting }),
  setStrategyProgressState: (strategyProgressState) => set({ strategyProgressState }),
  appendStrategyStreamingText: (chunk) =>
    set((s) => ({ strategyStreamingText: s.strategyStreamingText + chunk })),
  setStrategyStreamingText: (strategyStreamingText) => set({ strategyStreamingText }),
  appendStrategyThinkingText: (chunk) =>
    set((s) => ({ strategyThinkingText: s.strategyThinkingText + chunk })),
  resetStrategyStreaming: () =>
    set({ strategyStreamingText: '', strategyThinkingText: '', strategyProgressState: 'RECEIVE_IDEA', strategyError: null }),
  setStrategyError: (strategyError) => set({ strategyError }),
  setRetroLoading: (retroLoading) => set({ retroLoading }),
  setRetroStageIdx: (retroStageIdx) => set({ retroStageIdx }),
  appendRetroThinkingText: (chunk) =>
    set((s) => ({ retroThinkingText: s.retroThinkingText + chunk })),
  setRetroThinkingText: (retroThinkingText) => set({ retroThinkingText }),
  setRetroError: (retroError) => set({ retroError }),
  setRetroAnalysisCache: (videoId, entry) =>
    set((s) => ({ retroAnalysisCache: { ...s.retroAnalysisCache, [videoId]: entry } })),
  addRetroPreloadingId: (videoId) =>
    set((s) => ({ retroPreloadingIds: [...s.retroPreloadingIds, videoId] })),
  removeRetroPreloadingId: (videoId) =>
    set((s) => ({ retroPreloadingIds: s.retroPreloadingIds.filter((id) => id !== videoId) })),
  setPendingIdeaFromChat: (pendingIdeaFromChat) => set({ pendingIdeaFromChat }),
  resetForNewUser: () =>
    set({
      scene: 'home',
      chatOpen: false,
      profileReady: false,
      sessionId: null,
      snapshotId: null,
      reportId: null,
      profile: null,
      strategySnapshot: null,
      insightsReport: null,
      chatLog: emptyLog,
      onboardTicks: [],
      strategySubmitting: false,
      strategyProgressState: 'RECEIVE_IDEA',
      strategyStreamingText: '',
      strategyThinkingText: '',
      strategyError: null,
      retroLoading: false,
      retroStageIdx: 0,
      retroThinkingText: '',
      retroError: null,
      retroAnalysisCache: {},
      retroPreloadingIds: [],
      pendingIdeaFromChat: null,
    }),
}))

/** 是否为新用户（profile 未生成）。组件可用此判断是否走 EmptyHome。 */
export const useIsNewUser = (): boolean => !useAppStore((s) => s.profileReady)

/** 把 SourceTag 类型重新导出，方便组件 import。*/
export type { SourceTag } from '../types/agents'
