# Beacon · KOC 成长伙伴 · 产品需求文档（PRD）

## 0. 文档说明

### 0.1 本文档目的

本文档是 Beacon 产品端到端 demo 的实施需求规范，**用作 Claude Code 进行任务分解与实现的输入**。提交给评委的产品介绍文档不在本 PRD 范围内，将后续基于本文档另写。

本文档配合以下四份模块级技术规范使用：

* `onboarding_agent_demo_spec.md`
* `content_strategy_agent_demo_spec.md`
* `retro_insight_agent_demo_spec.md`
* `orchestrator_agent_demo_spec.md`

PRD 中涉及 agent 内部 workflow / prompt / memory 时直接引用上述文档，不再重复展开。

### 0.2 比赛背景与评分对齐

参赛对象为 PCG 校园 AI 产品创意大赛。Demo 形式：评委可以打开线上 web app，按照预设流程输入交互（用户数据为 mock，AI 回复为真实模型输出），得到完整端到端的产品体验。

**评分细则**（必要项 + 加分项）与 Beacon 设计的对应关系将在第 3 章详述。本 PRD 在功能设计上对每个评分维度都有显式承接。

### 0.3 范围内 / 范围外

**范围内**：

* 一个挂在腾讯云上、可对外访问的前后端 web app（M9 已上线）
* 完整的端到端 AI 调用链路（前端交互 → 后端 agent → DeepSeek v4 → 返回结构化 + 自然语言响应 → 前端渲染）
* 6 个核心视图共 5 个 scene 字符串：`home`（gate=false 时渲染 EmptyHomeView，gate=true 时渲染 HomeView）/ `onboard` / `profile` / `ideate` / `retro`
* 常驻 chat dock + chat-everything 交互模型；前端按 scene 硬路由到 strategy/refine 与 retro/drill 两条专属路径，其余全部走 orchestrator agent 兜底
* Source tagging 强制约束，五元枚举：画像驱动 / 趋势驱动 / 数据驱动 / 历史复盘 / 用户偏好驱动
* Mock data 驱动的演示故事线（小A 这一 persona 的完整旅程，复盘段预生成 vid_016 / vid_019 / vid_020 三条候选报告，主线选 vid_019）

**范围外**：

* 真实平台 API 接入（抖音 / 小红书）
* 商单匹配模块
* 多平台账号同步
* Proactive AI 主动触发（demo 中以"假设视频已发布"跳转到 retro）
* 用户注册 / 登录系统（demo 单 persona）
* 真实数据持久化与多用户并发

---

## 1. 产品概述

### 1.1 产品名称与定位

**产品名称**：Beacon

**Tagline**：KOC 成长伙伴

**一句话定位**：一个为早期视频类 KOC 提供"画像建立 → 选题策略 → 复盘洞察"完整闭环的 AI 成长伙伴，帮助粉丝量在 1K 至 10K 之间、缺乏专业运营能力的创作者把账号专业化、个性化、规模化。

### 1.2 核心价值主张

传统的 KOC 成长困境有两类：要么靠运气与直觉摸索，浪费机会成本；要么找代运营或 MCN，门槛高、成本高、个人色彩被稀释。Beacon 通过四层能力解决这一空白：

**第一层：永远先做功课**。AI 不向用户发空白问卷，而是先消化账号现有数据，提出带证据的假设让用户验证。

**第二层：三态画像**。把 KOC 画像区分为"已确定 / 个性化 / 待探索"三种状态，把"还在思考的方向"作为一等公民，让产品具备"陪用户做战略探索"的能力。

**第三层：双轴策略**。每条选题建议同时基于"画像驱动 + 趋势驱动"双轴判断，且必须明示来源，不给黑箱建议。

**第四层：闭环验证**。每条策略明示一个 `key_focus` 锚点（一句中文描述最该重点观察的指标或现象），发布后 retro 模块以同 pillar 历史基线（`baseline_pillar`）为参考系做"策略意图 vs 实际表现"的多维归因，并把验证结果（hypothesis 状态变更 / 新增观察 / to_explore 收敛）实时回写画像，立即触发 `profile_v{n+1}` 落盘。这一步让 AI "越用越懂你"。

### 1.3 产品形态

Beacon 是一个 **conversational + structured 双形态**的 web app：左侧是结构化信息（画像、数据、卡片、图表），右侧是常驻的 AI orchestrator 对话区。每一个数据点、每一条建议都是"对话入口"，用户点击即可向下追问。Source tagging（画像驱动 / 趋势驱动 / 数据驱动 / 历史复盘 / 用户偏好驱动 共 5 类）作为强制契约，是产品建立用户信任的根基。

---

## 2. 用户与场景

### 2.1 目标用户画像

**核心用户**：早期视频类 KOC

* 粉丝量：数百至 10000
* 平台：抖音、小红书、B站为主（demo 不限定平台，产品平台无关）
* 创作背景：兴趣驱动、非专业团队、单人或小型组合
* 内容主题：暂未稳定，跨多个垂类（如校园生活、美食探店、学习日常等）
* 商业目标：希望接到与个人定位相关的小型商单，创造额外收入
* 痛点共识：账号定位不明、内容选题缺乏方法论、缺乏数据复盘能力

**典型 persona：小A**

* 在校大三学生，热爱表达自我
* 抖音账号 1000 粉丝，发布校园 vlog 与食堂探店
* 正在思考是否把考研内容作为新主轴
* 希望通过专业化运营接到与校园生活、学业、就业相关的商单

### 2.2 核心痛点（与设计对应）

| 痛点 | 设计响应 |
|---|---|
| 不知道账号该做什么主题，对自己缺乏准确定位 | Onboarding 模块的"AI 先做功课 + 三态画像" |
| 内容选题不够切题，制作节奏不好 | Ideate 模块的双轴评估 + 执行要点输出 |
| 缺乏复盘、迭代、归因能力 | Retro 模块的策略 vs 实际归因 + 评论挖掘 |
| 不知道 AI 给的建议靠不靠谱 | Source tagging 强制契约 |

### 2.3 用户故事

完整 persona 故事线见第 13 章 Demo 演示规范。本节列出三个核心 user story：

**Story 1（onboarding）**：小A 第一次进入 Beacon。看到 Empty Home，三个模块视觉上锁。点击"开始对话"，进入 onboarding。AI 已经分析过她的 15 条历史视频，第一句话就是"我看完了你的视频，初步感受到三个特征……"。小A 在 5 至 8 轮对话中验证了 AI 的假设、补充了自己的顾虑、确认了若干待探索方向。生成画像，三个模块解锁。

**Story 2（ideate）**：小A 想拍"考研期间一日三餐怎么吃才能不困"。在 Ideate 模块输入 idea。AI 拉出她的画像 + 当前趋势数据，给出四个维度评估（热度 / 贴合 / 差异 / 执行）。每条建议都标注来源。小A 觉得 hook 设计太苦情，在 chat dock 里追问"能不能轻松一点"，AI 实时调整并解释取舍。

**Story 3（retro）**：视频发布 24 小时后，小A 进入 Retro 模块。AI 把发布前的策略快照与实际数据并列展示：hook 命中、完播率不达预期、关注转化超预期且是 key indicator。小A 点击完播率数据卡，向下追问"为什么会在第 12 秒掉"，AI 沿 evidence 链给出回答。复盘结束后画像引擎更新："考研内容能与既有素材融合"这一 hypothesis 增加了 evidence。

