/* Main app — wires modules to the orchestrator (right dock).
 * Each scene has its own scripted chat thread that demonstrates the relevant agent behavior. */

const SCENE_CHATS = {
  home: {
    messages: [
      { role: "ai", text: "我刚跑完最近 5 条视频的复盘。\n有 1 条数据偏弱但带来了高纯度的考研画像新粉 —— 这个信号比单纯的播放量更值得关注。" },
      { role: "ai", text: "你想从哪开始？", suggestions: [
        "先看那条视频的复盘",
        "顺势再做一条考研向 idea",
        "更新画像里那个待探索项",
      ]},
    ],
    suggestions: ["最近哪条视频涨粉最多", "我适合接什么类型的商单", "帮我想 3 个下周拍的选题"],
  },
  profile: {
    messages: [
      { role: "ai", text: "这是你目前的画像。我把它分成三态：\n· 确定项 — 已经稳下来的事实\n· 个性化项 — 你独特的资产\n· 待探索项 — 还没想清楚、需要在内容里去试的方向" },
      { role: "ai", text: "右边那两条紫色虚线框，是接下来最值得先验证的。", sources: ["12 条视频元数据", "Onboarding 对话"]},
    ],
    suggestions: ["把考研陪伴升级为确定项", "原神这个标签要保留吗", "我的画像里少了什么"],
  },
  ideate: {
    messages: [
      { role: "ai", text: "你提的这条 idea，我评了四个维度。整体推荐做。" },
      { role: "ai", text: "重点：这条会直接验证你画像里那个待探索项 — 「生活向 vs 考研向」。看完反响你就能下决定。", sources: ["你的画像", "近 7 天平台趋势"]},
      { role: "ai", text: "我用绿色 / 蓝色标了每条建议来自哪 — 画像还是趋势 — 你不用猜我在想什么。" },
    ],
    suggestions: ["开头钩子还能怎么改", "如果做成 vlog 而不是纪录片呢", "推荐 3 个相邻选题"],
  },
  retro: {
    messages: [
      { role: "ai", text: "这条数据没炸，但不是没价值。我归因了一下：" },
      { role: "ai", text: "钩子有效（前 12 秒留存 81%），但接下来的口播太冷拉不住人。这是节奏问题，不是选题问题。", sources: ["完播曲线", "评论聚类"]},
      { role: "ai", text: "另外有个发现 —— 它给你带来的新粉 83% 都是考研画像。我建议把这个写回画像引擎。点 Insight 03 可以详聊。", suggestions: [
        "把考研向写回画像",
        "下一条也做考研向",
        "为什么钩子拉得住人但口播拉不住",
      ]},
    ],
    suggestions: ["其他视频也帮我归因一下", "评论里最尖锐的几条", "给我导出一份复盘报告"],
  },
  onboard: {
    messages: [
      { role: "system", text: "ONBOARDING 模式 · 4 步 · 当前第 1 步" },
      { role: "ai", text: "嗨小A 👋\n这不是问卷。我会一边问你一边把答案凝练到右边那个画像里 —— 你能实时看到我在记什么。\n\n随时可以暂停。" },
    ],
    suggestions: ["跳过对话，从我视频里推断", "我有 5 分钟可以聊", "我想直接看示例画像"],
  },
};

