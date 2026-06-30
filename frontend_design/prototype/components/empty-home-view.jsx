/* Empty-state Home — shown to new users who have no profile yet.
 * Single, focused CTA: 创建画像. Other modules are locked until done. */

const EmptyHomeView = ({ onStart }) => (
  <div style={{
    maxWidth: 760, margin: "40px auto 0",
    display: "flex", flexDirection: "column", gap: 28,
  }}>
    <div>
      <div className="h-mono" style={{ marginBottom: 10 }}>欢迎，第一步</div>
      <h1 style={{
        fontSize: 38, lineHeight: 1.15, letterSpacing: "-0.02em",
        fontWeight: 600, margin: 0, color: "var(--fg-0)",
      }}>
        我先帮你建一个 <span style={{ color: "var(--accent)" }}>KOC 画像</span>。<br/>
        所有别的事都从它长出来。
      </h1>
      <p style={{
        marginTop: 18, fontSize: 15, lineHeight: 1.7,
        color: "var(--fg-1)", maxWidth: 600,
      }}>
        画像不是问卷，也不是标签云。它是你这个创作者「是谁、为谁创作、还在试什么」的实时记录 —— 我会基于它给你选题、做策略、跑复盘。
        没有画像，其他三个模块都没法工作。
      </p>
    </div>

    {/* Three locked cards previewing what unlocks */}
    <div style={{
      display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12,
    }}>
      {[
        { icon: "Lightbulb", title: "选题策略", body: "基于你的画像推选题，告诉你为什么推。" },
        { icon: "Chart", title: "复盘", body: "每条视频归因到画像里的某一项，告诉你下一步怎么走。" },
        { icon: "Brain", title: "AI 编排", body: "右侧持续对话 — 任何数字都能追问，任何建议都标了来源。" },
      ].map((m, i) => (
        <div key={i} style={{
          padding: 18, background: "var(--bg-1)",
          border: "1px dashed var(--line-2)", borderRadius: 14,
          opacity: 0.62, position: "relative",
        }}>
          <div style={{
            position: "absolute", top: 12, right: 12,
            width: 22, height: 22, borderRadius: 6,
            background: "var(--bg-2)", border: "1px solid var(--line-1)",
            display: "grid", placeItems: "center", color: "var(--fg-2)",
          }}>
            <I.Lock size={11}/>
          </div>
          <div style={{ color: "var(--fg-2)", marginBottom: 10 }}>
            {React.createElement(I[m.icon], { size: 18 })}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6, color: "var(--fg-1)" }}>{m.title}</div>
          <div style={{ fontSize: 12, color: "var(--fg-2)", lineHeight: 1.55 }}>{m.body}</div>
        </div>
      ))}
    </div>

    {/* Primary CTA */}
    <div style={{
      padding: 24,
      background: "var(--bg-1)",
      border: "1px solid var(--accent-line)",
      borderRadius: 18,
      display: "flex", alignItems: "center", gap: 20,
      boxShadow: "0 1px 0 var(--accent-soft) inset",
    }}>
      <div style={{
        width: 56, height: 56, borderRadius: 14,
        background: "var(--accent-soft)",
        border: "1px solid var(--accent-line)",
        display: "grid", placeItems: "center", color: "var(--accent)",
        flexShrink: 0,
      }}>
        <I.User size={24}/>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>开始创建你的 KOC 画像</div>
        <div style={{ fontSize: 12.5, color: "var(--fg-2)", lineHeight: 1.6 }}>
          一段对话 · 大约 5 分钟 · 你随时可以暂停。我会在你回答的同时把画像写出来给你看。
        </div>
      </div>
      <button onClick={onStart} className="btn-primary btn" style={{
        padding: "12px 22px", fontSize: 14, fontWeight: 600,
        display: "flex", alignItems: "center", gap: 8, flexShrink: 0,
      }}>
        开始对话 <I.ArrowR size={14}/>
      </button>
    </div>

    {/* Soft alternatives */}
    <div style={{
      display: "flex", gap: 8, alignItems: "center", justifyContent: "center",
      fontSize: 12, color: "var(--fg-2)",
    }}>
      <span>或者</span>
      <button className="btn btn-ghost" style={{
        padding: "6px 12px", fontSize: 12, color: "var(--fg-1)",
        background: "transparent", border: "1px solid var(--line-1)",
      }}>
        <I.Image size={12}/> 直接导入我的视频，让 AI 推断
      </button>
      <button className="btn btn-ghost" style={{
        padding: "6px 12px", fontSize: 12, color: "var(--fg-1)",
        background: "transparent", border: "1px solid var(--line-1)",
      }}>
        看一份示例画像
      </button>
    </div>
  </div>
);

Object.assign(window, { EmptyHomeView });
