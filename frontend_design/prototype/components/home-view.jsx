/* HOME view — daily digest + entry to all three modules.
 * Acts as the orchestrator's natural surface when nothing specific is in play. */

const HomeView = ({ onNav, onAsk }) => (
  <div style={{ maxWidth: 1100, display: "flex", flexDirection: "column", gap: 24 }}>
    {/* Greeting */}
    <div>
      <div className="h-mono" style={{ marginBottom: 8 }}>下午好，小A</div>
      <div style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1.2, maxWidth: 760 }}>
        我看了下你最近这条数据。<span style={{ color: "var(--fg-2)" }}>有件事你应该知道：</span>
        <span style={{ color: "var(--accent)" }}>它给你带来的新粉里，83% 是考研画像</span>。
      </div>
      <div style={{ fontSize: 14, color: "var(--fg-1)", marginTop: 12, maxWidth: 720, lineHeight: 1.65 }}>
        虽然这条整体数据不算炸，但精准度极高。这个信号挺值得跟一下 — 你之前在画像里留了个待探索项「下一阶段重心：生活向 vs 考研向」，这是第一个明确数据点。
      </div>
    </div>

    {/* Today's recommended actions */}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
      <ActionCard
        kicker="先做这个"
        tone="accent"
        icon="Chart"
        title="复盘这条视频"
        body="点完播率断点，看看到底是哪一秒掉的。我已经把假设和现实摆好了。"
        cta="去复盘"
        onClick={() => onNav?.("retro")}
      />
      <ActionCard
        kicker="顺手做"
        tone="info"
        icon="Lightbulb"
        title="把考研向选题再续一条"
        body="既然新粉是考研画像，建议小步快跑再做一条验证。我有一个 idea 等你看。"
        cta="看选题"
        onClick={() => onNav?.("ideate")}
      />
      <ActionCard
        kicker="可以聊"
        tone="explore"
        icon="User"
        title="更新你的画像"
        body="把「考研陪伴」从待探索项升级到候选确定项？我们 5 分钟可以聊完。"
        cta="去对话"
        onClick={() => onNav?.("profile")}
      />
    </div>

    {/* Quick numbers */}
    <div style={{
      background: "var(--bg-1)", border: "1px solid var(--line-1)",
      borderRadius: "var(--r-lg)", padding: 24,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <I.Chart size={16} style={{ color: "var(--fg-2)" }}/>
        <div style={{ fontSize: 15, fontWeight: 600 }}>过去 30 天</div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <button className="btn" style={{ padding: "5px 10px", fontSize: 11.5 }}>30 天</button>
          <button className="btn-ghost" style={{ padding: "5px 10px", fontSize: 11.5, color: "var(--fg-2)", border: "1px solid var(--line-1)", borderRadius: 999, background: "transparent" }}>90 天</button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24 }}>
        {[
          { l: "粉丝增长", v: "+186", spark: [4, 8, 6, 12, 18, 22, 35, 48], c: "var(--accent)" },
          { l: "总播放", v: "47.2K", spark: [3, 5, 8, 12, 9, 14, 18, 22], c: "var(--info)" },
          { l: "平均完播率", v: "37%", spark: [.32,.35,.41,.39,.36,.41,.38,.37], c: "var(--pillar-person)" },
          { l: "已发视频", v: "5", spark: [1, 1, 0, 1, 1, 0, 1, 1], c: "var(--fg-1)" },
        ].map((m, i) => (
          <div key={i}>
            <div className="h-mono" style={{ marginBottom: 6 }}>{m.l}</div>
            <div style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.01em" }}>{m.v}</div>
            <div style={{ marginTop: 6 }}><Sparkline values={m.spark} width={140} height={24} color={m.c} fill={true}/></div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

const ActionCard = ({ kicker, tone, icon, title, body, cta, onClick }) => {
  const colors = {
    accent: "var(--accent)",
    info: "var(--info)",
    explore: "var(--pillar-explore)",
  };
  const c = colors[tone];
  return (
    <button onClick={onClick} style={{
      textAlign: "left", padding: 22,
      background: "var(--bg-1)",
      border: "1px solid var(--line-1)",
      borderRadius: "var(--r-lg)",
      cursor: "pointer",
      display: "flex", flexDirection: "column", gap: 12,
      minHeight: 220,
      position: "relative", overflow: "hidden",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: `${c}18`, color: c,
          display: "grid", placeItems: "center",
        }}>{React.createElement(I[icon], { size: 16 })}</div>
        <span className="h-mono" style={{ color: c }}>{kicker}</span>
      </div>
      <div style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-0.01em", lineHeight: 1.3 }}>{title}</div>
      <div style={{ fontSize: 12.5, color: "var(--fg-1)", lineHeight: 1.6, flex: 1 }}>{body}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, color: c, fontSize: 12.5, fontWeight: 500, marginTop: 4 }}>
        {cta} <I.ChevronR size={12}/>
      </div>
    </button>
  );
};

Object.assign(window, { HomeView });