---

## 3. 评分细则映射

每一条评分维度在产品中的体现都在此处显式声明，便于后续提交给评委的产品文档直接引用。

### 3.1 必要项

**赛道适配性**：Beacon 服务于校园场景中最具规模的群体之一（学生 KOC），与 PCG 业务场景（视频内容生态、创作者赋能）天然契合。Demo 故事线 persona 小A 即为在校大三学生。

**作品完整性**：从用户痛点（早期 KOC 运营困境）→ 解决方案（三态画像 + 双轴策略 + 闭环复盘）→ 功能（4 模块 + chat dock）→ 演示（端到端可调用 demo），逻辑闭环完备。提交内容包含可访问 web app + 完整设计文档 + agent spec + 本 PRD。

**创新性**：

* "AI 先做功课"的 onboarding 范式（区别于业界标配的空白问卷）
* "三态画像"显式区分确定 / 个性化 / 待探索，把战略探索作为一等公民
* "Source tagging 强制契约"的信任机制
* "策略 vs 实际"契约式归因，闭环可验证
* Chat-everything 交互模型，结构化 UI 与对话深度无缝切换

**用户洞察深度与准确性**：目标用户具体（在校学生 KOC，粉丝 1K 至 10K，跨垂类摸索）；痛点真实（来自创作者运营访谈与平台数据观察）；使用场景可还原（小A 完整旅程在 demo 中可被评委逐步走完）。

**方案 AI 原生性**：

* Onboarding 中 AI 的"先做功课"能力依赖 LLM 对历史内容的语义理解
* 选题策略的双轴决策依赖 LLM 对画像与趋势的联合推理
* Retro 的归因与受众信号挖掘依赖 LLM 对评论文本的语义聚类
* Chat dock 的 chat-everything 入口完全建立在 LLM 实时响应能力上
* 没有 AI，整个产品形态不成立。AI 不是附加功能，是产品骨架

### 3.2 加分项

**落地可行性**：

* 技术栈成熟（React + Tailwind + Node/Python 后端 + DeepSeek v4 API）
* 部署路径清晰（腾讯云）
* MVP 范围合理（单 persona、mock 数据、3 个核心 agent）
* 真实落地的关键依赖（平台数据接入）已在路线图中标注路径

**商业化能力**：

* 短期变现：B 端按席位订阅（MCN 机构 / 校园运营团队）
* 中期变现：商单匹配抽佣（Beacon 沉淀的画像与策略历史是匹配商单的天然资产）
* 长期变现：成为创作者成长基础设施，平台合作、数据洞察服务
* 本 PRD 第 15 章列出商业化路径与未来路线图

---

## 4. 产品架构总览

### 4.1 模块组成

Beacon 由四层组成，前三层是功能模块，第四层是贯穿性体验：

```
┌──────────────────────────────────────────────────────────┐
│  应用层（Web UI）                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Profile │  │  Ideate  │  │  Retro   │  │   Home   │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│              ↓ 任意元素可点击进入对话                     │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Chat Dock (Orchestrator)  · 常驻 · 上下文感知       │ │
│  └────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│  Agent 层（后端）                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐│
│  │ Onboarding Agent│  │ Strategy Agent  │  │Retro Agent ││
│  └─────────────────┘  └─────────────────┘  └────────────┘│
│  ┌────────────────────────────────────────────────────┐ │
│  │ Orchestrator Agent (chat dock 的对话路由)           │ │
│  └────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│  数据层                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │
│  │ Profile Store  │  │ Strategy Store │  │Insights    │ │
│  │ (committed     │  │ (snapshots)    │  │Store       │ │
│  │  profiles)     │  │                │  │(reports)   │ │
│  └────────────────┘  └────────────────┘  └────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Mock Data Store (read-only)                         │ │
│  │ account / videos / comments / audience / trends     │ │
│  └────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│  基础设施                                                 │
│  腾讯云（前端静态托管 + 后端容器/函数 + 对象存储）         │
│  DeepSeek v4 API（三档模型 flash/flash-thinking/pro）     │
└──────────────────────────────────────────────────────────┘
```

### 4.2 数据流

核心闭环（onboarding → ideate → retro → 回写画像）：

```
mock_data
   ↓
Onboarding Agent ──→ profile_v1.json ──┐
                                        ↓
                       Strategy Agent ──→ strategy_snapshot.json ──┐
                                                                    ↓
                                                  (假设发布完成)     │
                                                                    ↓
                                       Retro Agent ──→ insights_report.json
                                                  ↓
                                            profile_delta.json
                                                  ↓
                                           profile_v2.json (更新)
```

每一步的中间产物都持久化为 JSON，可在 demo 中被评委直接查看。

### 4.3 四个 Agent 的技术规范引用

详见已交付的四份模块 spec：

* `onboarding_agent_demo_spec.md`：八状态状态机（含 FINALIZE / DONE）、三层 memory、7 段 prompt（含 system + 6 阶段）、profile schema
* `content_strategy_agent_demo_spec.md`：八状态状态机（RECEIVE_IDEA → ... → FINALIZE）、三层 memory、8 段 prompt（含 system + 6 阶段 + feedback 分类辅助）、strategy snapshot schema
* `retro_insight_agent_demo_spec.md`：九状态状态机（LOAD → ... → FINALIZE）、三层 memory、8 段 prompt、insights report schema
* `orchestrator_agent_demo_spec.md`：两阶段 LLM（router + chat）、stateless、router_system + 5 个 scene prompt、RouteDecision schema、source guard 强校验

---

## 5. 信息架构与导航

### 5.1 应用 Shell

3 列布局：

* **左侧导航栏**：220px 固定宽度
* **主内容区**：flex 1
* **Chat dock**：420px，可折叠（折叠时 0px，250ms 过渡）

### 5.2 导航项

| 序号 | 名称 | scene 标识 | gate=false 时渲染 | gate=true 时渲染 |
|---|---|---|---|---|
| 1 | 首页 | `home` | EmptyHomeView | HomeView |
| 2 | 我的画像 | `profile` | （锁，强制回 home） | ProfileView |
| 3 | 选题策略 | `ideate` | （锁，强制回 home） | IdeateView |
| 4 | 复盘 | `retro` | （锁，强制回 home） | RetroView |
| — | Onboarding | `onboard` | OnboardView | OnboardView（用户也可主动重跑） |

Onboarding 不出现在左侧导航，由 EmptyHomeView 的 primary CTA 进入；用户已生成 profile 后，仍可通过 ProfileView 顶部的"重置 Demo"按钮回到 onboard。

Gate 行为：当 `profileReady === false` 时，导航项 2/3/4 显示锁标 + opacity 0.55 + cursor not-allowed，点击无响应；同时 `SceneRouter` 在 useEffect 中兜底，把任何被锁 scene 强制 setScene('home')。完成 onboarding（FINALIZE → DONE）后立即解锁。

实际实现见 `frontend/src/views/SceneRouter.tsx`。

### 5.3 顶部条

Sticky 顶部条包含：

* 当前 scene 的 kicker label（小字标签，如"今天你能做什么"）
* 搜索按钮（⌘K，本期不实现搜索功能，按钮存在但点击仅打开 chat）
* "打开 AI 助手"按钮（仅在 chat dock 折叠时显示）

