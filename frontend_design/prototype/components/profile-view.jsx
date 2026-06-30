/* MODULE A — KOC Profile main view.
 * Three-state object: 确定项 (confirm) / 个性化项 (person) / 待探索项 (explore).
 * Plus "evidence" links back to onboarding answers + video metadata. */

const PROFILE_DATA = {
  confirm: [
    { tag: "平台", value: "抖音" },
    { tag: "粉丝量级", value: "1.2K" },
    { tag: "稳定方向", value: "校园 vlog · 探店" },
    { tag: "镜头语言", value: "手持 / 第一视角" },
    { tag: "更新频率", value: "周更 1.5 条" },
    { tag: "封面风格", value: "实拍照 + 大字标题" },
  ],
  person: [
    { label: "活力", weight: 0.86, evidence: "12 条视频里高频出现感叹语 / 笑声轨" },
    { label: "幽默感", weight: 0.71, evidence: "评论区 \"哈哈\" 占比 28%，远高于同量级基线" },
    { label: "考研中", weight: 0.95, evidence: "Onboarding 提到正在准备 26 考研（计算机）" },
    { label: "原神资深玩家", weight: 0.78, evidence: "3 条视频自然带过游戏术语，1 条玩家专属梗" },
    { label: "外向 · 爱表达", weight: 0.82, evidence: "口播平均 47% 时长，画面正脸出镜率 64%" },
  ],
  explore: [
    { q: "下一阶段重心：生活向 vs 考研向？", status: "尚未决定", hint: "两条都有粉丝拐点，但受众重叠 < 18%" },
    { q: "希望吸引的目标受众？", status: "假设中", hint: "目前默认\"同校园 18-22 岁\"，可验证" },
    { q: "希望接的商单类型？", status: "未填", hint: "建议在前 3 期视频里埋测试型软广" },
  ],
};

const Pillar = ({ tone, kicker, title, count, children }) => (
  <div style={{
    background: "var(--bg-1)",
    border: "1px solid var(--line-1)",
    borderRadius: "var(--r-lg)",
    padding: "var(--s-pad-card, 24px)",
    display: "flex", flexDirection: "column",
    minHeight: 360,
  }}>
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%",
        background: `var(--pillar-${tone})`,
      }}/>
      <span className="h-mono" style={{ color: `var(--pillar-${tone})`, fontSize: 9.5 }}>{kicker}</span>
      <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-2)" }}>{count}</span>
    </div>
    <div style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.01em", marginBottom: 16 }}>{title}</div>
    <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>{children}</div>
  </div>
);

