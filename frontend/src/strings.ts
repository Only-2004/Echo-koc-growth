/**
 * T59: 集中管理所有 UI 文案
 *
 * 兜底 / 占位 / 错误文案统一从此文件引用，避免散落各处导致口径不一致。
 * Source tag 中文翻译也统一在此。
 */

import type { SourceTag } from './types/agents'

// ─── Source tag 翻译映射 ──────────────────────────────────────────────
export const SOURCE_TAG_LABELS: Record<SourceTag, string> = {
  '画像驱动': '画像驱动',
  '趋势驱动': '趋势驱动',
  '数据驱动': '数据驱动',
  '历史复盘': '历史复盘',
  '用户偏好驱动': '用户偏好',
}

export const SOURCE_TAG_COLORS: Record<SourceTag, string> = {
  '画像驱动': 'var(--pillar-confirm, #22c55e)',
  '趋势驱动': 'var(--info, #3b82f6)',
  '数据驱动': 'var(--warn, #f59e0b)',
  '历史复盘': 'var(--info, #3b82f6)',
  '用户偏好驱动': 'var(--pillar-confirm, #22c55e)',
}

// ─── Chat Dock 占位文案 ───────────────────────────────────────────────
export const CHAT_PLACEHOLDER = '输入消息，或点击页面上的元素发起对话...'
export const CHAT_SENDING = 'AI 正在思考...'
export const CHAT_RETRY_PREFIX = '重试中'
export const CHAT_PAUSED = 'LLM 连接中断，已使用缓存响应'

// ─── 错误兜底文案 ─────────────────────────────────────────────────────
export const ERROR_LLM_UNAVAILABLE = 'AI 服务暂时不可用，已为你展示缓存数据。'
export const ERROR_NETWORK = '网络连接失败，请检查网络后重试。'
export const ERROR_GENERIC = '请求失败，请稍后再试。'

// ─── Onboarding ───────────────────────────────────────────────────────
export const ONBOARDING_START_CTA = '开始对话 →'
export const ONBOARDING_FINISH_CTA = '生成画像 →'
export const ONBOARDING_FINISH_LABEL = '已经够了'
export const ONBOARDING_PROGRESS_PREFIX = '第 {current} 步 / 共 {total} 步'

// ─── Profile ──────────────────────────────────────────────────────────
export const PROFILE_UPDATED_TOAST = '画像已更新到 v{version}'
export const PROFILE_LOCKED_HINT = '完成 Onboarding 后解锁'

// ─── Ideate ───────────────────────────────────────────────────────────
export const IDEATE_SUBMIT_PLACEHOLDER = '输入你的选题想法...'
export const IDEATE_NO_SNAPSHOT = '请先提交一个选题想法'

// ─── Retro ────────────────────────────────────────────────────────────
export const RETRO_WRITE_PROFILE_CTA = '写回画像'
export const RETRO_SINGLE_VIDEO_CAVEAT = '这是单条视频信号，需要再 2-3 条同向数据才能形成稳定结论。'

// ─── Home ─────────────────────────────────────────────────────────────
export const HOME_GREETING = '欢迎回来'
export const HOME_NEXT_ACTIONS = ['复盘新视频', '选题策略', '查看画像'] as const
