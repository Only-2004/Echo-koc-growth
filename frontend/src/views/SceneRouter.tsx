/**
 * Beacon · Scene 路由（M3 完整实现）
 *
 * 根据 store.scene + profileReady 显示不同视图：
 *   profileReady=false:
 *     - home    → EmptyHomeView
 *     - onboard → OnboardView
 *     - 其它 scene → 强制跳回 home（gate 兜底，PRD 红线 #3）
 *   profileReady=true:
 *     - home    → HomeView
 *     - profile → ProfileView
 *     - ideate  → IdeateView
 *     - retro   → RetroView
 *     - onboard → OnboardView（用户也可主动重跑 onboarding）
 */

import { useEffect } from 'react'
import { useAppStore } from '../store/app'
import { EmptyHomeView } from './EmptyHomeView'
import { OnboardView } from './OnboardView'
import { ProfileView } from './ProfileView'
import { IdeateView } from './IdeateView'
import { RetroView } from './RetroView'
import { HomeView } from './HomeView'

export function SceneRouter() {
  const scene = useAppStore((s) => s.scene)
  const profileReady = useAppStore((s) => s.profileReady)
  const setScene = useAppStore((s) => s.setScene)

  // gate 兜底：profileReady=false 时被锁的 scene 强制回 home
  useEffect(() => {
    if (!profileReady && (scene === 'profile' || scene === 'ideate' || scene === 'retro')) {
      setScene('home')
    }
  }, [scene, profileReady, setScene])

  if (scene === 'onboard') return <OnboardView />
  if (!profileReady && scene === 'home') return <EmptyHomeView />
  if (scene === 'home') return <HomeView />
  if (scene === 'profile') return <ProfileView />
  if (scene === 'ideate') return <IdeateView />
  return <RetroView />
}
