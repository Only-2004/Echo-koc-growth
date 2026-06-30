/* MODULE B — Ideation & Pre-publication Strategy.
 * Input: a user idea. Output: 4 pillars — 热度 / 画像贴合 / 差异化 / 执行要点.
 * Every recommendation is tagged: profile-driven vs trend-driven (no black box). */

const IDEA = {
  draft: "下一期想拍：" +
    "「考研图书馆里那个永远占座的人到底是谁」——" +
    "用半纪录片半搞笑的口吻，跟拍我自己一周的图书馆抢座经历。",
};

const HEAT = {
  score: 0.72,
  verdict: "推流期 · 还有 6-10 天窗口",
  cluster: "考研日常 / 图书馆类",
  metrics: [
    { label: "近 7 天发布量", value: "+34%", trend: "up" },
    { label: "近 7 天互动量", value: "+58%", trend: "up" },
    { label: "供给/需求比", value: "0.81", trend: "down", hint: "<1 = 内容供给不足，红利期" },
    { label: "同类爆款门槛", value: "8.4 万赞", trend: "flat" },
  ],
  spark: [22, 26, 31, 28, 35, 41, 52, 58, 61, 70, 82, 76, 84],
};

const FIT = {
  matchConfirm: 0.88,
  matchPerson:  0.74,
  exploreValue: 0.92,
  notes: [
    { source: "profile", text: "和「校园 vlog」「考研中」两个画像项强一致 — 你不需要重新建立可信度。" },
    { source: "profile", text: "镜头语言（手持 / 第一视角）正好适配「跟拍纪录片」格式。" },
    { source: "explore", text: "这条会直接验证「下一阶段重心：生活向 vs 考研向」这个待探索项 —— 看反响就能决策。" },
    { source: "trend",   text: "受众画像 18-22 岁占 61%，本主题平台数据该年龄段互动率超均值 1.8x。" },
  ],
};

const DIFF = [
  { angle: "视角差异", text: "大多数同主题内容是\"图书馆 vlog\"，第三视角扫场。你可以用「我盯了TA 一周」的悬疑视角，把日常变成轻轻的故事。", source: "profile" },
  { angle: "人设差异", text: "你有原神玩家这个标签，结尾可以放一个\"原来 TA 也在玩同一个深渊\"的彩蛋钩，把两个看似无关的标签连起来。", source: "profile" },
  { angle: "内容差异", text: "目前同类视频普遍把\"考研\"做得很苦情。你的活力 + 幽默感人设可以反着来 —— 把抢座做成喜剧。", source: "profile" },
  { angle: "节奏差异", text: "热度排行 TOP 5 平均时长 47秒，TOP 1 是 1分20秒。你这条建议做到 60-75秒。", source: "trend" },
];

const EXEC = {
  hook:    { sec: "0-3s", text: "黑屏 + 一句话：「这个人，七天没换过位置。」 直接抛悬念。" },
  pacing:  [
    { at: "0-3s",  what: "钩子" },
    { at: "3-15s", what: "建立\"目标人物\"，介绍图书馆背景" },
    { at: "15-45s", what: "你的视角观察 + 三段笑点 / 反差" },
    { at: "45-60s", what: "揭示 + 原神彩蛋（连接你自己人设）" },
    { at: "60-70s", what: "CTA：评论区聊聊\"你校的占座王\"" },
  ],
  cta:     "结尾抛话题：你校占座王是谁？把你拍到的发评论区。",
  tags:    ["#考研日常", "#图书馆", "#校园vlog", "#26考研", "#好笑的同学"],
};