背景色 `rgba(250,249,246,0.85)` + `backdrop-filter: blur(12px)`。

### 5.4 Chat Dock（Orchestrator）

常驻右侧，由 Orchestrator Agent 驱动。详见第 7.7 节。

---

## 6. 详细功能规范：5 个核心场景

设计规范、布局、文案、交互严格按 README 中的 hi-fi 设计文档复刻。本节列出关键规格，组件级细节以 README 中的设计文件为准。

### 6.1 Empty Home（新用户首屏）

**目的**：把新用户强制 funnel 到 onboarding。

**布局**：居中 760px 列。三个 locked 预览卡片（1×3 网格）+ 一个大型 primary CTA 卡片 + 软性次级链接。

**关键文案**：

* H1："我先帮你建一个 **KOC 画像**。所有别的事都从它长出来。"
* Body："画像不是问卷，也不是标签云。它是你这个创作者「是谁、为谁创作、还在试什么」的实时记录……"
* CTA 卡片："开始创建你的 KOC 画像 · 一段对话 · 大约 5 分钟 · 你随时可以暂停。"
* 按钮："开始对话 →"

**Locked 卡片**：图标 + 标题 + 1 句预览 + 右上角小锁徽章 + opacity 0.62 + dashed border。

**交互**：点击 primary CTA → `scene = "onboard"` + 打开 chat dock。

### 6.2 Onboarding

**目的**：通过对话构建初版画像，全程让用户实时看到 AI 在记录什么。

**布局**：双列 `1fr 360px`：

* 左列：对话主面板（白卡，radius 20px，padding 24/28）
* 右列：sticky "LIVE · 我正在构建" 信息栏，列出每个 profile tick，每条带颜色圆点（绿 = confirm / 琥珀 = person / 紫 = explore）+ 时间戳

**顶部进度条**："第 X 步 / 共 4 步" + 4 个小进度块。

**对话模式**：AI 在开放式问题与 3 至 4 个建议 chip 之间交替。用户选 chip 或自由输入后，AI 回复包含推理 + 数据引用（"你这 12 条视频里有 3 条提到考研，平均完播率 41%；其他校园 vlog 平均 33%"）。

**Finish CTA**：约 7 个 ticks 后，accent 色横条出现："已经够了。我已经收集到 7 个信号，可以先生成第一版画像。剩下的我们可以在使用中慢慢补。" + 按钮"生成画像 →"。

**Agent 实现**：直接对应 `onboarding_agent_demo_spec.md` 中八状态流转（INIT → ANALYZE → PRESENT → VALIDATE ⇄ EXPLORE → SUMMARIZE → FINALIZE → DONE）。前端展示的 LIVE 信息栏对应 draft_profile 的实时变化。

**Demo 优化**：ANALYZE 阶段输出预跑固化为 `candidate_claims.json`，演示时直接加载，避免现场 LLM 输出方差。

### 6.3 Profile（我的画像）

**目的**：呈现"活的"KOC 画像，三态分列。

**布局**：

* 顶部：头像 + 昵称 + 粉丝数 + 上次更新时间 + "更新画像" pill
* 中部：3 列 Pillar 网格（确定项 / 个性化项 / 待探索项），每列一张卡片，含 kicker 标签 + 计数 + item 列表
* 待探索项的 item 是 dashed border + 可点击，点击打开 chat dock 并自动发起"把这一项展开聊聊"
* 受众假设卡片：full-width，列出受众分群与权重 chip（chip size + 饱和度反映权重）
* History strip：7 个迷你柱图，标题"画像更新频次"

**数据源**：从 profile store 读取最新版本的 `profile_v1.json`（或 `profile_v2.json` 如已 retro）。

### 6.4 Ideate（选题策略）

**目的**：评估具体 idea 与画像和趋势的匹配，输出可执行策略。

**布局**：

* 顶部：Idea 输入卡片（textarea + 可选语音/图像按钮，本期不实现语音/图像功能）
* 中部：tabs（"评估 / 趋势 / 差异化 / 节奏 + CTA"）
* Active tab 内容卡片：

  * **评估 tab**：4 个指标卡（热度 / 贴合 / 差异 / 执行），每卡含分数 + 1 句解释；下方 FitBar 行，每行对应画像的一个 pillar 与该 idea 的贴合度
  * **趋势 tab**：13 天趋势图 + 供需比
  * **差异化 tab**：3 张角度卡片
  * **节奏 tab**：时间轴（0s, 3s, 12s, 25s 等）+ 每个 beat 的内容 + CTA 卡片

**交互**：所有卡片可点击进入 chat（"展开「<标签>」这个数据"）。

**Agent 实现**：对应 `content_strategy_agent_demo_spec.md`。

* 用户在 Idea 输入卡片提交 → RECEIVE_IDEA → ANALYZE_IDEA → SCORE → STRATEGIZE → PRESENT
* 4 个指标卡的分数对应 strategy snapshot 中的 heat_analysis 与 profile_fit 的子字段（其中 `pillar_alignment.alignment` 是 high/medium/low 三档枚举）
* 节奏 tab 的时间轴对应 strategy snapshot 中的 execution.hook + execution.pacing
* CTA 卡片对应 execution.cta
* 顶部"重点观察"提示对应 execution.key_focus（一句中文锚点，retro 阶段据此挑选 is_key_indicator 卡片）

**Chat → Ideate 回填**：用户在 chat dock（scene=ideate · snapshot 未生成时）与 orchestrator 对话磨清选题方向后，scene_ideate prompt 会让 LLM 在 SUGGESTIONS 行加 `[GENERATE_BRIEF]<选题标题>` 触发器；前端解析后渲染为"生成拍摄简报 →"按钮，点击通过 zustand `pendingIdeaFromChat` 把对话中的"标题 + 核心角度 + 拍摄思路"自动回填到 idea 输入框，触发完整 strategy 流程。这是 chat-everything 模型的反向应用。

### 6.5 Retro（复盘）

**目的**：每条视频的发布后归因。

**布局**：

* **左侧视频列表**：最近 5 条视频，每行 = 缩略图占位 + 标题 + 完播率 chip（"低于基线" / "超出基线"），active 行高亮
* **主区域上方**：Strategy vs Reality 卡片，并排两面板（发布前假设 dashed / 实际数据 solid），中间分割箭头
* **主区域中部**：3 张 Insight 卡片，每张含标题 + 正文 + 嵌入式 follow-up 问题 chip
* **主区域下方**：评论聚类卡片，4 个主题聚类 + 样本评论

**交互**：每张 Insight 卡片是进入深度对话的入口（DRILL）。

**Agent 实现**：对应 `retro_insight_agent_demo_spec.md`。

* "Strategy vs Reality" 卡片对应 InsightsReport.strategy_review（verdict 取值 hit / miss / exceed / within_noise / partial，参照 baseline_pillar 判定）
* 3 张 Insight 卡片对应 InsightsReport.insights（confidence 是 high/medium/low 三档枚举；单条视频样本时不得为 high）
* 评论聚类卡片对应 InsightsReport.audience_signals
* 视频列表中的指标卡 `is_key_indicator=true` 时高亮，对应 strategy 阶段的 execution.key_focus 锚点

