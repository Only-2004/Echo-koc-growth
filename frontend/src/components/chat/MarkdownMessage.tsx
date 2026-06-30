/**
 * MarkdownMessage — AI 消息的 markdown 渲染组件。
 *
 * 功能：
 * 1. 用 react-markdown 渲染基础 markdown（**bold**, *italic*, 列表）
 * 2. 内联 citation 引用（cmt_XXXX）自动转为上标 [评N]，hover 显示原始 ID
 * 3. 内联 source tag（<source:xxx>）转为彩色 chip
 * 4. 可折叠的 thinking 思考过程面板（仅当 thinkingText 非空时显示）
 */

import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface MarkdownMessageProps {
  text: string
  thinkingText?: string
  pending?: boolean
}

const SOURCE_RE = /<source:(画像驱动|趋势驱动|数据驱动|历史复盘|用户偏好驱动)>/g

const SOURCE_TONE: Record<string, string> = {
  画像驱动: 'text-pillar-confirm border-pillar-confirm/30 bg-pillar-confirm/10',
  趋势驱动: 'text-info border-info/30 bg-info/10',
  数据驱动: 'text-warn border-warn/30 bg-warn/10',
  历史复盘: 'text-fg-2 border-fg-2/30 bg-fg-2/10',
  用户偏好驱动: 'text-pillar-explore border-pillar-explore/30 bg-pillar-explore/10',
}
const SOURCE_FALLBACK = 'text-fg-2 border-fg-2/30 bg-fg-2/10'

/** 把 text 中的 cmt 引用、source tag 转换成 markdown 链接占位，供后续 a 组件解析渲染。 */
function preprocessText(text: string): string {
  // citation: （cmt_XXXX） → [评N](#cmt_XXXX)
  const seen = new Map<string, number>()
  let counter = 0
  let out = text.replace(/（cmt_(\d+)）/g, (_, digits) => {
    const id = `cmt_${digits}`
    if (!seen.has(id)) seen.set(id, ++counter)
    return `[评${seen.get(id)}](#${id})`
  })
  // source: <source:xxx> → [xxx](#__source__xxx)，加首尾空格避免黏连
  out = out.replace(SOURCE_RE, ' [$1](#__source__$1) ')
  return out
}

export function MarkdownMessage({ text, thinkingText, pending }: MarkdownMessageProps) {
  const [thinkingOpen, setThinkingOpen] = useState(false)
  const processed = preprocessText(text || (pending ? '…' : ''))

  return (
    <div className="space-y-2">
      {thinkingText && (
        <div className="border border-line-1 rounded-md overflow-hidden">
          <button
            type="button"
            onClick={() => setThinkingOpen((v) => !v)}
            className="w-full flex items-center justify-between px-3 py-1.5 bg-bg-inset text-[11px] text-fg-2 hover:bg-bg-2 transition"
          >
            <span className="font-mono tracking-wider">思考过程 · THINKING</span>
            {thinkingOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {thinkingOpen && (
            <div className="px-3 py-2 text-[11.5px] text-fg-2 leading-relaxed whitespace-pre-wrap font-mono bg-bg-0 max-h-[240px] overflow-y-auto">
              {thinkingText}
            </div>
          )}
        </div>
      )}
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="list-disc pl-4 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-4 space-y-0.5">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          // citation 链接渲染为上标；source tag 渲染为内联 chip
          a: ({ href, children }) => {
            if (href?.startsWith('#cmt_')) {
              return (
                <sup
                  title={href.slice(1)}
                  className="text-[10px] text-accent font-mono cursor-help ml-0.5 select-none"
                >
                  {children}
                </sup>
              )
            }
            if (href?.startsWith('#__source__')) {
              const tag = href.replace('#__source__', '')
              const cls = SOURCE_TONE[tag] ?? SOURCE_FALLBACK
              return (
                <span
                  className={[
                    'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-pill border text-[10px] font-medium align-middle no-underline',
                    cls,
                  ].join(' ')}
                >
                  <span className="w-1 h-1 rounded-pill bg-current" />
                  {children}
                </span>
              )
            }
            return <a href={href} className="underline text-accent">{children}</a>
          },
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  )
}