const IdeateView = ({ onAsk }) => {
  const [tab, setTab] = useState("heat");
  return (
    <div style={{ maxWidth: 1280, display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Idea input */}
      <div style={{
        background: "var(--bg-1)", border: "1px solid var(--line-1)",
        borderRadius: "var(--r-xl)", padding: 24,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <I.Lightbulb size={16} style={{ color: "var(--accent)" }}/>
          <span className="h-mono" style={{ color: "var(--accent)" }}>YOUR IDEA</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-3)", marginLeft: "auto" }}>
            草稿 · 刚才更新
          </span>
        </div>
        <div style={{
          fontSize: 18, fontWeight: 500, lineHeight: 1.55,
          letterSpacing: "-0.005em", color: "var(--fg-0)",
        }}>{IDEA.draft}</div>
        <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
          <button className="btn"><I.Refresh size={14}/> 让我改一改这条 idea</button>
          <button className="btn" onClick={() => onAsk?.("帮我看看还有哪些可以拍的 idea")}><I.Sparkle size={14}/> 给我 3 个相邻方向</button>
          <button className="btn"><I.Bookmark size={14}/> 收藏到选题库</button>
          <div style={{ flex: 1 }}/>
          <button className="btn btn-primary"><I.Bolt size={14}/> 生成完整拍摄简报</button>
        </div>
      </div>

      {/* 4-pillar score row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <ScoreCard
          active={tab === "heat"}
          onClick={() => setTab("heat")}
          kicker="01 · 热度匹配度"
          score={HEAT.score}
          verdict={HEAT.verdict}
          tone="info"
        />
        <ScoreCard
          active={tab === "fit"}
          onClick={() => setTab("fit")}
          kicker="02 · 画像贴合度"
          score={(FIT.matchConfirm + FIT.matchPerson + FIT.exploreValue) / 3}
          verdict="高度贴合 · 还能验证待探索项"
          tone="person"
        />
        <ScoreCard
          active={tab === "diff"}
          onClick={() => setTab("diff")}
          kicker="03 · 差异化空间"
          score={0.81}
          verdict="4 个可切入的独特角度"
          tone="explore"
        />
        <ScoreCard
          active={tab === "exec"}
          onClick={() => setTab("exec")}
          kicker="04 · 执行要点"
          score={null}
          verdict="开头 / 节奏 / CTA / Tag 已生成"
          tone="accent"
          icon="Bolt"
        />
      </div>

      {/* Active tab content */}
      <div style={{
        background: "var(--bg-1)", border: "1px solid var(--line-1)",
        borderRadius: "var(--r-lg)", padding: 28,
        minHeight: 400,
      }}>
        {tab === "heat" && <HeatPanel onAsk={onAsk}/>}
        {tab === "fit"  && <FitPanel onAsk={onAsk}/>}
        {tab === "diff" && <DiffPanel onAsk={onAsk}/>}
        {tab === "exec" && <ExecPanel onAsk={onAsk}/>}
      </div>
    </div>
  );
};

const ScoreCard = ({ active, onClick, kicker, score, verdict, tone, icon }) => {
  const color = {
    info: "var(--info)", person: "var(--pillar-person)",
    explore: "var(--pillar-explore)", accent: "var(--accent)",
  }[tone];
  return (
    <button onClick={onClick} style={{
      textAlign: "left", padding: 18,
      background: active ? "var(--bg-1)" : "var(--bg-1)",
      border: "1px solid " + (active ? color : "var(--line-1)"),
      borderRadius: "var(--r-lg)",
      cursor: "pointer",
      display: "flex", flexDirection: "column", gap: 10,
      position: "relative",
      boxShadow: active ? `0 0 0 3px ${color}20` : "none",
      transition: "all .15s",
    }}>
      <div className="h-mono" style={{ color, fontSize: 9.5 }}>{kicker}</div>
      {score !== null ? (
        <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
          <span style={{ fontSize: 32, fontWeight: 600, letterSpacing: "-0.02em", color }}>{Math.round(score * 100)}</span>
          <span style={{ fontSize: 12, color: "var(--fg-3)", fontFamily: "var(--font-mono)" }}>/ 100</span>
        </div>
      ) : (
        <div style={{ fontSize: 32, fontWeight: 600, color, display: "flex", alignItems: "center", gap: 8 }}>
          {React.createElement(I[icon || "Bolt"], { size: 26 })}
          <span style={{ fontSize: 14, fontWeight: 500, color: "var(--fg-1)" }}>READY</span>
        </div>
      )}
      <div style={{ fontSize: 12, color: "var(--fg-1)", lineHeight: 1.5 }}>{verdict}</div>
    </button>
  );
};

const HeatPanel = ({ onAsk }) => (
  <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 32 }}>
    <div>
      <SectionTitle
        kicker="01 · 热度匹配度 · 趋势驱动"
        title="这个主题正在涨"
        sub="过去 7 天「考研日常 / 图书馆类」的发布量、互动量都在快速上升，但供给还没填满需求。建议尽快发。"
      />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
        {HEAT.metrics.map((m, i) => (
          <div key={i} style={{
            padding: 16, borderRadius: 10,
            background: "var(--bg-2)", border: "1px solid var(--line-0)",
          }}>
            <div className="h-mono" style={{ marginBottom: 8 }}>{m.label}</div>
            <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.01em", display: "flex", alignItems: "center", gap: 8 }}>
              {m.value}
              {m.trend === "up"   && <I.ArrowUp size={14} style={{ color: "var(--pos)" }}/>}
              {m.trend === "down" && <I.ArrowDown size={14} style={{ color: m.label.includes("供给") ? "var(--pos)" : "var(--neg)" }}/>}
            </div>
            {m.hint && <div style={{ fontSize: 11, color: "var(--fg-3)", marginTop: 4 }}>{m.hint}</div>}
          </div>
        ))}
      </div>
    </div>
    <div>
      <div className="h-mono" style={{ marginBottom: 12 }}>同类话题热度走势 · 近 13 天</div>
      <div style={{
        padding: 20, background: "var(--bg-2)", borderRadius: 10,
        border: "1px solid var(--line-0)",
      }}>
        <Sparkline values={HEAT.spark} width={320} height={100} color="var(--info)" fill={true}/>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fg-3)" }}>
          <span>4/14</span><span>4/20</span><span>今天</span>
        </div>
      </div>
      <button onClick={() => onAsk?.("这个主题的爆款都长什么样？")} style={{
        width: "100%", marginTop: 12,
        padding: "10px 14px", borderRadius: 10,
        background: "var(--bg-2)", border: "1px solid var(--line-1)",
        color: "var(--fg-0)", fontSize: 12.5, textAlign: "left",
        display: "flex", alignItems: "center", gap: 10, cursor: "pointer",
      }}>
        <I.Trend size={14} style={{ color: "var(--info)" }}/>
        看 12 个 TOP 同类爆款
        <I.ChevronR size={14} style={{ marginLeft: "auto", color: "var(--fg-3)" }}/>
      </button>
    </div>
  </div>
);