**预加载策略**：RetroView 挂载时后台 prefetch 全部预生成报告（vid_016 / vid_019 / vid_020），在用户切换视频时立刻命中本地 zustand 缓存（`retroAnalysisCache`），无可感延迟。预加载状态可在 store 的 `retroPreloadingIds` 观察。

**写回画像入口**：DRILL 阶段或 PRESENT 直接展示后，用户点 retro view 顶部的"写回画像 →"按钮触发 UPDATE_PROFILE → FINALIZE 流程，profile_v{n+1}.json 立刻落盘，前端通过 `profile_updated` SSE 事件自动拉取并切换到新版画像，整段闭环 2–3 秒可视化完成。

**Demo 优化**：本期 demo 中"假设发布完成"，从 ideate 提交后直接跳转到 retro 并默认选 vid_019（主线），跳过 proactive AI 触发逻辑。vid_016 / vid_020 用作评委追问"再看一条"时的备用切换。

### 6.6 Home（回访用户）

**目的**：回访用户的"今天你能做什么"。

**布局**：

* Hero greeting + headline insight（数据点用 accent 色）
* 3 张 next-action 卡片：复盘 / 选题 / 画像更新
* 30 天数据卡：粉丝增长 / 总播放 / 平均完播率 / 已发视频 + sparklines

**Demo 中**：完成完整闭环（onboard → ideate → retro）后回到 Home，展示新的 30 天数据（mock）和"画像更新频次 +1"标识，证明闭环走通。

### 6.7 Chat Dock + Orchestrator

**目的**：常驻右侧的 AI 助手，always context-aware；任何 scene 下都可被主面板的可点击元素呼叫。

**Header**：当前 scene 对应的角色名称（"今天我能帮你做什么" / "画像编辑器" / "选题顾问" / "复盘分析师" / onboarding 时为副助手）。

**消息结构**：

```typescript
type SourceTag =
  | "画像驱动" | "趋势驱动" | "数据驱动"
  | "历史复盘" | "用户偏好驱动";

type AiMessage = {
  role: "ai";
  text: string;                  // 已 strip 末行 source tag 与 SUGGESTIONS 行
  sources?: SourceTag[];         // 强制约束 · 至少 1 个
  suggestions?: string[];        // 点击后作为新一轮 user turn 提交
  pending?: boolean;             // 流式期间为 true
};
```

**Source tagging 渲染**：消息正文下方一行 chip，五元枚举对应不同色：

| Tag | 含义 | 色 token |
|---|---|---|
| 画像驱动 | 来自画像三态 | 绿（`--pillar-confirm`） |
| 趋势驱动 | 来自外部 trend 数据 | 蓝（`--info`） |
| 数据驱动 | 来自历史视频指标或评论 | 琥珀（`--warn`） |
| 历史复盘 | 来自既往 InsightsReport | 灰 |
| 用户偏好驱动 | 来自用户既往明确表态 | 紫 |

**Composer**：textarea + 图像按钮（占位 · 不实现）+ 发送按钮。底部 microcopy："AI 引用你的画像与最近发布。了解隐私"。

**chat-everything 模型**：任何模块中的可点击数据点调用 `onAsk(text)` 进入 chat dock。该函数：

1. 打开 chat dock（如关闭）
2. Append user turn
3. 走下方"前端硬路由 + orchestrator 兜底"链路生成响应

#### 6.7.1 前端硬路由（两条专属路径）

为保证 strategy / retro agent 内部状态机的自洽与演示稳定性，`useChatSend.ts` 对两条已经成熟的路径直接走专门 endpoint，绕过 orchestrator：

| 触发条件 | endpoint | 走的 agent 阶段 |
|---|---|---|
| `scene === 'ideate'` 且 store.snapshotId 存在 | `POST /api/strategy/refine` | Strategy agent REFINE（含 §5.7 feedback 分类） |
| `scene === 'retro'` 且 store.reportId 存在 | `SSE /api/retro/drill` | Retro agent DRILL；中途可 yield `profile_updated` 触发画像刷新 |

#### 6.7.2 Orchestrator 兜底（其余全部 scene）

不满足上述条件的全部 chat（home / onboard / profile / ideate-pre-snapshot / retro-pre-report）走 `SSE /api/orchestrator/chat`。

Orchestrator agent 的两阶段架构：

1. **ROUTE**：极轻 LLM 分类（flash 无 thinking · ≤200 token · 300–600ms），输出 `RouteDecision { intent, needs_slices, tone, expect_suggestions }`
2. **CHAT_STREAM**：按 needs_slices 子集装配 profile / strategy / retro 切片，加 scene_<scene> 角色 prompt，flash-thinking 流式输出
3. **SOURCE_GUARD**：流结束后校验末行 source tag；缺则 retry 1 次；仍缺注入 fallback `[数据驱动]`

完整设计见 `orchestrator_agent_demo_spec.md`。

**重要约束**：每一条 AI 消息必须至少有一个 source tag。这是产品的信任契约，不可省略。后端在 source guard 阶段做强校验，缺 tag 触发 retry，仍缺则 fallback 注入并在 `done` 事件中标记 `used_fallback=true`，便于离线分析触发率。

---

## 7. AI Agent 设计与集成

### 7.1 Agent 列表

| Agent | 触发场景 | 详细 spec | 实现状态 |
|---|---|---|---|
| Onboarding Agent | scene = onboard | `onboarding_agent_demo_spec.md` | ✅ M4 完成（八状态 FSM） |
| Strategy Agent | scene = ideate · 用户提交 idea / chat dock REFINE | `content_strategy_agent_demo_spec.md` | ✅ M5 完成（八状态 FSM + 流式思考 token） |
| Retro Agent | scene = retro · 用户进入或选定视频 / chat dock DRILL | `retro_insight_agent_demo_spec.md` | ✅ M6 完成（九状态 FSM + 写回画像） |
| Orchestrator Agent | chat dock 兜底（home / onboard / profile / ideate-pre-snapshot / retro-pre-report） | `orchestrator_agent_demo_spec.md` | ✅ M7 完成（router + 5 scene prompt + source guard） |

### 7.2 模型分配策略

DeepSeek v4 提供三档模型：

* **flash with thinking**：低延迟 + 中等推理
* **flash without thinking**：最低延迟 + 快速分类
* **pro with thinking**：最高质量 + 高延迟

按职责分配：

| 阶段 / 操作 | 推荐模型 | 理由 |
|---|---|---|
| Onboarding ANALYZE | pro with thinking | 一次性深度分析全部账号数据，质量优先 |
| Onboarding PRESENT / EXPLORE / SUMMARIZE | flash with thinking | 对话式生成，需要语感与推理但不要慢 |
| Onboarding VALIDATE（动作分类） | flash without thinking | 简单分类任务 |
| Strategy GENERATE_IDEAS / SCORE / STRATEGIZE | pro with thinking | 复杂联合推理，质量直接影响策略可信度 |
| Strategy PRESENT / REFINE | flash with thinking | 对话式 |
| Retro COMPARE / ATTRIBUTE | pro with thinking | 归因质量直接决定产品价值 |
| Retro EXTRACT_SIGNALS | flash with thinking | 评论语义聚类 |
| Retro SYNTHESIZE | pro with thinking | 三层结构组装，质量优先 |
| Retro PRESENT / DRILL / UPDATE_PROFILE | flash with thinking | 对话式 |
| Orchestrator chat dock | flash with thinking | 实时对话，平衡延迟与质量 |

