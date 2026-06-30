/**
 * OnboardView — Onboarding agent 主面板（M4 闭环 · T25）
 *
 * 流程：
 *   1) mount → POST /api/onboarding/start → 拿 session_id + candidate_claims
 *   2) 渲染 candidate_claims 作为系统提示
 *   3) 自动触发第一次 turn(user_text=null) → SSE 流式开场白（PRESENT）
 *   4) 用户 composer 输入 → turn(user_text=...) → SSE
 *      - message.delta → 累积当前 AI 气泡
 *      - message.complete → 落 sources + 解锁 composer
 *      - profile.tick → LIVE rail append
 *      - state.transition → 顶部进度条
 *      - finish.ready → 显示「生成画像 →」CTA
 *   5) 点 CTA → POST /api/onboarding/finalize → setProfile + setProfileReady(true) → 跳 /profile
 *
 * UI 复刻 hi-fi prototype（左主对话 · 右 sticky LIVE rail）。
 * 数据来源：完全 backend；不再读 onboarding_turns.json mock。
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Brain,
  ChevronDown,
  ChevronUp,
  Loader2,
  Mic,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import {
  finalizeOnboardingStream,
  startOnboarding,
  turnOnboarding,
  type CandidateClaim,
  type OnboardingEvent,
} from '../api/onboarding'
import { LlmConnectionError, type RetryAttemptInfo } from '../api/sse'
import { MarkdownMessage } from '../components/chat/MarkdownMessage'
import { SourceChips } from '../components/chat/SourceChips'
import { useAppStore, type ChatMessage, type ProfileTick } from '../store/app'

const STATE_LABEL: Record<string, { idx: number; label: string }> = {
  ANALYZE: { idx: 0, label: '分析账号' },
  PRESENT: { idx: 1, label: '提出假设' },
  VALIDATE: { idx: 2, label: '验证回答' },
  EXPLORE: { idx: 2, label: '继续追问' },
  SUMMARIZE: { idx: 3, label: '总结对话' },
  FINALIZE: { idx: 3, label: '生成画像' },
}

const TONE_LABEL = {
  confirmed: '确定项',
  personalized: '个性化项',
  to_explore: '待探索项',
  default: '更新',
} as const

const TONE_DOT = {
  confirmed: 'bg-pillar-confirm',
  personalized: 'bg-pillar-person',
  to_explore: 'bg-pillar-explore',
  default: 'bg-fg-2',
} as const

type TickTone = keyof typeof TONE_LABEL

interface RailItem {
  tone: TickTone
  label: string
  time: string
}

function nowHHMM(d = new Date()): string {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const ACTION_PREFIX: Record<string, string> = {
  confirm: '✓ 确认',
  modify: '✎ 调整',
  reject: '✕ 否认',
  move_to_explore: '⤴ 移到待探索',
}

const CATEGORY_TONE: Record<string, TickTone> = {
  content_pillar: 'confirmed',
  persona_trait: 'personalized',
  life_context: 'personalized',
  open_question: 'to_explore',
  hypothesis: 'to_explore',
}

const CATEGORY_LABEL: Record<string, string> = {
  content_pillar: '内容主轴',
  persona_trait: '个性化特质',
  life_context: '生活上下文',
  open_question: '开放问题',
  hypothesis: '假设',
}

/**
 * 把 backend profile.tick patch 拆成若干条 LIVE rail 可读条目。
 * patch 形如 { actions: [{claim_id, action, new_text?}], new_observations: [{category, claim_text, proposed_state}] }
 */