const FitPanel = ({ onAsk }) => (
  <div>
    <SectionTitle
      kicker="02 · 画像贴合度 · 画像驱动"
      title="这条 idea 和你这个人的契合度"
      sub="拆成三个维度：和你已确定的方向一致吗？能挖掘你的独特点吗？最重要 —— 它能帮你回答还没想清楚的问题吗？"
    />
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
      <FitBar label="与确定项一致性" tone="confirm" value={FIT.matchConfirm} hint="校园 vlog · 考研中"/>
      <FitBar label="个性化资产挖掘" tone="person" value={FIT.matchPerson} hint="活力 / 幽默 / 原神标签"/>
      <FitBar label="对待探索项的验证价值" tone="explore" value={FIT.exploreValue} hint="生活向 vs 考研向"/>
    </div>
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {FIT.notes.map((n, i) => (
        <div key={i} style={{
          display: "flex", gap: 12,
          padding: "14px 16px",
          background: "var(--bg-2)", borderRadius: 10,
          border: "1px solid var(--line-0)",
        }}>
          <div style={{ flexShrink: 0, marginTop: 1 }}>
            <SourceTag source={n.source}/>
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.6, color: "var(--fg-0)" }}>{n.text}</div>
          <button className="btn-ghost" onClick={() => onAsk?.(`展开聊：${n.text}`)} style={{
            flexShrink: 0, marginLeft: "auto", padding: "4px 8px",
            border: "1px solid var(--line-1)", borderRadius: 6,
            background: "transparent", color: "var(--fg-2)",
            fontSize: 11, display: "inline-flex", alignItems: "center", gap: 4,
          }}>追问 <I.ChevronR size={11}/></button>
        </div>
      ))}
    </div>
  </div>
);

const FitBar = ({ label, tone, value, hint }) => (
  <div style={{
    padding: 16, background: "var(--bg-2)", borderRadius: 10,
    border: "1px solid var(--line-0)",
  }}>
    <div className="h-mono" style={{ marginBottom: 10, color: `var(--pillar-${tone})` }}>{label}</div>
    <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 8 }}>
      <span style={{ fontSize: 26, fontWeight: 600, color: `var(--pillar-${tone})` }}>{Math.round(value * 100)}</span>
      <span style={{ fontSize: 11, color: "var(--fg-3)", fontFamily: "var(--font-mono)" }}>/ 100</span>
    </div>
    <Score value={value} color={`var(--pillar-${tone})`}/>
    <div style={{ fontSize: 11, color: "var(--fg-2)", marginTop: 8 }}>{hint}</div>
  </div>
);

