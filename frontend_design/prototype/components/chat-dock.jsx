/* Right-dock chat: the Orchestrator surface.
 * Shows context-aware messages, structured cards inline,
 * and a "what I'm doing" header that reflects the current scene. */

const SCENE_LABELS = {
  home:    { kicker: "ORCHESTRATOR", title: "今天我能帮你做什么", color: "var(--accent)" },
  profile: { kicker: "PROFILE ENGINE", title: "正在维护你的画像", color: "var(--pillar-person)" },
  ideate:  { kicker: "STRATEGY COPILOT", title: "在帮你打磨这条选题", color: "var(--info)" },
  retro:   { kicker: "RETRO ENGINE", title: "在解读最近这期表现", color: "var(--accent)" },
  onboard: { kicker: "ONBOARDING", title: "我们来聊聊你的账号", color: "var(--accent)" },
};

const ChatDock = ({ scene = "home", messages = [], suggestions = [], onSend, onClose }) => {
  const meta = SCENE_LABELS[scene] || SCENE_LABELS.home;
  const scrollRef = useRef(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  return (
    <>
      {/* Dock header */}
      <div style={{
        padding: "16px 20px 14px",
        borderBottom: "1px solid var(--line-0)",
        display: "flex", alignItems: "flex-start", gap: 12,
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: meta.color === "var(--accent)" ? "var(--accent)" : meta.color,
          color: "var(--accent-ink)",
          display: "grid", placeItems: "center",
          fontFamily: "var(--font-mono)", fontWeight: 800, fontSize: 13,
          flexShrink: 0,
        }}>✦</div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="h-mono" style={{ color: meta.color, fontSize: 9.5, marginBottom: 3 }}>{meta.kicker}</div>
          <div style={{ fontSize: 14, fontWeight: 500, letterSpacing: "-0.005em" }}>{meta.title}</div>
        </div>
        <button onClick={onClose} className="btn-ghost" style={{
          width: 28, height: 28, border: "1px solid var(--line-1)",
          borderRadius: 8, background: "transparent", color: "var(--fg-2)",
          display: "grid", placeItems: "center",
        }} title="收起助手"><I.Close size={14}/></button>
      </div>

      {/* Conversation */}
      <div ref={scrollRef} style={{ flex: 1, overflow: "auto", padding: "20px 20px 8px" }}>
        {messages.map((m, i) => <ChatMsg key={i} {...m}/>)}
      </div>

      {/* Suggestions strip */}
      {suggestions.length > 0 && (
        <div style={{
          padding: "8px 20px 12px",
          display: "flex", flexWrap: "wrap", gap: 6,
          borderTop: "1px solid var(--line-0)",
        }}>
          <div className="h-mono" style={{ width: "100%", fontSize: 9.5, marginBottom: 4 }}>下一步可以问</div>
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => onSend?.(s)} style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid var(--line-1)",
              background: "var(--bg-1)",
              color: "var(--fg-1)",
              fontSize: 11.5,
              cursor: "pointer",
            }}>{s}</button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ padding: "12px 16px 16px", borderTop: "1px solid var(--line-0)" }}>
        <ChatInput onSend={onSend} placeholder={`问点关于"${SCENE_LABELS[scene]?.title || ""}"的事…`}/>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 10.5, color: "var(--fg-3)" }}>
          <span>AI 会引用你的画像与最近数据。<a style={{ color: "var(--fg-1)", textDecoration: "none", borderBottom: "1px dashed var(--fg-3)" }}>了解隐私</a></span>
          <span><span className="kbd" style={{ fontSize: 9 }}>⏎</span> 发送 · <span className="kbd" style={{ fontSize: 9 }}>⇧⏎</span> 换行</span>
        </div>
      </div>
    </>
  );
};

const ChatMsg = ({ role, text, card, sources, suggestions, onPick }) => {
  if (role === "system") {
    return (
      <div style={{
        textAlign: "center",
        fontFamily: "var(--font-mono)", fontSize: 10,
        color: "var(--fg-3)",
        margin: "12px 0",
        letterSpacing: "0.06em",
      }}>—— {text} ——</div>
    );
  }
  const isAI = role === "ai";
  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 18, alignItems: "flex-start" }}>
      <Avatar kind={isAI ? "ai" : "user"} size={26}/>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 11, color: "var(--fg-2)", marginBottom: 4, fontWeight: 500 }}>
          {isAI ? "Beacon" : "小A"}
        </div>
        {text && (
          <div style={{ fontSize: 13, lineHeight: 1.65, color: "var(--fg-0)", whiteSpace: "pre-wrap" }}>
            {text}
          </div>
        )}
        {card && <div style={{ marginTop: 10 }}>{card}</div>}
        {sources && sources.length > 0 && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
            {sources.map((s, i) => (
              <span key={i} style={{
                fontSize: 10.5, padding: "3px 8px",
                borderRadius: 999, background: "var(--bg-2)",
                border: "1px solid var(--line-1)", color: "var(--fg-2)",
              }}>↳ {s}</span>
            ))}
          </div>
        )}
        {suggestions && suggestions.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
            {suggestions.map((s, i) => (
              <button key={i} onClick={() => onPick?.(s)} style={{
                textAlign: "left",
                padding: "9px 12px",
                borderRadius: 10,
                border: "1px solid var(--line-1)",
                background: "var(--bg-1)",
                color: "var(--fg-0)",
                fontSize: 12.5,
                cursor: "pointer",
                display: "flex", alignItems: "center", gap: 8,
              }}>
                <span style={{ color: "var(--accent)" }}>→</span>{s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const ChatInput = ({ onSend, placeholder }) => {
  const [v, setV] = useState("");
  const submit = () => {
    if (!v.trim()) return;
    onSend?.(v.trim());
    setV("");
  };
  return (
    <div style={{
      display: "flex", alignItems: "flex-end", gap: 8,
      padding: 10,
      background: "var(--bg-inset)",
      border: "1px solid var(--line-1)",
      borderRadius: 14,
    }}>
      <textarea
        value={v}
        onChange={e => setV(e.target.value)}
        onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
        placeholder={placeholder || "聊点什么…"}
        rows={1}
        style={{
          flex: 1, resize: "none",
          background: "transparent", border: "none", outline: "none",
          color: "var(--fg-0)", fontFamily: "inherit", fontSize: 13, lineHeight: 1.5,
          padding: "4px 6px", maxHeight: 120, minHeight: 22,
        }}/>
      <button onClick={submit} style={{
        width: 30, height: 30, borderRadius: 8, border: "none",
        background: v.trim() ? "var(--accent)" : "var(--bg-3)",
        color: v.trim() ? "var(--accent-ink)" : "var(--fg-2)",
        display: "grid", placeItems: "center",
        cursor: v.trim() ? "pointer" : "default",
      }}><I.ArrowUp size={15}/></button>
    </div>
  );
};

Object.assign(window, { ChatDock, ChatMsg, ChatInput, SCENE_LABELS });
