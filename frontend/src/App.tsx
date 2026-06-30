/**
 * Beacon · App 入口
 *
 * Shell 包住 SceneRouter。Boot 时调 GET /api/profile/status 同步 profileReady：
 * - exists=true  → 加载最新 profile，setProfileReady(true)
 * - exists=false → setProfileReady(false)，停在 EmptyHome
 *
 * 右下角浮窗保留一个调试按钮：
 * - 冷/热启动 toggle（profileReady 仅前端门控，不删 runtime profile；用于跳关 demo）
 *
 * LLM 缓存策略统一由 ``USE_CACHED_ANALYSIS`` 环境变量控制（默认 true，演示一律走 cache）；
 * 前端不再有 cache/live toggle。
 */

import { useEffect } from 'react'
import { Shell } from './components/Shell'
import { SceneRouter } from './views/SceneRouter'
import { useAppStore } from './store/app'
import { getLatestProfile, getProfileStatus } from './api/profile'
import { reportError } from './lib/clientErrorReporter'

function ProfileReadyToggle() {
  const profileReady = useAppStore((s) => s.profileReady)
  const setProfileReady = useAppStore((s) => s.setProfileReady)
  return (
    <button
      type="button"
      onClick={() => setProfileReady(!profileReady)}
      className="fixed bottom-4 right-4 z-20 text-[10px] font-mono px-2.5 py-1 rounded-pill bg-bg-3 text-fg-2 hover:bg-bg-3/80 transition"
      title="冷启动 = 没有画像，进入 onboarding；热启动 = 已有画像，直接看 home（仅前端门控，不删 runtime profile）"
    >
      {profileReady ? '🔥 热启动（已有画像）' : '🧊 冷启动（无画像）'}
    </button>
  )
}

function App() {
  const setProfileReady = useAppStore((s) => s.setProfileReady)
  const setProfile = useAppStore((s) => s.setProfile)

  // Boot 时同步 profile 状态（M4-M6 闭环：runtime_data/profile_v*.json 决定 gate）
  useEffect(() => {
    let cancelled = false
    const sync = async () => {
      try {
        const status = await getProfileStatus()
        if (cancelled) return
        if (status.exists) {
          const profile = await getLatestProfile()
          if (cancelled) return
          setProfile(profile)
          setProfileReady(true)
        } else {
          setProfileReady(false)
        }
      } catch (err) {
        // backend 没起 / 网络错 → 保持初始值（profileReady=false），让 EmptyHome 兜底
        const message = err instanceof Error ? err.message : String(err)
        const stack = err instanceof Error ? err.stack : undefined
        reportError({
          kind: 'fetch',
          message: `[boot] profile status sync 失败：${message}`,
          stack,
        })
      }
    }
    void sync()
    return () => {
      cancelled = true
    }
  }, [setProfile, setProfileReady])

  return (
    <>
      <Shell>
        <SceneRouter />
      </Shell>
      <ProfileReadyToggle />
    </>
  )
}

export default App