function patchToRailItems(
  patch: Record<string, unknown>,
  claimMap: Map<string, string>,
  receivedAt: number,
): RailItem[] {
  const items: RailItem[] = []
  const time = nowHHMM(new Date(receivedAt))

  const actions = Array.isArray(patch.actions) ? (patch.actions as Record<string, unknown>[]) : []
  for (const a of actions) {
    const cid = typeof a.claim_id === 'string' ? a.claim_id : ''
    const action = typeof a.action === 'string' ? a.action : 'confirm'
    const newText = typeof a.new_text === 'string' ? a.new_text : ''
    const original = claimMap.get(cid) ?? cid
    const prefix = ACTION_PREFIX[action] ?? '·'
    const text = action === 'modify' && newText ? `${prefix}：${newText}` : `${prefix}：${original}`
    const tone: TickTone =
      action === 'reject' ? 'default' : action === 'move_to_explore' ? 'to_explore' : 'confirmed'
    items.push({ tone, label: text, time })
  }

  const obs = Array.isArray(patch.new_observations)
    ? (patch.new_observations as Record<string, unknown>[])
    : []
  for (const o of obs) {
    const cat = typeof o.category === 'string' ? o.category : 'open_question'
    const claimText = typeof o.claim_text === 'string' ? o.claim_text : ''
    const tone = CATEGORY_TONE[cat] ?? 'to_explore'
    const catLabel = CATEGORY_LABEL[cat] ?? '观察'
    items.push({ tone, label: `+ ${catLabel}：${claimText}`, time })
  }

  // 兜底：patch 既无 actions 也无 new_observations 时仍记录一条
  if (items.length === 0) {
    items.push({ tone: 'default', label: '收到一轮回答', time })
  }

  return items
}

