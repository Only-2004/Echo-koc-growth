/**
 * CommentClusters - 评论聚类卡：4 主题 + 样本评论。
 * 点击触发 useOnAsk(`展开看「<theme>」这一类的所有评论`)
 */

import { SectionTitle } from '../_shared/SectionTitle'
import { useOnAsk } from '../_shared/useOnAsk'

type Sentiment = 'pos' | 'neg' | 'warn'

interface Cluster {
  theme: string
  n: number
  sentiment: Sentiment
  quote: string
}

const SENT_TEXT: Record<Sentiment, string> = {
  pos: 'text-pos',
  neg: 'text-neg',
  warn: 'text-warn',
}
const SENT_BG: Record<Sentiment, string> = {
  pos: 'bg-pos-soft',
  neg: 'bg-neg-soft',
  warn: 'bg-warn-soft',
}

export function CommentClusters({ clusters }: { clusters: Cluster[] }) {
  const onAsk = useOnAsk()
  return (
    <div className="bg-bg-1 border border-line-1 rounded-lg p-6">
      <SectionTitle
        kicker="评论聚类"
        title="观众真实关切"
        sub={`从 ${clusters.reduce((s, c) => s + c.n, 0)} 条评论里聚出 ${clusters.length} 个主题。点进去能看到原评论与情感分布。`}
      />
      <div className="grid grid-cols-4 gap-3">
        {clusters.map((c) => (
          <button
            key={c.theme}
            type="button"
            onClick={() => onAsk(`展开看「${c.theme}」这一类的所有评论`)}
            className="text-left p-3.5 bg-bg-2 border border-line-0 rounded-md cursor-pointer flex flex-col gap-2 hover:bg-bg-3/40 transition"
          >
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium">{c.theme}</span>
              <span
                className={[
                  'font-mono text-[10px] px-1.5 py-0.5 rounded-sm',
                  SENT_TEXT[c.sentiment],
                  SENT_BG[c.sentiment],
                ].join(' ')}
              >
                {c.n} 条
              </span>
            </div>
            <div className="text-[11.5px] text-fg-2 leading-relaxed italic">{c.quote}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
