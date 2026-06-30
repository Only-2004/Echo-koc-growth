/* MODULE A — Onboarding conversation.
 * Shows the AI's open-ended + option-converging interaction pattern,
 * with a live "画像 building" rail on the right of the chat that ticks up. */

const ONBOARD_TURNS = [
  { role: "system", text: "ONBOARDING · 第 1 步 / 共 4 步" },
  { role: "ai", text: "嗨小A 👋 不用紧张，这不是问卷。\n我先看了下你最近 12 条视频，想和你聊几个小问题，帮你把账号定位想清楚一点。先从你自己开始 —— 你觉得现在你这个账号，最像哪种感觉？", suggestions: [
    "校园 vlog 博主",
    "考研陪伴号",
    "学生探店推荐",
    "我也说不太清，想一起想想",
  ]},
  { role: "user", text: "我也说不太清，想一起想想。最近其实有点纠结，到底要不要走考研那条线。" },
  { role: "ai", text: "完全可以一起想。我注意到一件事：你这 12 条视频里，有 3 条提到了考研（自习室、图书馆、错题本那几条），平均完播率是 41%；其他校园 vlog 平均是 33%。\n虽然样本不大，但考研内容其实对你账号是个被低估的方向。\n那我换个问法 —— 你做这个号，最希望它给你带来什么？", sources: ["最近 12 条视频", "完播率对比"], suggestions: [
    "稳定接到一些校园相关的商单",
    "记录自己考研这段经历",
    "纯粹好玩 / 表达欲",
    "都有，但商单是主目标",
  ]},
  { role: "user", text: "都有，但商单是主目标。" },
  { role: "ai", text: "了解。我把这条记到\"待探索项\"里 —— 因为商单方向其实和定位强绑定。\n再聊一个：你之前提到自己在玩原神，是顺嘴一说还是会想把游戏内容也做进来？这个决定挺重要的，会影响你的人设标签。", suggestions: [
    "想做，但不知道怎么和校园结合",
    "不想做，纯爱好",
    "先放一放，看看大家反馈",
  ]},
];

const PROFILE_TICKS = [
  { state: "confirm", label: "平台 = 抖音", ts: "00:08" },
  { state: "confirm", label: "粉丝量级 = 1.2K", ts: "00:08" },
  { state: "person",  label: "人格：外向 · 爱表达", ts: "00:42" },
  { state: "explore", label: "方向：生活向 vs 考研向", ts: "01:15" },
  { state: "person",  label: "背景：26 考研中（计算机）", ts: "01:30" },
  { state: "explore", label: "目标：以商单为主目标", ts: "02:04" },
  { state: "person",  label: "潜在标签：原神资深玩家", ts: "02:18" },
];

const OnboardView = ({ onAsk, onFinish }) => {
  return (
    <div style={{ maxWidth: 1280 }}>
      {/* Top */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <div className="h-mono" style={{ marginBottom: 6 }}>SETUP · ONBOARDING</div>
          <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em" }}>先聊一会儿，我帮你想清楚这个号</div>
          <div style={{ color: "var(--fg-2)", fontSize: 14, marginTop: 6, maxWidth: 640 }}>
            我会问 8-10 个问题，混合开放回答与几个选项。你的每一句回答会实时凝练成你的画像 —— 你随时能看见我在想什么。
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 12, color: "var(--fg-2)" }}>第 1 步 / 共 4 步</span>
          <div style={{ display: "flex", gap: 4 }}>
            {[0,1,2,3].map(i => (
              <div key={i} style={{
                width: 32, height: 4, borderRadius: 2,
                background: i === 0 ? "var(--accent)" : "var(--bg-3)",
              }}/>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 16, alignItems: "start" }}>
        {/* Conversation surface */}
        <div style={{
          background: "var(--bg-1)", border: "1px solid var(--line-1)",
          borderRadius: "var(--r-xl)",
          minHeight: 520,
          padding: "24px 28px 20px",
        }}>
          {ONBOARD_TURNS.map((m, i) => <ChatMsg key={i} {...m} onPick={(s) => onAsk?.(s)}/>)}

          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "12px 14px",
            background: "var(--bg-inset)",
            border: "1px solid var(--line-1)",
            borderRadius: 12,
            color: "var(--fg-3)", fontSize: 13,
            marginTop: 8,
          }}>
            <I.Mic size={14}/>
            <span style={{ flex: 1 }}>说说你的想法… 也可以选上面的选项</span>
            <span className="kbd" style={{ fontSize: 9 }}>⏎</span>
          </div>

          {onFinish && (
            <div style={{
              marginTop: 16, padding: 14,
              background: "var(--accent-soft)",
              border: "1px solid var(--accent-line)",
              borderRadius: 12,
              display: "flex", alignItems: "center", gap: 12,
            }}>
              <I.Sparkle size={16} style={{ color: "var(--accent)", flexShrink: 0 }}/>
              <div style={{ flex: 1, fontSize: 12.5, color: "var(--fg-1)", lineHeight: 1.55 }}>
                <strong style={{ color: "var(--fg-0)" }}>已经够了。</strong>
                我已经收集到 7 个信号，可以先生成第一版画像。剩下的我们可以在使用中慢慢补。
              </div>
              <button onClick={onFinish} className="btn-primary btn" style={{
                padding: "8px 14px", fontSize: 13, fontWeight: 600,
                display: "flex", alignItems: "center", gap: 6, flexShrink: 0,
              }}>
                生成画像 <I.ArrowR size={12}/>
              </button>
            </div>
          )}
        </div>

        {/* Live profile build rail */}
        <div style={{ position: "sticky", top: 80 }}>
          <div style={{
            background: "var(--bg-1)", border: "1px solid var(--line-1)",
            borderRadius: "var(--r-lg)", padding: 20,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <I.Brain size={14} style={{ color: "var(--accent)" }}/>
              <div className="h-mono" style={{ color: "var(--accent)" }}>LIVE · 我正在构建</div>
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>你的画像</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {PROFILE_TICKS.map((t, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: `var(--pillar-${t.state})`,
                    marginTop: 7, flexShrink: 0,
                  }}/>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, color: "var(--fg-0)" }}>{t.label}</div>
                    <div style={{ fontSize: 10.5, color: "var(--fg-3)", fontFamily: "var(--font-mono)", marginTop: 2 }}>
                      {t.state === "confirm" && "确定项"}
                      {t.state === "person" && "个性化项"}
                      {t.state === "explore" && "待探索项"}
                      <span> · {t.ts}</span>
                    </div>
                  </div>
                </div>
              ))}
              <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--fg-3)", fontSize: 11.5, marginTop: 4 }}>
                <div className="dot-pulse"/>
                <span>正在分析你最新一句回答…</span>
              </div>
            </div>
          </div>

          <div style={{
            marginTop: 12, padding: "12px 16px",
            background: "var(--bg-1)", border: "1px solid var(--line-1)",
            borderRadius: 12, fontSize: 11.5, color: "var(--fg-2)", lineHeight: 1.6,
          }}>
            ✨ 你随时可以说"先这样，待会再聊"。已经收集到的信息会留下来。
          </div>
        </div>
      </div>

      <style>{`
        .dot-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 1.4s infinite; }
        @keyframes pulse {
          0%,100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.3; transform: scale(.8); }
        }
      `}</style>
    </div>
  );
};

Object.assign(window, { OnboardView, ONBOARD_TURNS });