export function OnboardView() {
  const sessionId = useAppStore((s) => s.sessionId)
  const setSessionId = useAppStore((s) => s.setSessionId)
  const setProfile = useAppStore((s) => s.setProfile)
  const setProfileReady = useAppStore((s) => s.setProfileReady)
  const setScene = useAppStore((s) => s.setScene)
  const chatLog = useAppStore((s) => s.chatLog.onboard)
  const appendChatTurn = useAppStore((s) => s.appendChatTurn)
  const updateLastAiMessage = useAppStore((s) => s.updateLastAiMessage)
  const onboardTicks = useAppStore((s) => s.onboardTicks)
  const appendOnboardTick = useAppStore((s) => s.appendOnboardTick)
  const resetOnboardTicks = useAppStore((s) => s.resetOnboardTicks)

  const [candidates, setCandidates] = useState<CandidateClaim[]>([])
  const [candidatesExpanded, setCandidatesExpanded] = useState(false)
  const [currentState, setCurrentState] = useState<string>('PRESENT')
  const [finishReady, setFinishReady] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [composer, setComposer] = useState('')
  const [bootError, setBootError] = useState<string | null>(null)
  const [finalizing, setFinalizing] = useState(false)
  const [finalizeThinking, setFinalizeThinking] = useState('')
  const [finalizeThinkingOpen, setFinalizeThinkingOpen] = useState(true)
  const [retryStatus, setRetryStatus] = useState<RetryAttemptInfo | null>(null)
  const [paused, setPaused] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  // 把 onAttempt 回调统一处理：attempt>1 或带 error 才显示重试 banner
  function handleRetryAttempt(info: RetryAttemptInfo) {
    if (info.attempt === 1 && !info.error) {
      setRetryStatus(null)
    } else {
      setRetryStatus(info)
    }
  }

  function clearRetry() {
    setRetryStatus(null)
  }

  // -------------------- boot --------------------
  // React 18 StrictMode 下 effect 会双跑：mount → unmount → mount。
  // 这里不用 startedRef 拦截，纯靠 `cancelled` 让上一轮 boot 的 setState 失效；
  // backend onboarding.start 走 cache 模式 < 1s，双跑成本忽略。
  useEffect(() => {
    let cancelled = false
    const boot = async () => {
      try {
        resetOnboardTicks()
        setFinishReady(false)
        setPaused(false)
        const res = await startOnboarding({ onAttempt: handleRetryAttempt })
        if (cancelled) return
        clearRetry()
        setSessionId(res.session_id)
        setCurrentState(res.state)
        setCandidates(res.candidate_claims)
        appendChatTurn('onboard', {
          role: 'system',
          text: `已分析你的历史视频，整理出 ${res.candidate_claims.length} 条假设。`,
        })
        // 第一次 turn 用 res.session_id（不依赖 store commit 时机）
        if (cancelled) return
        await runTurn(res.session_id, null)
      } catch (err) {
        if (cancelled) return
        if (err instanceof LlmConnectionError) {
          setPaused(true)
          setRetryStatus(null)
          return
        }
        // eslint-disable-next-line no-console
        console.error('[onboard] boot failed', err)
        setBootError(err instanceof Error ? err.message : String(err))
      }
    }
    void boot()
    return () => {
      cancelled = true
      abortRef.current?.abort()
    }
    // boot 仅运行一次：StrictMode 下双跑由 cancelled flag 兜底
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // -------------------- turn driver --------------------
  async function runTurn(sid: string, userText: string | null) {
    if (!sid) return

    abortRef.current?.abort()
    abortRef.current = new AbortController()
    setStreaming(true)

    // 占位 AI 消息（流式累积）
    appendChatTurn('onboard', { role: 'ai', text: '', pending: true })

    try {
      for await (const ev of turnOnboarding(
        { session_id: sid, user_text: userText },
        abortRef.current.signal,
        { onAttempt: handleRetryAttempt },
      )) {
        handleEvent(ev)
      }
      clearRetry()
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return
      if (err instanceof LlmConnectionError) {
        setPaused(true)
        setRetryStatus(null)
        updateLastAiMessage('onboard', (m) => ({
          ...m,
          text: (m as Extract<ChatMessage, { role: 'ai' }>).text || '（LLM 连接失败）',
          pending: false,
        }))
        return
      }
      // eslint-disable-next-line no-console
      console.error('[onboard] turn stream error', err)
      updateLastAiMessage('onboard', (m) => ({
        ...m,
        text: (m as Extract<ChatMessage, { role: 'ai' }>).text +
          '\n\n（连接中断，请重新提交）',
        pending: false,
      }))
    } finally {
      setStreaming(false)
    }
  }

  function handleEvent(ev: OnboardingEvent): void {
    switch (ev.type) {
      case 'state.transition':
        setCurrentState(ev.to)
        return
      case 'thinking.delta':
        updateLastAiMessage('onboard', (m) => {
          const ai = m as Extract<ChatMessage, { role: 'ai' }>
          return { ...ai, thinkingText: (ai.thinkingText ?? '') + ev.text }
        })
        return
      case 'message.delta':
        updateLastAiMessage('onboard', (m) => ({
          ...m,
          text: (m as Extract<ChatMessage, { role: 'ai' }>).text + ev.text,
        }))
        return
      case 'message.complete':
        updateLastAiMessage('onboard', (m) => {
          const ai = m as Extract<ChatMessage, { role: 'ai' }>
          const incoming = typeof ev.text === 'string' ? ev.text.trim() : ''
          const accumulated = ai.text.trim()
          // 1) backend 给了 clean 正文 → 用 incoming 覆盖累积 buffer
          if (incoming.length > 0) {
            return {
              ...ai,
              text: incoming,
              sources: ev.sources ?? ai.sources,
              pending: false,
            }
          }
          // 2) backend 给了空 text，但前端 buffer 有累积 → 保留 buffer
          if (accumulated.length > 0) {
            return {
              ...ai,
              sources: ev.sources ?? ai.sources,
              pending: false,
            }
          }
          // 3) 双空：LLM 这一轮输出异常（backend 已 fallback_injected
          //    "数据驱动" tag 但正文空）。提示用户重新表达，不展示 fallback chip
          //    避免误导（chip 不代表真实归因）。
          return {
            ...ai,
            text: '⚠️ LLM 这次回复异常（输出为空）。请试着把问题说得更具体一些，再发一次。',
            sources: [],
            pending: false,
          }
        })
        return
      case 'profile.tick': {
        const tick: ProfileTick = { receivedAt: Date.now(), patch: ev.patch }
        appendOnboardTick(tick)
        return
      }
      case 'finish.ready':
        setFinishReady(true)
        return
      case 'error':
        // eslint-disable-next-line no-console
        console.warn('[onboard] backend error event', ev.message)
        return
    }
  }

  // -------------------- composer submit --------------------
  async function handleSubmit() {
    const text = composer.trim()
    if (!text || streaming) return
    const sid = useAppStore.getState().sessionId
    if (!sid) return
    setComposer('')
    appendChatTurn('onboard', { role: 'user', text })
    await runTurn(sid, text)
  }

  // -------------------- finalize --------------------
  async function handleFinish() {
    const sid = useAppStore.getState().sessionId
    if (!sid || finalizing) return
    setFinalizing(true)
    setFinalizeThinking('')
    setFinalizeThinkingOpen(true)
    try {
      for await (const ev of finalizeOnboardingStream(
        sid,
        undefined,
        { onAttempt: handleRetryAttempt },
      )) {
        if (ev.type === 'thinking.delta') {
          setFinalizeThinking((prev) => prev + ev.text)
        } else if (ev.type === 'profile.ready') {
          clearRetry()
          setProfile(ev.profile as import('../types/agents').Profile)
          setProfileReady(true)
          setScene('profile')
          return
        } else if (ev.type === 'error') {
          alert(`生成画像失败：${ev.message}`)
          return
        }
      }
    } catch (err) {
      if (err instanceof LlmConnectionError) {
        setPaused(true)
        setRetryStatus(null)
      } else {
        // eslint-disable-next-line no-console
        console.error('[onboard] finalize failed', err)
        alert(`生成画像失败：${err instanceof Error ? err.message : String(err)}`)
      }
    } finally {
      setFinalizing(false)
    }
  }

  const stepInfo = STATE_LABEL[currentState] ?? STATE_LABEL.PRESENT
  const stepTotal = 4

  // 把 backend profile.tick patch 流派生成 LIVE rail 可读条目
  const railItems = useMemo(() => {
    const claimMap = new Map(candidates.map((c) => [c.claim_id, c.claim_text]))
    const all: RailItem[] = []
    for (const t of onboardTicks) {
      all.push(...patchToRailItems(t.patch, claimMap, t.receivedAt))
    }
    return all
  }, [onboardTicks, candidates])
  const visibleTickCount = railItems.length

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-6 flex flex-col gap-6">
      {/* Top header + progress */}
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-[28px] font-semibold tracking-tight">
            创建你的画像
          </div>
          <div className="text-fg-2 text-sm mt-1.5 max-w-[640px] leading-relaxed">
            我会从聊天中提取信息凝练成你的画像。
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-fg-2">
            {stepInfo.label} · 第 {stepInfo.idx + 1} 步 / 共 {stepTotal} 步
          </span>
          <div className="flex gap-1">
            {Array.from({ length: stepTotal }).map((_, i) => (
              <div
                key={i}
                className={[
                  'w-8 h-1 rounded-sm',
                  i <= stepInfo.idx ? 'bg-accent' : 'bg-bg-3',
                ].join(' ')}
              />
            ))}
          </div>
        </div>
      </div>

      {/* LLM retry / paused 状态条 */}
      {paused ? (
        <div className="bg-neg-soft border border-neg/40 rounded-md px-4 py-3 flex items-center gap-3">
          <AlertTriangle size={16} className="text-neg flex-shrink-0" />
          <div className="flex-1 text-sm text-neg">
            <strong>LLM 连接错误</strong>，已暂停 agent。请刷新页面重试。
          </div>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="text-xs px-3 py-1.5 rounded-pill bg-neg text-neg-soft hover:opacity-90 transition flex items-center gap-1.5"
          >
            <RefreshCw size={12} /> 刷新
          </button>
        </div>
      ) : retryStatus && (retryStatus.attempt > 1 || retryStatus.error) ? (
        <div className="bg-warn-soft border border-warn/40 rounded-md px-4 py-3 flex items-center gap-3">
          <Loader2 size={16} className="text-warn flex-shrink-0 animate-spin" />
          <div className="flex-1 text-sm text-warn">
            LLM 连接错误，正在重试 ({retryStatus.attempt}/{retryStatus.max})…
          </div>
        </div>
      ) : null}

      {/* Two-column: chat + live profile rail */}
      <div className="grid grid-cols-[1fr_360px] gap-4 items-start">
        {/* Conversation surface */}
        <div className="bg-bg-1 border border-line-1 rounded-xl min-h-[520px] px-7 py-6 space-y-4">
          {bootError && (
            <div className="text-sm text-neg bg-neg-soft border border-neg/30 rounded-md px-4 py-3">
              连接 onboarding agent 失败：{bootError}
              <br />
              <span className="text-xs text-fg-2">
                请确认后端在 8000 端口运行（uvicorn backend.main:app）。
              </span>
            </div>
          )}

          {/* candidate_claims 摘要（可展开） */}
          {candidates.length > 0 && (
            <div className="bg-bg-inset border border-line-1 rounded-md px-4 py-3 text-[12.5px] text-fg-1 space-y-1.5">
              <div className="flex items-center justify-between mb-1">
                <div className="text-kicker text-fg-2">
                  候选假设 · {candidates.length} 条
                </div>
                <button
                  type="button"
                  onClick={() => setCandidatesExpanded((v) => !v)}
                  className="text-[11px] text-fg-2 hover:text-fg-0 transition flex items-center gap-1"
                >
                  {candidatesExpanded ? (
                    <>
                      收起 <ChevronUp size={12} />
                    </>
                  ) : (
                    <>
                      展开全部 <ChevronDown size={12} />
                    </>
                  )}
                </button>
              </div>
              {(candidatesExpanded ? candidates : candidates.slice(0, 4)).map((c) => (
                <div key={c.claim_id} className="flex items-start gap-2">
                  <span
                    className={[
                      'w-1.5 h-1.5 rounded-pill mt-1.5 flex-shrink-0',
                      c.proposed_state === 'confirmed'
                        ? 'bg-pillar-confirm'
                        : c.proposed_state === 'personalized'
                        ? 'bg-pillar-person'
                        : 'bg-pillar-explore',
                    ].join(' ')}
                  />
                  <span className="leading-snug">{c.claim_text}</span>
                </div>
              ))}
              {!candidatesExpanded && candidates.length > 4 && (
                <button
                  type="button"
                  onClick={() => setCandidatesExpanded(true)}
                  className="text-fg-3 text-[11px] hover:text-fg-0 transition cursor-pointer"
                >
                  + 还有 {candidates.length - 4} 条，点击展开
                </button>
              )}
            </div>
          )}

          {/* Chat log */}
          {chatLog.map((m, i) => (
            <ChatBubble key={i} m={m} />
          ))}

          {streaming && (
            <div className="flex items-center gap-2 text-fg-3 text-xs pl-1">
              <Loader2 size={12} className="animate-spin" />
              生成中…
            </div>
          )}

          {/* Composer */}
          <div className="flex items-center gap-2.5 px-3.5 py-3 bg-bg-inset border border-line-1 rounded-md text-fg-3 text-sm mt-2">
            <Mic size={14} />
            <input
              className="flex-1 bg-transparent outline-none text-fg-0 placeholder:text-fg-3"
              placeholder={
                streaming ? '正在生成回复…' : '说说你的想法…（按 ⏎ 发送）'
              }
              value={composer}
              disabled={streaming || !sessionId}
              onChange={(e) => setComposer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void handleSubmit()
                }
              }}
            />
            <span className="kbd">⏎</span>
          </div>

          {/* Finish CTA */}
          {finishReady && (
            <div className="mt-4 flex flex-col gap-3 px-4 py-3.5 bg-accent-soft border border-accent-line rounded-md">
              <div className="flex items-center gap-3">
                <Sparkles size={16} className="text-accent flex-shrink-0" />
                <div className="flex-1 text-[12.5px] text-fg-1 leading-relaxed">
                  我已经收集到 {visibleTickCount} 个信号，可以先生成第一版画像。
                </div>
                <button
                  type="button"
                  onClick={() => void handleFinish()}
                  disabled={finalizing}
                  className="px-3 py-1.5 rounded-md bg-accent text-white text-[12px] font-medium hover:bg-accent/90 disabled:opacity-60 disabled:cursor-not-allowed transition flex items-center gap-1.5 flex-shrink-0"
                >
                  {finalizing ? (
                    <>
                      <Loader2 size={12} className="animate-spin" />
                      生成中...
                    </>
                  ) : (
                    <>
                      生成画像
                      <ArrowRight size={12} />
                    </>
                  )}
                </button>
              </div>
              {/* thinking panel：生成中实时显示 */}
              {finalizing && (
                <div className="border border-line-1 rounded-md overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setFinalizeThinkingOpen((v) => !v)}
                    className="w-full flex items-center justify-between px-3 py-1.5 bg-bg-inset text-[11px] text-fg-2 hover:bg-bg-2 transition"
                  >
                    <span className="font-mono tracking-wider flex items-center gap-1.5">
                      <Loader2 size={10} className="animate-spin" />
                      思考过程 · THINKING
                    </span>
                    {finalizeThinkingOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>
                  {finalizeThinkingOpen && (
                    <div className="px-3 py-2 text-[11px] text-fg-2 leading-relaxed whitespace-pre-wrap font-mono bg-bg-0 max-h-[200px] overflow-y-auto">
                      {finalizeThinking || '（等待模型开始推理…）'}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Live profile rail */}
        <div className="sticky top-[72px] flex flex-col gap-3">
          <div className="bg-bg-1 border border-line-1 rounded-lg p-5">
            <div className="flex items-center gap-2 mb-1">
              <Brain size={14} className="text-accent" />
              <div className="text-kicker text-accent">LIVE</div>
            </div>
            <div className="text-[15px] font-semibold mb-4">已提取的画像信息</div>
            <div className="flex flex-col gap-2.5">
              {railItems.map((it, i) => (
                <div key={i} className="flex items-start gap-2.5">
                  <div
                    className={[
                      'w-1.5 h-1.5 rounded-pill mt-[7px] flex-shrink-0',
                      TONE_DOT[it.tone],
                    ].join(' ')}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-[12.5px] text-fg-0 leading-snug">{it.label}</div>
                    <div className="text-[10.5px] text-fg-3 font-mono mt-0.5">
                      {TONE_LABEL[it.tone]} · {it.time}
                    </div>
                  </div>
                </div>
              ))}
              {streaming && (
                <div className="flex items-center gap-2.5 text-fg-3 text-[11.5px] mt-1">
                  <DotPulse />
                  <span>正在分析你最新一句回答…</span>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

function ChatBubble({ m }: { m: ChatMessage }) {
  if (m.role === 'system') {
    return <div className="text-center text-[11px] text-fg-2 font-mono py-2">{m.text}</div>
  }
  if (m.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-accent text-accent-ink rounded-lg rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">
          {m.text}
        </div>
      </div>
    )
  }
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2 text-sm text-fg-0 leading-relaxed">
        <MarkdownMessage
          text={m.text}
          thinkingText={m.thinkingText}
          pending={m.pending}
        />
        {m.sources && m.sources.length > 0 && <SourceChips sources={m.sources} />}
        {m.suggestions && m.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {m.suggestions.map((s) => (
              <button
                key={s}
                type="button"
                className="text-xs px-3 py-1 rounded-pill border border-line-1 text-fg-1 hover:bg-bg-2 transition"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DotPulse() {
  return (
    <span
      className="w-2 h-2 rounded-pill bg-accent"
      style={{ animation: 'beacon-pulse 1.4s infinite' }}
    />
  )
}