const ProfileView = ({ onAsk }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28, maxWidth: 1280 }}>
      {/* Header card — identity */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "auto 1fr auto",
        gap: 28, alignItems: "center",
        background: "var(--bg-1)",
        border: "1px solid var(--line-1)",
        borderRadius: "var(--r-xl)",
        padding: "28px 32px",
      }}>
        <Avatar size={72}/>
        <div>
          <div className="h-mono" style={{ marginBottom: 6 }}>YOUR KOC PROFILE</div>
          <div style={{ fontSize: 30, fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1.15 }}>
            <span style={{ color: "var(--fg-2)", fontWeight: 400 }}>一个</span>
            <span style={{ marginLeft: 10 }}>有活力的</span>
            <span style={{ marginLeft: 10, color: "var(--accent)" }}>校园 vlog 创作者</span>
          </div>
          <div style={{ fontSize: 14, color: "var(--fg-1)", marginTop: 8, lineHeight: 1.6, maxWidth: 720 }}>
            正在准备考研，原神资深玩家，镜头放得开。账号目前在<span style={{ color: "var(--accent)" }}>校园生活</span>与<span style={{ color: "var(--pillar-explore)" }}>考研记录</span>两个方向之间，尚未做出最终选择 — 这是我们接下来的探索重点。
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            <span className="chip" data-tone="confirm"><span className="dot"/>抖音 · 1.2K 粉</span>
            <span className="chip" data-tone="confirm"><span className="dot"/>校园 vlog</span>
            <span className="chip" data-tone="person"><span className="dot"/>26 考研中</span>
            <span className="chip" data-tone="person"><span className="dot"/>原神玩家</span>
            <span className="chip" data-tone="explore"><span className="dot"/>2 个方向待决</span>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <button className="btn btn-primary" onClick={() => onAsk?.("帮我把画像 export 给我看看")}>
            <I.Sparkle size={14}/> 重新对话以更新画像
          </button>
          <button className="btn">
            <I.Refresh size={14}/> 从新视频中再抽取
          </button>
          <div style={{ fontSize: 11, color: "var(--fg-3)", marginTop: 4, textAlign: "right" }}>
            上次更新：2 天前 · 基于 12 条视频 + 1 次对话
          </div>
        </div>
      </div>

      {/* Three pillars */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        <Pillar tone="confirm" kicker="确定项 · CONFIRMED" title="已经稳下来的" count={`${PROFILE_DATA.confirm.length} 项`}>
          {PROFILE_DATA.confirm.map((it, i) => (
            <div key={i} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 0", borderBottom: i < PROFILE_DATA.confirm.length - 1 ? "1px solid var(--line-0)" : "none",
            }}>
              <span style={{ fontSize: 12.5, color: "var(--fg-2)" }}>{it.tag}</span>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{it.value}</span>
            </div>
          ))}
        </Pillar>

        <Pillar tone="person" kicker="个性化项 · YOU" title="可以挖掘的差异化" count={`${PROFILE_DATA.person.length} 项`}>
          {PROFILE_DATA.person.map((it, i) => (
            <div key={i} style={{ padding: "8px 0" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{it.label}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-2)" }}>{Math.round(it.weight*100)}</span>
              </div>
              <Score value={it.weight} color="var(--pillar-person)"/>
              <div style={{ fontSize: 11, color: "var(--fg-3)", marginTop: 6, lineHeight: 1.5 }}>↳ {it.evidence}</div>
            </div>
          ))}
        </Pillar>

        <Pillar tone="explore" kicker="待探索项 · OPEN" title="还没想清楚的" count={`${PROFILE_DATA.explore.length} 项`}>
          {PROFILE_DATA.explore.map((it, i) => (
            <button key={i} onClick={() => onAsk?.(`聊聊：${it.q}`)} style={{
              textAlign: "left",
              padding: 12,
              background: "rgba(122,78,196,0.05)",
              border: "1px dashed rgba(122,78,196,0.32)",
              borderRadius: 10,
              cursor: "pointer",
              display: "flex", flexDirection: "column", gap: 6,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: "var(--fg-0)" }}>{it.q}</span>
                <I.ChevronR size={14} style={{ color: "var(--pillar-explore)", flexShrink: 0, marginTop: 2 }}/>
              </div>
              <div style={{ fontSize: 11, color: "var(--pillar-explore)", fontFamily: "var(--font-mono)", letterSpacing: "0.04em" }}>{it.status}</div>
              <div style={{ fontSize: 11.5, color: "var(--fg-2)", lineHeight: 1.5 }}>{it.hint}</div>
            </button>
          ))}
        </Pillar>
      </div>

      {/* Audience hypothesis */}
      <div style={{
        background: "var(--bg-1)", border: "1px solid var(--line-1)",
        borderRadius: "var(--r-lg)", padding: 24,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
          <I.User size={16} style={{ color: "var(--fg-2)" }}/>
          <div style={{ fontSize: 15, fontWeight: 600 }}>当前粉丝构成</div>
          <span className="chip" style={{ fontSize: 10.5 }}>来自抖音后台 · 自动同步</span>
          <div style={{ marginLeft: "auto", fontSize: 11, color: "var(--fg-3)" }}>1,238 人 · 男 41% / 女 59%</div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr", gap: 24 }}>
          <div>
            <div className="h-mono" style={{ marginBottom: 10 }}>年龄分布</div>
            <AgeBars/>
          </div>
          <div>
            <div className="h-mono" style={{ marginBottom: 10 }}>来源城市 TOP 5</div>
            {[
              ["杭州", 0.42], ["上海", 0.18], ["北京", 0.11], ["南京", 0.08], ["其他", 0.21],
            ].map(([c, w], i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <span style={{ fontSize: 12, width: 48, color: "var(--fg-1)" }}>{c}</span>
                <Score value={w} color="var(--info)"/>
                <span style={{ fontSize: 11, color: "var(--fg-2)", fontFamily: "var(--font-mono)", minWidth: 32, textAlign: "right" }}>{Math.round(w*100)}%</span>
              </div>
            ))}
          </div>
          <div>
            <div className="h-mono" style={{ marginBottom: 10 }}>关键词共现</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {[["考研", 1], ["校园", 1], ["杭州", 0.8], ["原神", 0.7], ["vlog", 0.6], ["探店", 0.6], ["奶茶", 0.4], ["自习", 0.4], ["计算机", 0.4]].map(([k, w], i) => (
                <span key={i} style={{
                  padding: "4px 10px",
                  fontSize: 11 + w * 4,
                  borderRadius: 999,
                  background: `rgba(93,122,26,${w * 0.10})`,
                  border: `1px solid rgba(93,122,26,${w * 0.4})`,
                  color: "var(--accent)",
                }}>{k}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const AgeBars = () => {
  const data = [
    { age: "<18", v: 0.08 },
    { age: "18-22", v: 0.61 },
    { age: "23-26", v: 0.22 },
    { age: "27-30", v: 0.06 },
    { age: "30+", v: 0.03 },
  ];
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 120 }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, textAlign: "center" }}>
          <div style={{
            height: `${d.v * 100}%`,
            background: i === 1 ? "var(--accent)" : "var(--bg-3)",
            borderRadius: "4px 4px 0 0",
            marginBottom: 8,
            position: "relative",
            minHeight: 4,
          }}>
            <span style={{
              position: "absolute", top: -18, left: "50%", transform: "translateX(-50%)",
              fontSize: 10, color: i === 1 ? "var(--accent)" : "var(--fg-2)",
              fontFamily: "var(--font-mono)",
            }}>{Math.round(d.v * 100)}</span>
          </div>
          <div style={{ fontSize: 10.5, color: "var(--fg-2)", fontFamily: "var(--font-mono)" }}>{d.age}</div>
        </div>
      ))}
    </div>
  );
};

Object.assign(window, { ProfileView, PROFILE_DATA });
