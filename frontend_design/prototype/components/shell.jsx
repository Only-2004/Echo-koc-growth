/* App shell: left rail (modules), main content, right dock (chat).
 * The right dock is the Orchestrator — always present, context-aware.
 * This is the Notion-AI-style structured-page-with-side-chat hybrid. */

const { useState, useRef, useEffect } = React;

const NAV = [
  { id: "home",     label: "首页",        icon: "Sparkle",   note: "今日要做什么" },
  { id: "profile",  label: "我的画像",    icon: "User",     note: "KOC 画像引擎" },
  { id: "ideate",   label: "选题策略",    icon: "Lightbulb", note: "下一期想拍什么" },
  { id: "retro",    label: "复盘",        icon: "Chart",    note: "最近视频表现" },
];

const AppShell = ({ active, onNav, children, chat, density = "cozy", onDensity, onChat, chatOpen = true, layout = "split", locked = false }) => {
  return (
    <div data-density={density} style={{
      display: "grid",
      gridTemplateColumns: `220px 1fr ${chatOpen ? (layout === "split" ? "420px" : "0px") : "0px"}`,
      height: "100vh",
      background: "var(--bg-0)",
      transition: "grid-template-columns .25s ease",
    }}>
      {/* Left rail */}
      <aside style={{
        borderRight: "1px solid var(--line-1)",
        padding: "20px 14px",
        display: "flex", flexDirection: "column",
        gap: 4,
        background: "var(--bg-0)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 8px 18px" }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: "var(--accent)", color: "var(--accent-ink)",
            display: "grid", placeItems: "center",
            fontFamily: "var(--font-mono)", fontWeight: 800, fontSize: 14,
          }}>✦</div>
          <div style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.01em" }}>Beacon</div>
          <div className="h-mono" style={{ marginLeft: "auto", fontSize: 9.5 }}>BETA</div>
        </div>

        <div className="h-mono" style={{ padding: "8px 8px 4px", fontSize: 9.5 }}>工作区</div>
        {NAV.map(n => {
          const isLocked = locked && n.id !== "home";
          return (
          <button key={n.id} onClick={() => !isLocked && onNav(n.id)} disabled={isLocked} title={isLocked ? "请先创建画像" : undefined} style={{
            display: "flex", alignItems: "center", gap: 12,
            padding: "10px 10px",
            borderRadius: 10,
            background: active === n.id ? "var(--bg-2)" : "transparent",
            border: "1px solid " + (active === n.id ? "var(--line-1)" : "transparent"),
            color: isLocked ? "var(--fg-3)" : (active === n.id ? "var(--fg-0)" : "var(--fg-1)"),
            textAlign: "left", width: "100%",
            fontSize: 13, fontWeight: active === n.id ? 500 : 400,
            cursor: isLocked ? "not-allowed" : "pointer",
            opacity: isLocked ? 0.55 : 1,
            transition: "background .12s",
          }}>
            <span style={{ color: isLocked ? "var(--fg-3)" : (active === n.id ? "var(--accent)" : "var(--fg-2)"), display: "inline-flex" }}>
              {React.createElement(I[n.icon], { size: 16 })}
            </span>
            <span style={{ flex: 1 }}>{n.label}</span>
            {isLocked && <I.Lock size={12} style={{ color: "var(--fg-3)" }}/>}
          </button>
          );
        })}

        <div style={{ flex: 1 }}/>

        {/* User card */}
        <div style={{
          padding: 12, borderRadius: 12,
          background: "var(--bg-1)",
          border: "1px solid var(--line-1)",
          display: "flex", gap: 10, alignItems: "center",
        }}>
          <Avatar size={32}/>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>小A</div>
            <div style={{ fontSize: 11, color: "var(--fg-2)" }}>1,238 粉丝 · 抖音</div>
          </div>
          <button className="btn-ghost" style={{
            width: 28, height: 28, borderRadius: 8, border: "1px solid var(--line-1)",
            background: "transparent", color: "var(--fg-2)",
            display: "grid", placeItems: "center",
          }}><I.Settings size={14}/></button>
        </div>
      </aside>

      {/* Main */}
      <main style={{ overflow: "auto", position: "relative" }}>
        {/* Top bar */}
        <div style={{
          position: "sticky", top: 0, zIndex: 5,
          display: "flex", alignItems: "center", gap: 12,
          padding: "14px 32px",
          background: "rgba(250,249,246,0.85)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--line-0)",
        }}>
          <div className="h-mono" style={{ fontSize: 10 }}>
            {NAV.find(n => n.id === active)?.note || "Beacon"}
          </div>
          <div style={{ flex: 1 }}/>
          <button className="btn btn-ghost" style={{ padding: "6px 12px", fontSize: 12 }}>
            <I.Search size={14}/> 搜索内容、insight、画像
            <span style={{ marginLeft: 8, opacity: .6 }} className="kbd">⌘K</span>
          </button>
          {!chatOpen && (
            <button className="btn" style={{ padding: "6px 12px", fontSize: 12 }} onClick={() => onChat?.(true)}>
              <I.Sparkle size={14}/> 打开 AI 助手
            </button>
          )}
        </div>
        <div style={{ padding: "28px 32px 80px" }}>{children}</div>
      </main>

      {/* Right dock: chat / orchestrator */}
      {chatOpen && (
        <aside style={{
          borderLeft: "1px solid var(--line-1)",
          background: "var(--bg-0)",
          display: "flex", flexDirection: "column",
          minWidth: 0,
          overflow: "hidden",
        }}>
          {chat}
        </aside>
      )}
    </div>
  );
};

Object.assign(window, { AppShell, NAV });