const App = () => {
  const [tweaks, setTweak] = useTweaks(/*EDITMODE-BEGIN*/{
    "accent": "lime",
    "density": "cozy",
    "layout": "split",
    "newUser": true
  }/*EDITMODE-END*/);

  const profileReady = !tweaks.newUser;

  // Apply accent
  useEffect(() => {
    const map = {
      lime:   { accent: "#5d7a1a", ink: "#ffffff", soft: "rgba(93,122,26,0.10)", line: "rgba(93,122,26,0.32)" },
      orange: { accent: "#c4632a", ink: "#ffffff", soft: "rgba(196,99,42,0.10)", line: "rgba(196,99,42,0.32)" },
      cyan:   { accent: "#1e7a72", ink: "#ffffff", soft: "rgba(30,122,114,0.10)", line: "rgba(30,122,114,0.32)" },
      violet: { accent: "#6a4ab4", ink: "#ffffff", soft: "rgba(106,74,180,0.10)", line: "rgba(106,74,180,0.32)" },
    };
    const t = map[tweaks.accent] || map.lime;
    document.documentElement.style.setProperty("--accent", t.accent);
    document.documentElement.style.setProperty("--accent-ink", t.ink);
    document.documentElement.style.setProperty("--accent-soft", t.soft);
    document.documentElement.style.setProperty("--accent-line", t.line);
  }, [tweaks.accent]);

  const [scene, setScene] = useState("home");
  const [chatOpen, setChatOpen] = useState(true);
  const [chatLog, setChatLog] = useState({});

  // If new user, force-keep chat closed on home (focus the empty state)
  // and auto-redirect any locked nav to home.
  useEffect(() => {
    if (!profileReady && scene !== "home" && scene !== "onboard") {
      setScene("home");
    }
  }, [profileReady, scene]);
  useEffect(() => {
    if (!profileReady && scene === "home") setChatOpen(false);
  }, [profileReady, scene]);

  const startOnboarding = () => {
    setScene("onboard");
    setChatOpen(true);
  };
  const finishOnboarding = () => {
    setTweak("newUser", false);
    setScene("profile");
    setChatOpen(true);
  };

  // Initialize chat log per scene from script
  useEffect(() => {
    setChatLog(prev => {
      if (prev[scene]) return prev;
      return { ...prev, [scene]: SCENE_CHATS[scene]?.messages || [] };
    });
  }, [scene]);

  const onAsk = (text) => {
    setChatOpen(true);
    setChatLog(prev => {
      const cur = prev[scene] || SCENE_CHATS[scene]?.messages || [];
      const next = [...cur, { role: "user", text }, {
        role: "ai",
        text: synthReply(scene, text),
        sources: synthSources(scene, text),
      }];
      return { ...prev, [scene]: next };
    });
  };

  const messages = chatLog[scene] || SCENE_CHATS[scene]?.messages || [];
  const suggestions = SCENE_CHATS[scene]?.suggestions || [];

  return (
    <>
      <AppShell
        active={scene}
        onNav={setScene}
        density={tweaks.density}
        chatOpen={chatOpen}
        layout={tweaks.layout}
        onChat={setChatOpen}
        locked={!profileReady}
        chat={
          <ChatDock
            scene={scene === "onboard" ? "onboard" : scene}
            messages={messages}
            suggestions={suggestions}
            onSend={onAsk}
            onClose={() => setChatOpen(false)}
            onFinishOnboarding={!profileReady && scene === "onboard" ? finishOnboarding : undefined}
          />
        }
      >
        {scene === "home"     && (profileReady
          ? <HomeView onNav={setScene} onAsk={onAsk}/>
          : <EmptyHomeView onStart={startOnboarding}/>)}
        {scene === "profile"  && profileReady && <ProfileView onAsk={onAsk}/>}
        {scene === "ideate"   && profileReady && <IdeateView onAsk={onAsk}/>}
        {scene === "retro"    && profileReady && <RetroView onAsk={onAsk}/>}
        {scene === "onboard"  && <OnboardView onAsk={onAsk} onFinish={finishOnboarding}/>}
      </AppShell>

      {/* Bottom-right scene jumper for demo */}
      <div style={{
        position: "fixed", bottom: 16, left: 236,
        display: "flex", gap: 6, padding: 6,
        background: "var(--bg-1)", border: "1px solid var(--line-1)",
        borderRadius: 999, boxShadow: "var(--shadow-md)",
        fontSize: 11.5, zIndex: 50,
      }}>
        <span style={{ padding: "6px 10px", color: "var(--fg-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}>DEMO ▸</span>
        <button onClick={() => { setTweak("newUser", true); setScene("home"); setChatOpen(false); }} style={{
          padding: "6px 10px", borderRadius: 999, border: "none",
          background: !profileReady && scene === "home" ? "var(--accent)" : "transparent",
          color: !profileReady && scene === "home" ? "var(--accent-ink)" : "var(--fg-1)",
          fontWeight: !profileReady && scene === "home" ? 600 : 400,
          cursor: "pointer", fontSize: 11.5,
        }}>0. New user</button>
        {[
          { id: "onboard", label: "1. Onboard" },
          { id: "profile", label: "→ Profile" },
          { id: "ideate",  label: "→ Ideate" },
          { id: "retro",   label: "→ Retro" },
          { id: "home",    label: "→ Home" },
        ].map(s => (
          <button key={s.id} onClick={() => { if (s.id !== "onboard" && s.id !== "home") setTweak("newUser", false); setScene(s.id); setChatOpen(true); }} style={{
            padding: "6px 10px", borderRadius: 999, border: "none",
            background: scene === s.id && !(s.id === "home" && !profileReady) ? "var(--accent)" : "transparent",
            color: scene === s.id && !(s.id === "home" && !profileReady) ? "var(--accent-ink)" : "var(--fg-1)",
            fontWeight: scene === s.id ? 600 : 400,
            cursor: "pointer", fontSize: 11.5,
          }}>{s.label}</button>
        ))}
      </div>

      {(
        <TweaksPanel>
          <TweakSection label="主题">
            <TweakRadio
              label="主题色"
              value={tweaks.accent}
              options={[
                { value: "lime", label: "Lime" },
                { value: "orange", label: "Orange" },
                { value: "cyan", label: "Cyan" },
                { value: "violet", label: "Violet" },
              ]}
              onChange={v => setTweak("accent", v)}
            />
          </TweakSection>
          <TweakSection label="布局">
            <TweakRadio
              label="对话/画布"
              value={tweaks.layout}
              options={[
                { value: "split", label: "并排" },
                { value: "focus", label: "隐藏对话" },
              ]}
              onChange={v => setTweak("layout", v)}
            />
            <TweakRadio
              label="信息密度"
              value={tweaks.density}
              options={[
                { value: "compact", label: "紧凑" },
                { value: "cozy", label: "舒适" },
                { value: "roomy", label: "宽松" },
              ]}
              onChange={v => setTweak("density", v)}
            />
          </TweakSection>
        </TweaksPanel>
      )}
    </>
  );
};

// Light synthetic replies for the demo — keep them grounded in scene.
function synthReply(scene, text) {
  const t = text.toLowerCase();
  if (scene === "retro") {
    if (t.includes("钩子")) return "黑屏静态钩子能拉住人，是因为它制造了\"即将发生什么\"的预期。但你紧跟的口播是\"信息型\"的（介绍人物背景），它没有继续制造预期，反而开始解题 —— 观众潜意识觉得\"已经知道了\"，于是滑走。\n建议：钩子之后接的不应该是解释，而是一个新的更小的悬念。";
    if (t.includes("考研")) return "好，我把这个动作放到了你的待办里。下次画像更新时会把「考研陪伴」从待探索项移到候选确定项 —— 不过我想再积累 1-2 条数据点再确认。";
    return "好的，我帮你看一下。这条数据的归因主要在节奏，不在选题本身。要不要我把分析展开成一份 PDF？";
  }
  if (scene === "ideate") {
    if (t.includes("vlog")) return "如果做成 vlog（第一视角），画像贴合度会从 74 涨到 86 —— 因为你本来就习惯第一视角。但差异化空间会从 81 降到 58，因为大量 vlog 都长这样。\n trade-off：纪录片更新颖但执行更难，vlog 更稳但更卷。";
    return "好问题。我从你的画像和近期趋势里抽了几个角度，你可以挑一个继续展开。";
  }
  if (scene === "profile") {
    return "好，我把这个变更放到画像变更日志里了。下次你打开复盘时会看到「基于新画像重新解读」的提示。";
  }
  return "我可以从这个角度展开。给我一秒整理。";
}
function synthSources(scene, text) {
  if (scene === "retro") return ["完播曲线", "87 条评论"];
  if (scene === "ideate") return ["你的画像", "近 7 天趋势"];
  if (scene === "profile") return ["12 条视频", "Onboarding 对话"];
  return null;
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
