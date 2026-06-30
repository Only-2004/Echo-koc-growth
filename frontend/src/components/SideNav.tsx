/**
 * Echo · 左侧导航
 *
 * - logo + wordmark
 * - 4 nav 按钮（首页 / 我的画像 / 选题策略 / 复盘）
 * - profileReady=false 时后 3 个置灰锁死
 * - 底部 user 卡（小A · 1,238 粉 · 抖音）
 */

import { Home, Lightbulb, ChartBar, Lock, Sparkles, User } from 'lucide-react'
import type { Scene } from '../store/app'
import { useAppStore } from '../store/app'

interface NavItemDef {
  scene: Scene
  label: string
  icon: typeof Home
  requiresProfile: boolean
}

const NAV_ITEMS: NavItemDef[] = [
  { scene: 'home', label: '首页', icon: Home, requiresProfile: false },
  { scene: 'profile', label: '我的画像', icon: User, requiresProfile: true },
  { scene: 'ideate', label: '选题策略', icon: Lightbulb, requiresProfile: true },
  { scene: 'retro', label: '复盘', icon: ChartBar, requiresProfile: true },
]

export function SideNav() {
  const scene = useAppStore((s) => s.scene)
  const profileReady = useAppStore((s) => s.profileReady)
  const setScene = useAppStore((s) => s.setScene)

  return (
    <div className="flex flex-col h-full p-4 gap-6">
      <div className="flex items-center gap-2 px-2">
        <Sparkles size={20} className="text-accent" />
        <span className="font-semibold tracking-tight text-fg-0">Echo</span>
      </div>

      <div className="space-y-1">
        {NAV_ITEMS.map((item) => {
          const locked = item.requiresProfile && !profileReady
          const active = scene === item.scene
          const Icon = item.icon
          return (
            <button
              key={item.scene}
              type="button"
              onClick={() => {
                if (locked) return
                setScene(item.scene)
              }}
              disabled={locked}
              className={[
                'w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition',
                active ? 'bg-accent-soft text-accent' : 'text-fg-1 hover:bg-bg-2',
                locked ? 'opacity-55 text-fg-3 cursor-not-allowed hover:bg-transparent' : '',
              ].join(' ')}
            >
              <Icon size={16} />
              <span className="flex-1 text-left">{item.label}</span>
              {locked && <Lock size={12} className="text-fg-3" />}
            </button>
          )
        })}
      </div>

      <div className="flex-1" />

      <div className="border border-line-1 rounded-lg p-3 bg-bg-2">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-pill bg-pillar-explore/20 flex items-center justify-center text-pillar-explore text-xs font-medium">
            小A
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-fg-0 truncate">小A</div>
            <div className="text-[10px] text-fg-2">1,238 粉 · 抖音</div>
          </div>
        </div>
      </div>
    </div>
  )
}
