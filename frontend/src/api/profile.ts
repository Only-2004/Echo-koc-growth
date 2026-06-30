/**
 * /api/profile/* 客户端
 */

import type { Profile } from '../types/agents'
import { fetchJson, fetchJsonWithRetry, type RetryConfig } from './sse'

export interface ProfileStatus {
  exists: boolean
  latest_version: number | null
  user_id: string | null
  available_versions: number[]
}

/** 状态查询不走 retry（boot 时太多 retry 会卡住界面）。失败 caller 处理。*/
export async function getProfileStatus(): Promise<ProfileStatus> {
  return fetchJson<ProfileStatus>('/api/profile/status')
}

export async function getLatestProfile(retry?: RetryConfig): Promise<Profile> {
  return fetchJsonWithRetry<Profile>('/api/profile/', {}, retry)
}

export async function getProfileByVersion(
  version: number,
  retry?: RetryConfig,
): Promise<Profile> {
  return fetchJsonWithRetry<Profile>(`/api/profile/${version}`, {}, retry)
}

export interface ResetResult {
  reset_to: number
  deleted: string[]
  latest_version: number
}

export async function resetDemo(): Promise<ResetResult> {
  return fetchJson<ResetResult>('/api/profile/reset', {
    method: 'POST',
  })
}
