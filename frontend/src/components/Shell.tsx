/**
 * Beacon · App Shell
 *
 * 3 列 grid：220 / 1fr / 420，chat dock 折叠时第三列收到 0px。
 * 顶部 sticky bar，左侧 nav rail，主内容区由 children 占。
 */

import type { ReactNode } from 'react'
import { useAppStore } from '../store/app'
import { SideNav } from './SideNav'
import { TopBar } from './TopBar'
import { ChatDock } from './chat/ChatDock'

interface ShellProps {
  children: ReactNode
}

export function Shell({ children }: ShellProps) {
  const chatOpen = useAppStore((s) => s.chatOpen)

  return (
    <div
      className="grid h-screen"
      style={{
        gridTemplateColumns: chatOpen ? '220px 1fr 420px' : '220px 1fr 0px',
        transition: 'grid-template-columns 250ms ease',
      }}
    >
      <aside className="border-r border-line-1 bg-bg-1 overflow-y-auto">
        <SideNav />
      </aside>

      <main className="flex flex-col overflow-hidden">
        <TopBar />
        <div className="flex-1 overflow-y-auto">{children}</div>
      </main>

      <aside className="border-l border-line-1 bg-bg-1 overflow-hidden">
        {chatOpen && <ChatDock />}
      </aside>
    </div>
  )
}
