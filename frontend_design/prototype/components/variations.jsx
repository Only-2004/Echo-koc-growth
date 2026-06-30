/* Variation B — "Conversation-first" layout (Perplexity / ChatGPT style).
 * Same data and modules as the main app, but the chat is the entire surface,
 * with structured cards (画像 / 策略 / 复盘) appearing INSIDE the conversation. */

const VarBChat = () => {
  return (
    <div style={{
      width: "100%", height: "100%",
      background: "var(--bg-0)",
      display: "flex", flexDirection: "column",
    }}>
      {/* Top bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 12,
        padding: "14px 24px",
        borderBottom: "1px solid var(--line-0)",
      }}>
        <div style={{
          width: 26, height: 26, borderRadius: 7,
          background: "var(--accent)", color: "var(--accent-ink)",
          display: "grid", placeItems: "center",
          fontFamily: "var(--font-mono)", fontWeight: 800, fontSize: 13,
        }}>✦</div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>Beacon</div>
        <span className="chip" style={{ fontSize: 10.5 }}>Conversation-first</span>
        <div style={{ flex: 1 }}/>
        <div style={{ display: "flex", gap: 6 }}>
          {["画像", "选题", "复盘", "新对话"].map(x => (
            <button key={x} className="btn" style={{ padding: "5px 12px", fontSize: 11.5 }}>{x}</button>
          ))}
        </div>
      </div>

      {/* Conversation surface */}
      <div style={{ flex: 1, overflow: "auto", padding: "32px 0" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", padding: "0 24px" }}>
          <ChatMsg role="user" text="帮我看下「图书馆永远占座的人」这条 idea 怎么样"/>
          <ChatMsg
            role="ai"
            text="我评了四个维度，整体推荐做。重点是这条会直接验证你画像里那个「生活向 vs 考研向」的待探索项。"
            sources={["你的画像", "近 7 天平台趋势"]}
            card={
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                {[
                  { l: "热度", v: 72, c: "var(--info)" },
                  { l: "贴合", v: 85, c: "var(--pillar-person)" },
                  { l: "差异", v: 81, c: "var(--pillar-explore)" },
                  { l: "执行", v: "✓", c: "var(--accent)" },
                ].map((m, i) => (
                  <div key={i} style={{
                    padding: 14, background: "var(--bg-2)",
                    border: "1px solid var(--line-0)", borderRadius: 10,
                  }}>
                    <div className="h-mono" style={{ marginBottom: 8 }}>{m.l}</div>
                    <div style={{ fontSize: 22, fontWeight: 600, color: m.c }}>{m.v}</div>
                  </div>
                ))}
              </div>
            }
          />
          <ChatMsg
            role="ai"
            text="我把发布前的策略放在你的待发布池里了，这是关键决定："
            card={
              <div style={{
                padding: 16, background: "var(--bg-1)",
                border: "1px solid var(--accent-line)", borderRadius: 12,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <span className="h-mono" style={{ color: "var(--accent)" }}>开场钩子 · 0-3s</span>
                </div>
                <div style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: 1.5 }}>
                  "这个人，七天没换过位置。"
                </div>
              </div>
            }
            suggestions={[
              "如果做成 vlog 而不是纪录片呢",
              "再给我 3 个相邻方向",
              "导出拍摄简报",
            ]}
          />
        </div>
      </div>

      {/* Composer */}
      <div style={{ padding: "16px 24px 24px", borderTop: "1px solid var(--line-0)" }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          <div style={{
            display: "flex", alignItems: "flex-end", gap: 10,
            padding: 14,
            background: "var(--bg-1)",
            border: "1px solid var(--line-1)",
            borderRadius: 16,
          }}>
            <div style={{ flex: 1, minHeight: 40, color: "var(--fg-3)", fontSize: 13.5 }}>问点关于这条 idea 的事…</div>
            <button className="btn-ghost" style={{ width: 32, height: 32, borderRadius: 8, border: "1px solid var(--line-1)", background: "transparent", color: "var(--fg-2)", display: "grid", placeItems: "center" }}><I.Image size={14}/></button>
            <button style={{
              width: 32, height: 32, borderRadius: 8, border: "none",
              background: "var(--accent)", color: "var(--accent-ink)",
              display: "grid", placeItems: "center", cursor: "pointer",
            }}><I.ArrowUp size={14}/></button>
          </div>
          <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
            <span className="h-mono" style={{ marginRight: 4, fontSize: 9.5 }}>试试</span>
            {["更新我的画像", "下一期拍什么", "上条视频复盘", "我适合接什么商单"].map(s => (
              <button key={s} className="btn" style={{ padding: "5px 12px", fontSize: 11.5 }}>{s}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

/* Variation C — "Dashboard-first" layout (no persistent chat).
 * Chat is invoked as a slide-up sheet from any clickable element.
 * Density-heavy, for power users. */

const VarCDashboard = () => (
  <div style={{
    width: "100%", height: "100%",
    background: "var(--bg-0)",
    display: "grid", gridTemplateColumns: "180px 1fr",
  }}>
    {/* Compact rail */}
    <aside style={{
      borderRight: "1px solid var(--line-1)",
      padding: "16px 12px",
      display: "flex", flexDirection: "column", gap: 4,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 6px 14px" }}>
        <div style={{
          width: 22, height: 22, borderRadius: 6,
          background: "var(--accent)", color: "var(--accent-ink)",
          display: "grid", placeItems: "center",
          fontFamily: "var(--font-mono)", fontWeight: 800, fontSize: 11,
        }}>✦</div>
        <div style={{ fontSize: 12.5, fontWeight: 600 }}>Beacon</div>
        <span className="h-mono" style={{ marginLeft: "auto", fontSize: 9 }}>PRO</span>
      </div>
      {[
        ["首页", "Sparkle", true],
        ["画像", "User", false],
        ["选题", "Lightbulb", false],
        ["复盘", "Chart", false],
        ["对话", "Brain", false],
      ].map(([l, ic, a]) => (
        <button key={l} style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "8px 8px",
          borderRadius: 8,
          background: a ? "var(--bg-2)" : "transparent",
          border: "1px solid " + (a ? "var(--line-1)" : "transparent"),
          color: a ? "var(--fg-0)" : "var(--fg-1)",
          textAlign: "left", width: "100%",
          fontSize: 12, cursor: "pointer",
        }}>
          <span style={{ color: a ? "var(--accent)" : "var(--fg-2)", display: "inline-flex" }}>
            {React.createElement(I[ic], { size: 14 })}
          </span>
          <span>{l}</span>
        </button>
      ))}
    </aside>

    {/* Main grid */}
    <main style={{ overflow: "auto", padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
        <div>
          <div className="h-mono" style={{ marginBottom: 4 }}>OPS DASHBOARD</div>
          <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.01em" }}>小A 的运营台</div>
        </div>
        <button className="btn" style={{ padding: "6px 12px", fontSize: 12 }}>
          <I.Sparkle size={14}/> 唤起 AI（⌘K）
        </button>
      </div>

      {/* Tight KPI strip */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10, marginBottom: 16 }}>
        {[
          { l: "粉丝", v: "1,238", d: "+186" },
          { l: "30d 完播", v: "37%", d: "-2pp" },
          { l: "30d 互动率", v: "8.4%", d: "+1.1pp" },
          { l: "投稿", v: "5", d: "" },
          { l: "热门 idea", v: "3", d: "待选" },
          { l: "复盘待办", v: "2", d: "" },
        ].map((m, i) => (
          <div key={i} style={{
            padding: 12, background: "var(--bg-1)",
            border: "1px solid var(--line-1)", borderRadius: 8,
          }}>
            <div style={{ fontSize: 10.5, color: "var(--fg-2)", fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>{m.l}</div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>{m.v}</div>
            <div style={{ fontSize: 10.5, color: "var(--fg-3)", marginTop: 2 }}>{m.d}</div>
          </div>
        ))}
      </div>

      {/* Two columns: profile + retro */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
        <div style={{ background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 10, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>画像快照</div>
            <span className="h-mono" style={{ fontSize: 9 }}>UPD 2D</span>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
            <span className="chip" data-tone="confirm" style={{ fontSize: 10.5 }}><span className="dot"/>校园 vlog</span>
            <span className="chip" data-tone="confirm" style={{ fontSize: 10.5 }}><span className="dot"/>抖音 1.2K</span>
            <span className="chip" data-tone="person" style={{ fontSize: 10.5 }}><span className="dot"/>26 考研</span>
            <span className="chip" data-tone="person" style={{ fontSize: 10.5 }}><span className="dot"/>原神</span>
            <span className="chip" data-tone="explore" style={{ fontSize: 10.5 }}><span className="dot"/>2 个待决</span>
          </div>
          <div style={{ fontSize: 11, color: "var(--fg-2)", lineHeight: 1.6 }}>
            生活向 vs 考研向 — 上条视频带来 83% 考研画像新粉，建议升级为候选确定项。
          </div>
        </div>
        <div style={{ background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 10, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>最近 5 条</div>
            <span className="h-mono" style={{ fontSize: 9 }}>FINISH RATE</span>
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 60 }}>
            {[0.46, 0.39, 0.41, 0.36, 0.28].map((v, i) => (
              <div key={i} style={{ flex: 1 }}>
                <div style={{
                  height: `${v * 100}%`,
                  background: i === 4 ? "var(--neg)" : i === 0 ? "var(--accent)" : "var(--bg-3)",
                  borderRadius: "3px 3px 0 0",
                }}/>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 10, color: "var(--fg-3)", fontFamily: "var(--font-mono)" }}>
            <span>3w 前</span><span>今天</span>
          </div>
        </div>
      </div>

      {/* Insight feed */}
      <div style={{ background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 10, padding: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Insight 信号流</div>
        {[
          { t: "完播率断崖在第 12s", b: "对应你新尝试的口播开场。下次 ≤ 5s。", src: "data" },
          { t: "考研画像新粉占比 83%", b: "强信号 · 建议把待探索项升级。", src: "profile" },
          { t: "图书馆类话题处于推流期", b: "供给/需求比 0.81，6-10 天窗口。", src: "trend" },
        ].map((x, i) => (
          <div key={i} style={{
            display: "flex", gap: 10, padding: "10px 0",
            borderTop: i > 0 ? "1px solid var(--line-0)" : "none",
            alignItems: "center",
          }}>
            <SourceTag source={x.src}/>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12.5, fontWeight: 500 }}>{x.t}</div>
              <div style={{ fontSize: 11, color: "var(--fg-2)", marginTop: 2 }}>{x.b}</div>
            </div>
            <button className="btn-ghost" style={{ padding: "4px 8px", fontSize: 11, color: "var(--fg-2)", border: "1px solid var(--line-1)", borderRadius: 999, background: "transparent" }}>
              追问 <I.ChevronR size={11}/>
            </button>
          </div>
        ))}
      </div>
    </main>
  </div>
);

Object.assign(window, { VarBChat, VarCDashboard });