const DiffPanel = ({ onAsk }) => (
  <div>
    <SectionTitle
      kicker="03 · 差异化建议"
      title="同主题里的人都在做什么 — 你怎么不一样"
      sub="基于近 30 天 47 条同主题视频的内容拆解，结合你的画像，给你 4 个角度。"
    />
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      {DIFF.map((d, i) => (
        <div key={i} style={{
          padding: 18, background: "var(--bg-2)", borderRadius: 12,
          border: "1px solid var(--line-0)",
          display: "flex", flexDirection: "column", gap: 10,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="h-mono" style={{ fontSize: 9.5, color: "var(--fg-2)" }}>{String(i + 1).padStart(2, "0")}</span>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{d.angle}</span>
            <div style={{ marginLeft: "auto" }}><SourceTag source={d.source}/></div>
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.65, color: "var(--fg-1)" }}>{d.text}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button className="btn" style={{ padding: "5px 10px", fontSize: 11.5 }}>采用这个角度</button>
            <button className="btn-ghost" onClick={() => onAsk?.(`帮我把"${d.angle}"展开`)} style={{
              padding: "5px 10px", fontSize: 11.5, color: "var(--fg-2)",
              border: "1px solid var(--line-1)", borderRadius: 999, background: "transparent",
            }}>追问</button>
          </div>
        </div>
      ))}
    </div>
  </div>
);

const ExecPanel = ({ onAsk }) => (
  <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 28 }}>
    <div>
      <SectionTitle
        kicker="04 · 执行要点"
        title="可以按这个拍"
        sub="开头钩子、节奏、CTA、Tag 已经为你定好。可以直接拷贝去剪辑。"
      />
      {/* Hook */}
      <div style={{
        padding: 18, borderRadius: 12,
        background: "linear-gradient(180deg, var(--accent-soft), transparent 80%)",
        border: "1px solid var(--accent-line)",
        marginBottom: 16,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <span className="h-mono" style={{ color: "var(--accent)" }}>开场钩子 · {EXEC.hook.sec}</span>
        </div>
        <div style={{ fontFamily: "var(--font-serif)", fontSize: 18, lineHeight: 1.5, color: "var(--fg-0)" }}>
          "{EXEC.hook.text}"
        </div>
      </div>

      {/* Pacing timeline */}
      <div className="h-mono" style={{ marginBottom: 10 }}>节奏建议</div>
      <div style={{
        background: "var(--bg-2)", borderRadius: 12,
        border: "1px solid var(--line-0)",
        padding: 16,
      }}>
        {EXEC.pacing.map((p, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "flex-start", gap: 14,
            paddingBottom: 12,
            borderBottom: i < EXEC.pacing.length - 1 ? "1px solid var(--line-0)" : "none",
            marginBottom: i < EXEC.pacing.length - 1 ? 12 : 0,
          }}>
            <span style={{
              fontFamily: "var(--font-mono)", fontSize: 11,
              padding: "4px 10px", borderRadius: 999,
              background: "var(--bg-3)", color: "var(--fg-1)",
              minWidth: 64, textAlign: "center", flexShrink: 0,
            }}>{p.at}</span>
            <span style={{ fontSize: 13, color: "var(--fg-0)", lineHeight: 1.5, flex: 1 }}>{p.what}</span>
          </div>
        ))}
      </div>
    </div>
    <div>
      <div className="h-mono" style={{ marginBottom: 10 }}>CTA</div>
      <div style={{
        padding: 16, background: "var(--bg-2)",
        border: "1px solid var(--line-0)", borderRadius: 12,
        fontSize: 13.5, lineHeight: 1.6, color: "var(--fg-0)", marginBottom: 18,
      }}>{EXEC.cta}</div>
      <div className="h-mono" style={{ marginBottom: 10 }}>Tag 推荐</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 18 }}>
        {EXEC.tags.map((t, i) => (
          <span key={i} className="chip" data-tone="accent" style={{ fontFamily: "var(--font-mono)" }}>{t}</span>
        ))}
      </div>
      <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }}>
        <I.Bolt size={14}/> 导出为拍摄简报 PDF
      </button>
      <button className="btn" style={{ width: "100%", justifyContent: "center", marginTop: 8 }} onClick={() => onAsk?.("发完后帮我跟踪表现")}>
        <I.Pin size={14}/> 发完后自动加入复盘
      </button>
    </div>
  </div>
);

Object.assign(window, { IdeateView });