每个 agent 的实现代码中应将模型选择参数化，便于调优。

### 7.3 LLM 调用约束

**JSON 输出**：所有结构化输出阶段（ANALYZE / SCORE / SYNTHESIZE 等）必须强约束 JSON。Prompt 中明确要求格式，后端用 pydantic 或同等校验，失败时 retry 1 次后回退到缓存兜底。

**流式输出**：对话式阶段（PRESENT / DRILL / Orchestrator）使用流式输出，前端逐字渲染，提升临场感。

**Token 预算**：每轮 user-facing LLM 调用控制在 8 秒内完成首 token 返回，30 秒内完成全部输出。超时前端展示骨架屏 + 友好提示。

**重试策略**：429 / 5xx 错误指数退避重试至多 2 次；JSON parse 失败 retry 1 次；持续失败回退到预先缓存的"保底响应"（demo 不崩溃为最高优先级）。

### 7.4 预跑缓存策略

为保证 demo 现场稳定性，以下阶段必须预跑并缓存：

* Onboarding ANALYZE：缓存为 `cache/onb_analyze.json`
* Strategy SCORE + STRATEGIZE：缓存为 `cache/strategy_score_strategize.json`
* Retro COMPARE + ATTRIBUTE + EXTRACT_SIGNALS + SYNTHESIZE：缓存为 `cache/retro_synthesis.json`

后端启动时根据环境变量 `USE_CACHED_ANALYSIS` 决定是否走缓存。Demo 默认 `true`，开发与调试时可设 `false` 走真实 LLM。

实时 LLM 调用保留：所有 PRESENT / REFINE / EXPLORE / DRILL / VALIDATE / Orchestrator chat 阶段。这些阶段构成"AI 在思考"的临场感。

---

## 8. 数据模型

### 8.1 Mock 数据清单

mock 数据围绕 persona 小A 的完整故事线，存放于后端 `mock_data/` 目录：

| 文件 | 内容 | 服务于 |
|---|---|---|
| `account_snapshot.json` | 账号身份信息 | Onboarding ANALYZE |
| `historical_videos.json` | 10 至 15 条历史视频（含 metrics、drop_off_curve、transcript） | Onboarding ANALYZE / Ideate |
| `comments.json` | 每条视频 5 至 10 条评论，含可触发 insight 的伏笔 | Onboarding / Retro |
| `audience_snapshot.json` | 粉丝画像 | Onboarding |
| `account_baseline.json` | 历史指标基线 | Retro |
| `external_trends.json` | 2 至 3 个候选话题的趋势数据 | Ideate |
| `new_video_for_retro.json` | 待复盘的新视频（含 metrics、drop_off、评论） | Retro |
| `onboarding_conversation_template.json` | onboarding 对话脚本（用于现场演示稳定） | Demo backup |

各文件 schema 详见三份 agent spec 中的 mock 数据章节。

### 8.2 运行时数据

所有运行时输出存于 `runtime_data/`（demo 部署时内存或本地 JSON 持久化均可）：

* `profile_v{n}.json`：onboarding 与 retro 后的画像版本
* `strategy_snapshot_{id}.json`：每条 idea 提交后的策略快照
* `insights_report_{id}.json`：每条视频的复盘报告
* `chat_history.json`：chat dock 完整对话记录（demo 单 persona，单文件足够）

### 8.3 Schema 引用

详细 schema 定义见三份 agent spec：

* Profile schema：`onboarding_agent_demo_spec.md` §4
* Strategy snapshot schema：`content_strategy_agent_demo_spec.md` §4
* InsightsReport schema：`retro_insight_agent_demo_spec.md` §4

---

## 9. 技术栈与部署

### 9.1 前端

* **框架**：React 18 + Vite（部署为静态资产）
* **路由**：React Router 或 URL state（5 个 scene 对应 `/empty` `/onboard` `/profile` `/ideate` `/retro` `/home`）
* **样式**：Tailwind CSS + design tokens（README 中列出的 tokens 全部移植到 `tailwind.config.ts` 的 theme.extend）
* **组件**：Radix Primitives + shadcn/ui（用于 Dialog、Tabs、ScrollArea、Tooltip）
* **图标**：Lucide React
* **状态管理**：Zustand（chat / scene / profile 状态）+ React Context（design tweaks）
* **流式**：fetch + ReadableStream 或 SSE 处理 LLM 流式响应

### 9.2 后端

* **运行时**：Node.js 20 或 Python 3.11（任选其一，建议 Python 因 LLM 生态更成熟）
* **框架**：FastAPI（Python）或 Express（Node）
* **核心模块**：

  * `agents/`：onboarding / strategy / retro / orchestrator 各一个文件
  * `prompts/`：所有 prompt 模板，按 agent 分组
  * `mock_data/`：mock JSON 文件，启动时加载到内存
  * `runtime_data/`：运行时输出（demo 单 persona，本地 JSON 即可）
  * `cache/`：预跑缓存
  * `api/`：HTTP 路由
* **LLM 客户端**：DeepSeek v4 SDK 或直接 HTTP（OpenAI-compatible API）
* **数据校验**：pydantic（Python）或 zod（Node）

### 9.3 部署架构

腾讯云挂载方式：

```
┌────────────────────────────────────────────────────┐
│  腾讯云 COS （静态托管）                            │
│  └─ 前端构建产物（dist/）                           │
└────────────────────────────────────────────────────┘
                       ↓ HTTPS
┌────────────────────────────────────────────────────┐
│  腾讯云 CloudBase 或 SCF （后端）                   │
│  ├─ FastAPI / Express server                       │
│  ├─ /api/onboarding/*                              │
│  ├─ /api/strategy/*                                │
│  ├─ /api/retro/*                                   │
│  └─ /api/orchestrator/*                            │
└────────────────────────────────────────────────────┘
                       ↓ HTTPS
┌────────────────────────────────────────────────────┐
│  DeepSeek v4 API                                    │
└────────────────────────────────────────────────────┘
```

### 9.4 环境变量与密钥管理

**关键约束**：

* 所有模型 API key 与敏感配置写入 `.env` 文件
* `.env` 文件 **Claude Code 不可读**（`.gitignore` + 沙箱权限隔离）
* `.env.example` 提供模板，列出所有必需变量名（不含值）
* Claude Code 在 sandbox 运行，不能访问真实密钥

`.env.example` 应包含：

```
# DeepSeek v4 API
DEEPSEEK_API_KEY=
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# 模型选择（三档）
MODEL_FLASH=deepseek-v4-flash
MODEL_FLASH_THINKING=deepseek-v4-flash-thinking
MODEL_PRO_THINKING=deepseek-v4-pro-thinking

# 应用配置
USE_CACHED_ANALYSIS=true
LOG_LEVEL=info
PORT=8000

# 腾讯云（仅生产）
TENCENT_SECRET_ID=
TENCENT_SECRET_KEY=
TENCENT_REGION=ap-guangzhou
```

**实施约定**：

