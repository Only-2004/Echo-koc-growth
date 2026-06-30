/* MODULE C — Retro & Insight Engine.
 * 3-layer dashboard: KPI cards → insight (with attribution to策略 hypothesis) → actionable suggestion.
 * Every layer is clickable as a chat-deepening entry point. */

const VIDEOS = [
  { id: "v1", title: "图书馆永远占座的那个人", date: "今天", views: 4820, finish: 0.28, follow: 12, share: 31, comments: 87, baseline: { finish: 0.41 }, hot: true },
  { id: "v2", title: "考研三个月，我的桌子变成这样", date: "3 天前", views: 12400, finish: 0.46, follow: 84, share: 220, comments: 312, baseline: { finish: 0.41 }, hot: false },
  { id: "v3", title: "杭州学院路 5 家咖啡评测", date: "6 天前", views: 7200, finish: 0.39, follow: 38, share: 95, comments: 142, baseline: { finish: 0.33 }, hot: false },
];

const RetroView = ({ onAsk }) => {
  const [vid, setVid] = useState("v1");
  const v = VIDEOS.find(x => x.id === vid);
  return (
    <div style={{ maxWidth: 1280, display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Top header w/ video selector */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div className="h-mono" style={{ marginBottom: 6 }}>RETRO · 复盘</div>
          <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em" }}>最近这条没炸，我来告诉你为什么。</div>
          <div style={{ color: "var(--fg-2)", fontSize: 13, marginTop: 6, maxWidth: 720 }}>
            我把发布前的策略和发布后的真实数据放在一起对比。点任何一个数字、insight 或建议，可以继续追问我。
          </div>
        </div>
      </div>

      {/* Video selector strip */}
      <div style={{ display: "flex", gap: 10, overflow: "auto", paddingBottom: 4 }}>
        {VIDEOS.map(x => (
          <button key={x.id} onClick={() => setVid(x.id)} style={{
            display: "flex", gap: 12, alignItems: "center",
            padding: 10,
            background: vid === x.id ? "var(--bg-2)" : "var(--bg-1)",
            border: "1px solid " + (vid === x.id ? "var(--accent-line)" : "var(--line-1)"),
            borderRadius: 12,
            minWidth: 280, flex: 1,
            textAlign: "left", cursor: "pointer",
            position: "relative",
          }}>
            <div className="placeholder" style={{ width: 56, height: 72, flexShrink: 0, fontSize: 8 }}>16:9</div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontSize: 12.5, fontWeight: 500, color: "var(--fg-0)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{x.title}</div>
              <div style={{ fontSize: 11, color: "var(--fg-3)", marginTop: 4 }}>{x.date} · {x.views.toLocaleString()} 播放</div>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
                {x.finish < x.baseline.finish ? (
                  <span className="chip" style={{ fontSize: 10, padding: "2px 7px", color: "var(--neg)", borderColor: "rgba(196,74,58,0.3)", background: "rgba(196,74,58,0.06)" }}>
                    <span className="dot" style={{ background: "var(--neg)" }}/>低于基线
                  </span>
                ) : (
                  <span className="chip" style={{ fontSize: 10, padding: "2px 7px", color: "var(--pos)", borderColor: "rgba(61,138,58,0.3)", background: "rgba(61,138,58,0.06)" }}>
                    <span className="dot" style={{ background: "var(--pos)" }}/>超出基线
                  </span>
                )}
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <KPI label="完播率" value={`${Math.round(v.finish * 100)}%`} delta={v.finish - v.baseline.finish} format="pp" onAsk={onAsk}
          spark={[0.35, 0.38, 0.42, 0.41, 0.39, 0.31, 0.28]} negativeIsBad/>
        <KPI label="新增关注" value={v.follow} delta={-22} format="rel" onAsk={onAsk}
          spark={[40, 60, 84, 38, 12]} negativeIsBad/>
        <KPI label="转发" value={v.share} delta={-86} format="rel" onAsk={onAsk}
          spark={[120, 220, 220, 95, 31]} negativeIsBad/>
        <KPI label="评论情感" value="混合" delta="42% 困惑" format="raw" onAsk={onAsk} tone="warn"/>
      </div>

      {/* Strategy vs reality */}
      <div style={{
        background: "var(--bg-1)", border: "1px solid var(--line-1)",
        borderRadius: "var(--r-lg)", padding: 24,
      }}>
        <div className="h-mono" style={{ marginBottom: 14, color: "var(--fg-2)" }}>归因 · 策略 vs 实际</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 32px 1fr", gap: 16, alignItems: "stretch" }}>
          <div style={{
            padding: 16, background: "var(--bg-2)", borderRadius: 10,
            border: "1px dashed var(--line-2)",
          }}>
            <div className="h-mono" style={{ marginBottom: 8 }}>发布前的策略假设</div>
            <ul style={{ margin: 0, padding: "0 0 0 16px", fontSize: 12.5, lineHeight: 1.7, color: "var(--fg-1)" }}>
              <li>开场钩子：黑屏 + 一句话悬念</li>
              <li>主线：跟拍 + 三段反差笑点</li>
              <li>预估完播率：≥ 41%</li>
              <li>验证假设：考研向是否能持续吸粉</li>
            </ul>
          </div>
          <div style={{ display: "grid", placeItems: "center" }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%",
              background: "var(--bg-2)", color: "var(--fg-2)",
              display: "grid", placeItems: "center",
              border: "1px solid var(--line-1)",
            }}><I.Arrow size={14}/></div>
          </div>
          <div style={{
            padding: 16, background: "var(--bg-2)", borderRadius: 10,
            border: "1px solid var(--line-1)",
          }}>
            <div className="h-mono" style={{ marginBottom: 8, color: "var(--fg-1)" }}>发生了什么</div>
            <ul style={{ margin: 0, padding: "0 0 0 16px", fontSize: 12.5, lineHeight: 1.7, color: "var(--fg-1)" }}>
              <li><span style={{ color: "var(--neg)" }}>钩子没拉住人</span> · 第 12s 流失 38%</li>
              <li>笑点节奏 OK，但跨越点不明显</li>
              <li>实际完播率：28% · 比基线低 13pp</li>
              <li>评论里 42% 表达"没看懂在拍啥"</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Insights → suggestions */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <InsightCard
          n="01"
          tone="neg"
          title="完播率低于基线 13pp，主要发生在第 12 秒"
          body="第 12 秒对应你这次新尝试的口播开场（介绍人物背景）。在那之前留存 81%，那之后降到 51%。说明黑屏钩子有效，但紧跟的口播太长太冷。"
          metric={{ label: "12s 流失", value: "-38%" }}
          source="data"
          suggestions={[
            "下次类似选题，开场口播控制在 ≤ 5 秒，或换成 b-roll 引入。",
            "把人物背景信息分散到中段，不要堆在开头。",
          ]}
          onAsk={onAsk}
        />
        <InsightCard
          n="02"
          tone="warn"
          title={`42% 评论表达"没看懂"，主要是没看完悬念的人`}
          body={`完播率 < 50% 的观众里，68% 留下了"啥意思""看不懂"类评论。完播观众普遍正面。问题不在内容本身，在于钩子吊得太久没揭。`}
          metric={{ label: "困惑评论占比", value: "42%" }}
          source="data"
          suggestions={[
            "在 15s 处先给一个\"小揭示\"，让没耐心的人也有获得感。",
            "标题可以做得更直白一点 —— 现在依赖完整观看才能 get。",
          ]}
          onAsk={onAsk}
        />
        <InsightCard
          n="03"
          tone="pos"
          title={`新粉的画像反而更接近"考研人"，不是泛校园`}
          body={`这条转化的 12 个新粉中，10 个主页有考研相关 tag。虽然总量小，但精准度极高。这其实是「待探索项」的一个明确信号 —— 考研向更能给你带来精准粉。`}
          metric={{ label: "考研画像新粉占比", value: "83%" }}
          source="profile"
          suggestions={[
            "更新画像：把「考研陪伴」从待探索项升级到候选确定项。",
            "下一条建议继续考研向选题，做小步快跑验证。",
          ]}
          onAsk={onAsk}
        />
        <InsightCard
          n="04"
          tone="info"
          title="Tag 投放过散，没拿到精准推流"
          body="这条用了 5 个 Tag，其中 #校园vlog #杭州 这两个流量大但和内容关联度弱，分走了系统的相关性判断。"
          metric={{ label: "推流相关性", value: "0.42" }}
          source="trend"
          suggestions={[
            "下次只用 3 个高相关 Tag：#考研日常 #图书馆 #26考研",
            "把弱相关 Tag 移到文案末尾而非视频 Tag。",
          ]}
          onAsk={onAsk}
        />
      </div>

      {/* Comment cluster */}
      <div style={{
        background: "var(--bg-1)", border: "1px solid var(--line-1)",
        borderRadius: "var(--r-lg)", padding: 24,
      }}>
        <SectionTitle
          kicker="评论聚类"
          title="观众真实关切"
          sub="从 87 条评论里聚出 4 个主题。点进去能看到原评论与情感分布。"
        />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {[
            { theme: "没看懂在拍啥", n: 36, sentiment: "neg", quote: "\"所以这个人是谁来着\"" },
            { theme: "我们学校也有这种人", n: 22, sentiment: "pos", quote: "\"我天，我们图书馆也有一个\"" },
            { theme: "想看更多考研内容", n: 18, sentiment: "pos", quote: "\"博主继续拍考研日常吧\"" },
            { theme: "原神彩蛋好评", n: 11, sentiment: "pos", quote: "\"结尾那个深渊太懂了哈哈\"" },
          ].map((c, i) => (
            <button key={i} onClick={() => onAsk?.(`展开看「${c.theme}」这一类的所有评论`)} style={{
              textAlign: "left",
              padding: 14, background: "var(--bg-2)",
              border: "1px solid var(--line-0)", borderRadius: 10,
              cursor: "pointer", display: "flex", flexDirection: "column", gap: 8,
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{c.theme}</span>
                <span style={{
                  fontFamily: "var(--font-mono)", fontSize: 10,
                  color: c.sentiment === "neg" ? "var(--neg)" : "var(--pos)",
                  padding: "2px 6px", borderRadius: 4,
                  background: c.sentiment === "neg" ? "var(--neg-soft)" : "var(--pos-soft)",
                }}>{c.n} 条</span>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--fg-2)", lineHeight: 1.5, fontStyle: "italic" }}>{c.quote}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

const KPI = ({ label, value, delta, format, spark, tone, negativeIsBad, onAsk }) => {
  const num = typeof delta === "number" ? delta : null;
  const isBad = num !== null && (negativeIsBad ? num < 0 : num > 0);
  const isGood = num !== null && (negativeIsBad ? num > 0 : num < 0);
  const color = tone === "warn" ? "var(--warn)" : isBad ? "var(--neg)" : isGood ? "var(--pos)" : "var(--fg-2)";
  const display = num !== null
    ? (format === "pp" ? `${num > 0 ? "+" : ""}${(num * 100).toFixed(1)} pp` : `${num > 0 ? "+" : ""}${num}%`)
    : delta;
  return (
    <button onClick={() => onAsk?.(`展开「${label}」这个数据`)} style={{
      textAlign: "left", padding: 18,
      background: "var(--bg-1)", border: "1px solid var(--line-1)",
      borderRadius: "var(--r-lg)", cursor: "pointer",
      display: "flex", flexDirection: "column", gap: 10, position: "relative",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div className="h-mono">{label}</div>
        {spark && <Sparkline values={spark} width={60} height={20} color={isBad ? "var(--neg)" : "var(--info)"}/>}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontSize: 30, fontWeight: 600, letterSpacing: "-0.02em" }}>{value}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, color }}>
        {num !== null && (isBad ? <I.ArrowDown size={12}/> : isGood ? <I.ArrowUp size={12}/> : null)}
        <span style={{ fontSize: 12, fontFamily: "var(--font-mono)" }}>{display}</span>
        <span style={{ fontSize: 11, color: "var(--fg-3)" }}>vs 你的基线</span>
      </div>
    </button>
  );
};

const InsightCard = ({ n, tone, title, body, metric, source, suggestions, onAsk }) => {
  const c = { neg: "var(--neg)", warn: "var(--warn)", pos: "var(--pos)", info: "var(--info)" }[tone];
  return (
    <div style={{
      background: "var(--bg-1)", border: "1px solid var(--line-1)",
      borderRadius: "var(--r-lg)", padding: 22,
      display: "flex", flexDirection: "column", gap: 14,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 10,
          padding: "2px 8px", borderRadius: 999,
          color: c, border: `1px solid ${c}40`, background: `${c}10`,
        }}>INSIGHT {n}</span>
        <SourceTag source={source}/>
        {metric && (
          <div style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 11, color: c }}>
            {metric.label} <span style={{ fontWeight: 600 }}>{metric.value}</span>
          </div>
        )}
      </div>
      <div style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.4, letterSpacing: "-0.005em" }}>{title}</div>
      <div style={{ fontSize: 13, color: "var(--fg-1)", lineHeight: 1.7 }}>{body}</div>
      <div style={{
        background: "var(--bg-2)", borderRadius: 10,
        border: "1px solid var(--line-0)", padding: 14,
      }}>
        <div className="h-mono" style={{ marginBottom: 10, color: "var(--accent)" }}>下一步可以这么做</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => onAsk?.(s)} style={{
              textAlign: "left",
              padding: "10px 12px",
              background: "var(--bg-1)", border: "1px solid var(--line-1)",
              borderRadius: 8, color: "var(--fg-0)", fontSize: 12.5,
              lineHeight: 1.55, cursor: "pointer",
              display: "flex", gap: 10, alignItems: "flex-start",
            }}>
              <span style={{ color: "var(--accent)", marginTop: 1 }}>→</span>
              <span style={{ flex: 1 }}>{s}</span>
              <I.ChevronR size={12} style={{ color: "var(--fg-3)", marginTop: 2 }}/>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { RetroView });