1. 后端代码读取密钥**只通过** `os.getenv` / `process.env`，不允许任何 hard-coded 密钥
2. 部署到腾讯云时通过云平台的"环境变量配置"或"密钥管理"注入
3. Claude Code 在沙箱中开发时使用 mock 密钥 + `USE_CACHED_ANALYSIS=true` 走缓存
4. README 与本 PRD 不出现真实 key
5. 所有日志中过滤含 `KEY` `SECRET` `TOKEN` 关键词的内容

### 9.5 本地开发

提供 `docker-compose.yml` 一键启动前后端：

```
docker compose up
```

后端默认 8000 端口，前端默认 5173 端口（Vite dev）。前端通过 proxy 转发 `/api/*` 到后端。

---

## 10. 安全与隐私

### 10.1 数据所有权与隐私表态

Beacon 在产品层明确以下立场（写入应用 footer 与隐私页）：

**用户拥有自己的画像与对话数据**。任何时候用户可导出完整画像 JSON 与聊天历史。本期 demo 不实现导出 UI，但在后端预留导出 endpoint。

**数据最小化**。Beacon 不主动抓取用户其他平台账号信息，所有外部数据来源由用户主动授权或提供。本期 demo 全部使用 mock 数据，无真实数据采集。

**对话历史短期保留**。生产环境聊天历史默认保留 90 天后自动归档脱敏。Demo 单 persona 不涉及。

**画像数据不出境**。生产环境画像数据托管在腾讯云内地节点，不跨境传输。

**不向第三方分享个人化数据**。商业化路径（订阅、商单匹配）不依赖出售用户画像数据。

### 10.2 接口安全

* 所有后端 API 走 HTTPS
* 输入做长度与字符校验，防 prompt injection
* 速率限制：每 IP 每分钟最多 60 次 chat 请求
* CORS 仅允许前端域名

### 10.3 LLM 安全

* System prompt 中加入 prompt injection 防护语句
* 用户输入在拼接进 prompt 前做 escape
* LLM 输出过滤敏感信息（虽然 demo 风险低）

---

## 11. 非功能要求

### 11.1 性能

* 首屏加载 ≤ 2s（前端静态资产 + CDN）
* Onboarding PRESENT 首 token ≤ 3s
* 任意 chat dock 响应首 token ≤ 5s
* 整体 demo 流程（onboard → ideate → retro）≤ 8 分钟

### 11.2 可用性

* Demo 期间 SLA 99%（演示期前进行至少 5 次完整流程演练）
* 所有 LLM 调用配 retry + 缓存兜底，单点失败不导致 demo 崩溃
* 前端关键路径加载失败时展示友好错误页 + 重试按钮

### 11.3 可扩展性

* 平台无关：所有 schema 中的 `platform` 字段为枚举，新增平台无需改 schema
* Agent 可插拔：新增模块（例如未来的商单匹配）按相同 spec 范式扩展
* 模型可替换：LLM 客户端封装为接口，DeepSeek 可替换为其他 OpenAI-compatible 服务

---

## 12. 开发路线图（Claude Code 任务分解）

本节为 Claude Code 提供按里程碑的任务清单。建议按顺序推进，每个里程碑结束做一次端到端 smoke test。

### 12.0 实施进度概览（截至 2026-05-06）

| Milestone | 状态 | 阶段复盘 |
|---|---|---|
| M0 项目初始化 | ✅ | [phase-0-bootstrap.md](docs/phase-reports/phase-0-bootstrap.md) |
| M1 Mock 数据与 Schema | ✅ | （并入 M0/M3） |
| M2 设计 Tokens 与 Shell | ✅ | （tag `m2-pass`） |
| M3 5 个 Scene 静态实现 | ✅ | [phase-3-scenes.md](docs/phase-reports/phase-3-scenes.md) |
| M4 Onboarding Agent | ✅ | [phase-4-onboarding.md](docs/phase-reports/phase-4-onboarding.md) |
| M5 Strategy Agent | ✅ | [phase-5-strategy.md](docs/phase-reports/phase-5-strategy.md) |
| M6 Retro Agent | ✅ | [phase-6-retro.md](docs/phase-reports/phase-6-retro.md) |
| M7 Orchestrator + Source Tagging | ✅ | [phase-7-orchestrator.md](docs/phase-reports/phase-7-orchestrator.md) |
| M8 闭环演示与故事线打磨 | 🟡 进行中 | demo 主线已打通，故事线脚本待整理 |
| M9 腾讯云部署 | ✅ | [phase-9-deploy.md](docs/phase-reports/phase-9-deploy.md) |
| M10 风险演练与冷热备 | ⏳ 未做 | 缓存兜底已就绪；chaos 测试与一键切换脚本待补 |

### 12.1 Milestone 0：项目初始化

**任务**：

1. 创建项目目录结构（前端 + 后端 + mock_data + cache + docs）
2. 初始化前端（Vite + React + TS + Tailwind + Radix）
3. 初始化后端（FastAPI 或 Express + 基础目录结构）
4. 创建 `.env.example`，README 中说明本地开发流程
5. 创建 `docker-compose.yml` 实现一键启动

**验收**：本地能 `docker compose up`，前后端均可访问，前端能调 `/api/health` 返回 ok。

### 12.2 Milestone 1：Mock 数据与 Schema

**任务**：

1. 按三份 agent spec 中的 mock data schema 生成 `mock_data/` 全部 JSON 文件，围绕 persona 小A 构造内部一致的故事线（关键约束：埋伏笔评论必须与 retro 故事线对应）
2. 用 pydantic / zod 实现各 schema 类型定义
3. 后端启动时加载所有 mock 数据到内存

**验收**：所有 mock JSON 通过 schema 校验；`/api/mock/account` 等调试接口返回数据正确。

### 12.3 Milestone 2：设计 Tokens 与 Shell

**任务**：

1. 把 README 中的 design tokens 全部移植到 `tailwind.config.ts`
2. 实现 `App Shell`：3 列布局（220 / 1fr / 420）+ 导航栏 + 顶部条
3. 实现 chat dock 容器（暂无实际对话功能，只渲染框架）
4. 实现 onboarding gate 路由逻辑：`profileReady` 状态变量控制锁/解锁

**验收**：5 个 scene 路由可切换，chat dock 可折叠，gate 状态切换时导航锁/解锁正确。

### 12.4 Milestone 3：5 个 Scene 静态实现

**任务**：

按 §6 详细规范实现 5 个 scene 的 UI（Empty Home / Onboarding / Profile / Ideate / Retro / Home）。本里程碑只做静态渲染（用 mock 数据），不接 LLM。

**验收**：每个 scene 视觉与 README 设计 hi-fi 一致；所有可点击元素 hover 状态正确；chat-everything 入口已埋点（暂时弹"待实现"提示）。

### 12.5 Milestone 4：Onboarding Agent

**任务**：

按 `onboarding_agent_demo_spec.md` 实现：

1. 后端 onboarding agent（八状态状态机：含 FINALIZE / DONE）
2. 6 段 prompt 移植到 `prompts/onboarding/`
3. ANALYZE 阶段预跑脚本，生成 `cache/onb_analyze.json`
4. 前端 onboarding view 接入 agent，实现实时对话 + LIVE 信息栏更新
5. 完成后写入 `runtime_data/profile_v1.json`
6. `profileReady` 状态切换，解锁其他模块

**验收**：可走完完整 onboarding 流程，得到 profile_v1.json 三态俱全；ANALYZE 阶段走缓存时延迟 < 1s；现场重新跑 ANALYZE 也可在 30s 内完成。

### 12.6 Milestone 5：Strategy Agent

**任务**：

按 `content_strategy_agent_demo_spec.md` 实现：

1. 后端 strategy agent（八状态状态机）
2. 6 段 prompt 移植到 `prompts/strategy/`
3. SCORE + STRATEGIZE 预跑脚本，生成 `cache/strategy_score_strategize.json`
4. 前端 ideate view 接入 agent，实现 idea 提交 → 4 tab 内容渲染
5. 实现 chat dock 中的 REFINE 流程
6. 完成后写入 `runtime_data/strategy_snapshot_{id}.json`

**验收**：可提交 idea 并得到完整策略；4 个指标卡显示正确；REFINE 至少能处理 challenge / adjust / approve 三类反馈；strategy snapshot JSON schema 完整。

### 12.7 Milestone 6：Retro Agent

**任务**：

按 `retro_insight_agent_demo_spec.md` 实现：

1. 后端 retro agent（九状态状态机）
2. 8 段 prompt 移植到 `prompts/retro/`
3. COMPARE + ATTRIBUTE + EXTRACT_SIGNALS + SYNTHESIZE 预跑脚本，生成 `cache/retro_synthesis.json`
4. 前端 retro view 接入 agent，实现 Strategy vs Reality + Insight cards + 评论聚类
5. 实现 chat dock 中的 DRILL 流程
6. UPDATE_PROFILE 阶段实时执行，更新 `runtime_data/profile_v2.json`

**验收**：可从 ideate 直接跳到 retro；Strategy vs Reality 对比正确；至少 1 轮 DRILL 交互成功；profile_delta 正确写入；闭环可被验证。

### 12.8 Milestone 7：Orchestrator 与 Source Tagging

**任务**：

1. 实现 Orchestrator agent（chat dock 路由层）
2. 所有 chat 响应强约束 source tags 输出
3. 前端 source tag 渲染（chip 样式按 §6.7）
4. chat-everything 模型：所有 §6 中标注的可点击元素统一调用 `onAsk(text)`

**验收**：每条 AI 消息都带至少一个 source tag；点击任意数据卡 / insight / suggestion 都能进入 chat 并得到正确响应。

### 12.9 Milestone 8：闭环演示与故事线打磨

**任务**：

1. 完整跑通 onboarding → ideate → retro → home 的端到端流程至少 5 次
2. 优化所有 LLM 输出的语感与节奏（必要时调 prompt）
3. 准备保底脚本：每个 LLM 调用点的 hardcoded 响应，应急时切换
4. 准备 demo 演示脚本（评委交互引导）

**验收**：评委可独立按演示脚本走完 5 至 8 分钟完整流程，全程不卡壳。

### 12.10 Milestone 9：腾讯云部署

**任务**：

1. 前端构建产物上传 COS + CDN 配置
2. 后端打包为容器或 SCF 函数，部署
3. 配置 `.env` 通过腾讯云密钥管理注入
4. HTTPS + 域名绑定
5. 配置基础监控与日志告警

**验收**：评委可通过公网 URL 访问 demo；首屏加载 < 2s；完整 demo 流程在线上无报错。

### 12.11 Milestone 10：风险演练与冷热备

**任务**：

1. LLM 调用全链路加 retry + 超时 + 缓存兜底
2. 关键路径（onboarding 对话、ideate 提交、retro 进入）做 chaos 测试
3. 准备演示当天的"应急切换脚本"：一键从实时 LLM 切到全缓存兜底

**验收**：模拟 LLM 服务 50% 失败率时 demo 仍可走通；切换脚本响应时间 < 5s。

---

## 13. Demo 演示规范

### 13.1 演示故事线（5 至 8 分钟）

| 时间 | 场景 | 内容 |
|---|---|---|
| 0:00 至 0:30 | 介绍 | 介绍小A、痛点、Beacon 定位 |
| 0:30 至 1:00 | Empty Home | 展示新用户首屏，强调 profile/ideate/retro 三模块上锁 + 强 funnel |
| 1:00 至 3:00 | Onboarding | 走完 5 至 8 轮对话，展示 LIVE 信息栏实时更新；强调"AI 先做功课"；点击"生成画像 →"触发 FINALIZE 落盘 |
| 3:00 至 3:30 | Profile | 三态画像呈现，强调"待探索项"作为一等公民 |
| 3:30 至 5:00 | Ideate | 提交 idea "考研期间一日三餐怎么吃"，展示 4 维评估 + 节奏设计 + execution.key_focus 锚点；演示 1 轮 REFINE（chat dock → strategy/refine 路径） |
| 5:00 至 5:30 | "假设视频已发布" | 主线跳转到 retro vid_019；vid_016 / vid_020 备用切换供评委追问 |
| 5:30 至 7:00 | Retro | Strategy vs Reality 对比（参照 baseline_pillar）+ 3 张 insight（confidence 三档枚举）+ 1 轮 DRILL（chat dock → retro/drill 路径）；点"写回画像 →"触发 UPDATE_PROFILE，前端实时切到 profile_v{n+1} |
| 7:00 至 7:30 | 回到 Home | 展示画像更新可视化 + "画像更新频次 +1" |
| 7:30 至 8:00 | 总结 | 强调闭环价值 + 评分细则映射 |

### 13.2 关键演示话术

**强调"AI 先做功课"**：onboarding 第一句 AI 消息出现时，主持人话术："注意，这是 AI 看完她 15 条视频之后的第一次开口，不是空白问卷。"

**强调"三态画像"**：Profile view 切换时，话术："关键设计：我们把'还在思考的方向'作为一等公民，这是 AI 陪伴战略探索的能力，区别于固化标签的传统画像。"

**强调"双轴决策 + source tagging"**：ideate 评估卡片出现时，话术："每条建议下面都标注了来源——画像驱动 / 趋势驱动 / 数据驱动 / 历史复盘 / 用户偏好驱动。我们把信任契约做进了产品。"

**强调"闭环"**：retro 的 UPDATE_PROFILE 触发时，话术："这一刻，AI 把这次发布学到的东西回写到画像里。下一次选题，它会站在更高的起点。这就是为什么它'越用越懂你'。"

### 13.3 应急方案

* 实时 LLM 失败 → 切换全缓存兜底（保留 PRESENT 等少数实时阶段，其余从 cache 读取并模拟流式输出）
* 网络中断 → 本地备份 demo 视频（720p）作为最终兜底
* 评委追问超出预设范围 → 引导回核心闭环故事线，超纲问题答以"这是路线图中的内容"

### 13.4 评委交互入口

为让评委亲自体验而非仅观看，ProfileView 顶部明显位置放置"重置 Demo"按钮：

* 调 `POST /api/profile/reset` 把 runtime_data 重置到 profile_v3（demo 初始固化态），同时把前端 `profileReady=false`，回到 Empty Home + 清空 chat 日志
* 点击会先弹 `confirm`："重置到 Demo 初始态（v3）？所有测试 session 数据将删除。"
* v3 是预生成的稳定演示画像，每次评委体验都从同一基线出发，避免上一位评委的修改污染下一位

---

## 14. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|---|---|---|---|
| LLM 输出方差大，演示不稳定 | 高 | 高 | 关键阶段预跑缓存；保留实时阶段 + 保底脚本 |
| DeepSeek API 限流 | 中 | 高 | 速率限制 + 缓存兜底 + 离线 mock 模式 |
| 腾讯云部署延迟 | 中 | 中 | 提前 1 周完成部署 + 域名 + HTTPS 配置 |
| 评委追问超纲 | 中 | 中 | 引导回核心故事线 + 路线图答案 |
| 前端设计还原度不足 | 低 | 中 | 严格按 design tokens 复刻 + 早期对齐 |
| 端到端流程时长超时 | 中 | 中 | 演练 5 次以上 + 不必要交互可跳过 |

---

## 15. 开放项与未来路线图

本期 demo 不实现，但在 PRD 中标注实施路径，供评委后续提问时回答，并作为产品长期规划锚点。

### 15.1 商单匹配（中期最重要的变现路径）

**思路**：Beacon 沉淀的画像（确定 pillar、个性化资产、目标受众分群）+ 历史 strategy snapshot + 历次 retro insight，构成创作者侧的丰富数据资产。结合品牌方的需求画像（行业、目标人群、内容调性），可做高质量自动匹配。

**路径**：

* 第 1 阶段（demo 后 3 个月）：手动 + 半自动撮合，验证供需
* 第 2 阶段（6 至 9 个月）：商单匹配 agent 上线，自动推荐适合的商单 + 内容融入策略
* 第 3 阶段（12 个月以上）：撮合后效果数据反哺，形成正循环

### 15.2 多平台同步

**思路**：Beacon 平台无关，画像 schema 中的 `platform` 字段已为枚举。多平台时一个 KOC 拥有多个账号视图，画像在"个人特质 / 内容主轴"层面合一，在"平台风格"层面分流。

**路径**：

* 第 1 阶段：单平台 MVP 验证
* 第 2 阶段：第二平台接入，画像引擎升级支持 multi-account 视图
* 第 3 阶段：跨平台推流策略 agent

### 15.3 Proactive AI

**思路**：发布后 24 小时数据稳定时自动触发 retro；周维度自动生成 batch retro 报告；监测到画像异常变化时主动提示。

**路径**：

* 第 1 阶段：MVP 仅支持手动触发
* 第 2 阶段：定时任务 + 推送通道（站内 + 邮件）
* 第 3 阶段：基于用户行为的动态触发

### 15.4 数据接入

**思路**：本期 mock 数据，未来需要对接真实平台。优先走平台官方 OpenAPI（抖音 OpenAPI、小红书品牌合作平台 API），无授权时降级到用户手动导入或第三方数据服务。

**路径**：

* 第 1 阶段：MVP 提供 CSV 导入
* 第 2 阶段：抖音 OpenAPI 对接（需企业资质）
* 第 3 阶段：小红书 + B站

### 15.5 商业模式

**短期（0 至 6 个月）**：免费 + 付费 Pro 订阅。Pro 解锁高级 retro 维度、画像版本历史、批量复盘等。

**中期（6 至 18 个月）**：商单匹配抽佣（撮合成功后按比例）+ B 端席位订阅（MCN / 校园运营团队）。

**长期（18 个月以上）**：成为创作者成长基础设施。平台合作（数据洞察服务）+ SaaS 工具链（其他创作者工具的 API 接入）。

---

## 16. 附录

### 16.1 术语表

| 术语 | 含义 |
|---|---|
| KOC | Key Opinion Consumer，关键意见消费者，区别于头部 KOL 的中小型创作者 |
| 三态画像 | 画像中 confirmed / personalized / to_explore 三种状态 |
| Source tagging | 每条 AI 建议必须标注来源，五元枚举：画像驱动 / 趋势驱动 / 数据驱动 / 历史复盘 / 用户偏好驱动 |
| Chat-everything | 任意结构化 UI 元素都可点击进入对话的交互模型 |
| Strategy snapshot | 发布前的策略快照，retro 阶段做"假设 vs 实际"对比的契约 |
| Drop-off curve | 完播率离散曲线，按时间桶呈现观众流失 |
| Onboarding gate | 新用户必须完成 onboarding 才解锁其他模块的强约束 |
| Pillar | 画像中的内容主轴（如食堂探店、考研日常） |

### 16.2 引用文档

* `onboarding_agent_demo_spec.md`：Onboarding agent 详细技术规范
* `content_strategy_agent_demo_spec.md`：Strategy agent 详细技术规范
* `retro_insight_agent_demo_spec.md`：Retro agent 详细技术规范
* `orchestrator_agent_demo_spec.md`：Orchestrator agent 详细技术规范（chat dock 兜底）
* `frontend_design/README.md`（前端 hi-fi 设计文档）：UI 视觉、交互、tokens 规范
* `docs/phase-reports/phase-{0,3,4,5,6,7,9}-*.md`：各 milestone 阶段复盘

### 16.3 设计 Tokens 速查

完整 tokens 见 README，关键值：

* 主背景 `--bg-0: #faf9f6`
* 主色 `--accent: #5d7a1a`（深橄榄绿）
* 三态色：confirmed `#3d8a3a`（绿）/ personalized `#b87a1a`（琥珀）/ to_explore `#7a4ec4`（紫）
* 主字体：Inter + PingFang SC
* 圆角：`--r-xl: 20px`（卡片）/ `--r-pill: 999px`（chip）

---

## 17. 验收 Checklist

提交前的最终自检清单：

**功能完整性**

- [x] 6 个视图共 5 个 scene 全部可访问，UI 与 hi-fi 设计一致
- [x] Onboarding gate 流正确（新用户被锁，完成后解锁；SceneRouter useEffect 兜底）
- [x] Onboarding 完整跑通，得到 profile_v1.json 三态俱全（八状态 FSM 含 FINALIZE / DONE）
- [x] Ideate 完整跑通，得到 strategy_snapshot_*.json（含 execution.key_focus）
- [x] Retro 完整跑通，得到 insights_report_*.json + profile_v{n+1}.json（写回画像可视化 2–3 秒完成）
- [x] Chat dock 任意场景可用，每条 AI 消息有 source tag（五元枚举 · source guard retry + fallback）

**端到端**

- [x] 完整 demo 流程 5 至 8 分钟内可走完
- [ ] 至少 5 次完整流程演练无报错（M8 进行中）
- [x] LLM 失败兜底机制可工作（缓存 + retry + source fallback）
- [ ] 评委可独立按引导走通完整流程（M8 演示脚本待整理）

**部署**（M9）

- [x] 前端 HTTPS 公网可访问，首屏 ≤ 2s
- [x] 后端 API 公网可访问，关键 endpoint 响应正常
- [x] `.env` 通过腾讯云配置注入，代码中无 hardcoded key
- [x] Claude Code 沙箱中无法访问真实密钥

**评分映射**

- [x] 每个评分维度（5 必要 + 2 加分）在产品中有显式承接点（PRD §3）
- [ ] Demo 话术中明确提及关键创新（M8 演示脚本待整理）

**文档**

- [x] 本 PRD 与四份 agent spec 同步交付（含 orchestrator spec）
- [x] README 更新部署与本地开发指南
- [ ] 评委演示脚本独立成文（M8 待补）

---

文档完。本 PRD 作为 Claude Code 实施的输入，建议下一步从 §12 开发路线图的 Milestone 0 开始拆解任务并执行。
