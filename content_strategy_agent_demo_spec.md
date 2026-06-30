# Content Strategy Agent 设计规范

## 1. 这个 Agent 做什么

### 1.1 调用时机

三种进入模式：

**Idea-driven**（用户已有想法）：用户主动提出"我下期想拍 X，帮我看看怎么准备"。

**Discovery-driven**（用户没思路）：用户表达"我不知道下期拍什么，给我点建议"。

**System-triggered**（系统主动推荐）：当 profile 中存在高优先级 to_explore 项，agent 主动提议"我们可以做一期 X 来验证 Y 这个假设"。

### 1.2 核心职责

把"用户的一个 idea 或一个空白"转化为一份带证据的、可执行的、可被后续 retro 模块直接消费的内容策略。具体功能包括：

* 候选 idea 生成（discovery 模式下）
* 热度匹配：评估 idea 在当前平台的趋势位置
* 画像贴合度评估：idea 与 confirmed pillar、personalized 资产、to_explore 项的关系
* 差异化建议：基于用户独有资产的角度选择
* 执行要点输出：hook、pacing、CTA、tags
* 可验证指标预测：把策略落到具体可观测的指标上
* 对话式精修：用户质疑、调整、否决的实时响应

### 1.3 设计原则

**双轴决策**。每条建议都基于"画像驱动 + 趋势驱动"双轴交叉判断，且必须明示来源，不给黑箱建议。

**差异化优先于热度**。画像与趋势冲突时，优先保护用户的人格独特性。爆款不是产品的终极目标，差异化资产积累才是。

**可验证策略**。所有"预测"必须落到具体可观测的指标（完播率区间、关注转化率、评论关键词），方便 retro 阶段做"假设 vs 实际"归因。

**承接 to_explore**。生成策略时主动检查 profile 中的待探索项，让一条内容同时承担"试图涨粉"和"验证假设"两个目标。

## 2. Workflow

```
[RECEIVE_IDEA]
  ├─ idea_provided   → [ANALYZE_IDEA]
  └─ no_idea         → [GENERATE_IDEAS] → 用户选定 → [ANALYZE_IDEA]
[ANALYZE_IDEA]               (在线 LLM 调用)
  ↓ 检索 profile slice 与 matched trends
[SCORE]                      (在线 LLM 调用)
  ↓ 输出 heat_analysis 与 profile_fit
[STRATEGIZE]                 (在线 LLM 调用)
  ↓ 输出 differentiation 与 execution（含 key_focus 锚点）
[PRESENT]                    (在线 LLM 调用)
  ↓ 等待用户响应
[REFINE]                     (在线 LLM 调用)
  ↓ feedback 类型分支：challenge / adjust / approve
       ├─ approve         → [FINALIZE]
       ├─ challenge       → 回 PRESENT（解释推理链）
       └─ adjust          → 回 STRATEGIZE 或 SCORE 重跑
[FINALIZE]                   (写入 strategy snapshot，终态)
```

实际实现见 `backend/agents/strategy/state_machine.py`。Demo 默认走 idea_driven 路径；system_triggered 模式（基于 to_explore 主动提议）被合并到 RECEIVE_IDEA，不单独成态。

### 2.1 各状态职责

**RECEIVE_IDEA**：接收用户提交的 idea 或 discovery 模式的空请求。Idea_driven 直接进入 ANALYZE_IDEA；discovery_driven 进入 GENERATE_IDEAS；system_triggered 携带 profile to_explore 上下文（demo 中以预设 prompt 注入）。

**GENERATE_IDEAS**：discovery 模式专属。基于 profile（特别是 to_explore 项）与当前 trends，生成 2 至 3 个候选 idea，每个 idea 显式标注它能验证的假设、贴合的 pillar、踩到的趋势。

**ANALYZE_IDEA**：对 idea 做语义分析（核心命题、最可能贴合的 pillar、可验证的 to_explore 假设、相关 trend 主题）。不评分；评分由 SCORE 完成。

**SCORE**：计算两个核心维度：

* heat_analysis：该 idea 在当前平台的热度（trend_score、direction、supply_demand_ratio）
* profile_fit：该 idea 与画像的贴合度（pillar_alignment 用 high/medium/low 三档枚举，配合 evidence；persona_leverage、to_explore_validation、综合 fit_score）

**STRATEGIZE**：基于 SCORE 结果，生成差异化点（用户独有的可调用资产）与执行要点（hook、pacing、CTA、tags、key_focus 锚点）。`key_focus` 是一句中文描述，明示 retro 阶段最该重点观察的指标或现象，作为闭环验证的锚点。

**PRESENT**：把结构化策略翻译成自然语言，每条建议显式标注来源（画像驱动 / 趋势驱动 / 数据驱动 / 历史复盘 / 用户偏好驱动）。

**REFINE**：处理用户三类反馈，辅助 prompt（`06a_classify_feedback.txt`）先把用户原话分类：

* challenge：质疑某条建议的依据，agent 给出基于 profile / trends 的解释（留在 PRESENT/REFINE 循环）
* adjust：要求修改某个字段（"hook 改成 X"），agent 更新 strategy_draft，按改动范围回退到 STRATEGIZE 或 SCORE 重跑
* approve：用户认可，进入 FINALIZE

**FINALIZE**：终态。将 strategy snapshot 写入 `runtime_data/strategy_snapshot_{id}.json`。该 snapshot 是 retro 模块"假设 vs 实际"归因的契约输入。

## 3. Memory

### 3.1 Layer 1：会话工作记忆（in-context）

每次 LLM 调用时按当前阶段裁剪：

* current_state 与 current_idea
* profile_slice：与 idea 相关的画像子集（不塞完整 profile）
* matched_trends：与 idea 相关的 trend 项（不塞全部 trends）
* strategy_draft：当前策略草稿
* recent_turns：最近 3 至 4 轮对话

### 3.2 Layer 2：会话持久化记忆

* full_profile：完整画像快照（消费自 onboarding 输出）
* full_trends：本次 session 拉取的全部趋势数据
* strategy_draft：完整草稿
* refinement_history：所有改动的轨迹，REFINE 阶段引用以避免重复修改

### 3.3 Layer 3：跨模块共享

* strategy_snapshots：所有 commit 的策略快照，按 user_id 与 video_id 索引。该 store 是 strategy agent 与 retro agent 之间的契约接口。

## 4. Strategy Snapshot Schema（输出目标）

实际 schema 见 `backend/schemas/strategy.py`（pydantic v2，`extra="forbid"`）。

```json
{
  "strategy_id": "str_001",
  "user_id": "user_a_001",
  "profile_version": 1,
  "generated_at": "2026-04-27T11:00:00Z",
  "input": {
    "mode": "idea_driven",
    "user_idea": "考研期间一日三餐怎么吃才能不困",
    "iterations": 2
  },
  "idea": {
    "topic": "考研期间一日三餐怎么吃才能不困",
    "predicted_pillar": "考研日常 + 食堂探店融合",
    "rationale": "..."
  },
  "heat_analysis": {
    "trend_score": 0.82,
    "trend_direction": "rising",
    "supply_demand_ratio": 0.7,
    "matched_trends": ["考研一日三餐"],
    "comment": "处于上升期，供给少于需求，存在推流红利"
  },
  "profile_fit": {
    "pillar_alignment": [
      {"pillar": "食堂探店", "alignment": "high",   "evidence": "..."},
      {"pillar": "考研日常", "alignment": "high",   "evidence": "..."}
    ],
    "persona_leverage": [
      {"trait": "活力 + 真实感",                "how_to_use": "..."},
      {"life_context": "在读大三、考研中",       "how_to_use": "..."}
    ],
    "to_explore_validation": [
      {"hypothesis_id": "h001", "what_this_tests": "考研内容能否与既有食堂、校园生活素材自然融合"}
    ],
    "fit_score": 0.78
  },
  "differentiation": [
    {"point": "利用'本人正在考研'的真实身份",     "source": "画像驱动"},
    {"point": "复用既有食堂场景资源，节省制作成本", "source": "历史复盘"},
    {"point": "结合学习状态做反差，区别于纯食谱博主", "source": "趋势驱动"}
  ],
  "execution": {
    "hook":   { "design": "前 3 秒展示困到趴桌的画面 + 字幕'考研第 67 天'", "rationale": "对标当前同主题 top 视频开场" },
    "pacing": "前 1/3 做'问题感'铺垫，中段呈现 3 个解决方案，结尾收口到考研日常",
    "cta":    "评论区分享你考研中最困的时段",
    "tags":   ["考研日常", "食堂探店", "考研党"],
    "key_focus": "新增粉丝中考研兴趣标签占比 —— 这是验证'考研内容融合'假设的核心信号"
  }
}
```

字段说明：

* `pillar_alignment.alignment` 是三档枚举 `"high" | "medium" | "low"`（不是 0–1 浮点），配合 `evidence` 一句话理由
* `differentiation.source` 必须落在五元枚举内：`画像驱动 | 趋势驱动 | 数据驱动 | 历史复盘 | 用户偏好驱动`
* `execution.key_focus` 是一句中文锚点描述。它取代了早期方案里的 `predicted_metrics` 区间预测，作为 retro 阶段"重点观察哪个现象 / 指标"的契约输入。Retro agent 据此挑选 `is_key_indicator=true` 的 DataCard，并在 PRESENT 阶段用更长的篇幅讨论
* schema 之外的字段一律拒绝（`extra="forbid"`），任何 LLM 输出违规会被 retry 1 次后回退到缓存兜底

## 5. Prompts

### 5.1 System Prompt（贯穿全部 LLM 调用）

```
你是一个为早期视频类 KOC 提供内容策略的 AI 顾问。
你的目标是把用户的一个想法或一个空白，转化为一份带证据的、
可执行的、可被后续复盘验证的内容策略。

你必须遵守以下原则：

1. 双轴决策。每条建议都明示其来源（五元枚举之一）：
   "画像驱动" / "趋势驱动" / "数据驱动" / "历史复盘" / "用户偏好驱动"。
   不要给黑箱建议。

2. 差异化优先于热度。当画像与趋势冲突时，优先保护用户的人格独特性，
   不为流量牺牲账号定位。

3. 可验证。每条策略必须明示一个 key_focus 锚点（一句中文），
   告诉 retro 阶段最该重点观察的指标或现象，作为闭环验证的契约。

4. 承接 to_explore。生成策略时主动检查 profile 中的待探索项，
   尽量让一条内容同时承担"试图涨粉"和"验证假设"两个目标。

5. 简洁、专业、不油腻。中文回复。
```

### 5.2 GENERATE_IDEAS Prompt（discovery 模式）

```
任务：基于用户画像和当前趋势，生成 2 至 3 个候选 idea。

[USER_PROFILE]
{{profile_json}}

[CURRENT_TRENDS]
{{trends_json}}

请输出 JSON：

{
  "candidate_ideas": [
    {
      "idea_id": "i001",
      "topic": "...",
      "primary_pillar": "...",
      "rationale": "贴合 X 主轴 + 踩到 Y 趋势 + 验证 Z 假设",
      "trend_link": "...",
      "to_explore_link": "...",
      "differentiation_seed": "..."
    }
  ]
}

要求：
* 每个 idea 必须显式连接到 profile 中至少一个 confirmed pillar
  或 to_explore 项
* 至少一个 idea 服务于 to_explore 验证（不只是踩热点）
* 候选 idea 之间应有差异度（不要全部聚焦同一主轴）
* rationale 用一句话讲清"为什么是这个"
```

### 5.3a ANALYZE_IDEA Prompt（在线，语义分析）

```
任务：对用户提交的 idea 做初步语义分析。
不评分；评分由 SCORE 阶段完成。

[USER_IDEA]
{{idea_text}}

[USER_PROFILE_SLICE]
{{profile_slice_json}}

[CANDIDATE_TRENDS]
{{trends_json}}

请输出一段简短中文分析（≤ 200 字），覆盖：
1. 这条 idea 的核心命题是什么；
2. 它最可能贴合哪个 confirmed pillar；
3. 它能验证哪些 to_explore 假设；
4. 它与哪些 trend 主题语义相关。
```

完整模板见 `backend/prompts/strategy/01_analyze_idea.txt`。

### 5.3b SCORE Prompt（在线，热度 + 贴合评估）

```
任务：对用户提出的 idea 做热度匹配 + 画像贴合度评估。

[USER_IDEA]
{{idea_text}}

[USER_PROFILE_SLICE]
{{profile_slice_json}}

[MATCHED_TRENDS]
{{trends_json}}

请严格输出 JSON：

{
  "heat_analysis": {
    "trend_score": 0.0 至 1.0,
    "trend_direction": "rising | stable | falling",
    "supply_demand_ratio": 数值,
    "matched_trends": ["..."],
    "comment": "一句话评论"
  },
  "profile_fit": {
    "pillar_alignment": [
      {"pillar": "...", "alignment": "high | medium | low", "evidence": "..."}
    ],
    "persona_leverage": [
      {"trait": "...", "how_to_use": "..."}
    ],
    "to_explore_validation": [
      {"hypothesis_id": "...", "what_this_tests": "..."}
    ],
    "fit_score": 0.0 至 1.0
  },
  "idea_summary": {
    "topic": "...",
    "predicted_pillar": "...",
    "rationale": "..."
  }
}

判定规则：
* fit_score 综合考虑 pillar、persona、to_explore 三方面
* 至少识别一个 persona_leverage 点
* 如该 idea 能验证某个 to_explore 项，必须显式列出（hypothesis_id 必填）
* fit 与 heat 矛盾时，分别如实给出，不要为了一致性扭曲
* alignment 三档参考：high = 与该 pillar 强相关；medium = 部分相关；low = 弱相关或不相关
```

完整模板见 `backend/prompts/strategy/03_score.txt`。

### 5.4 STRATEGIZE Prompt

```
任务：基于热度与画像分析，生成差异化点和执行要点。

[HEAT_ANALYSIS]
{{heat_json}}

[PROFILE_FIT]
{{fit_json}}

[TOP_VIDEOS_FOR_THIS_TREND]
{{top_videos_json}}

请严格输出 JSON：

{
  "differentiation": [
    {"point": "...", "source": "画像驱动 | 趋势驱动 | 数据驱动 | 历史复盘 | 用户偏好驱动"}
  ],
  "execution": {
    "hook":   {"design": "...", "rationale": "..."},
    "pacing": "...",
    "cta":    "...",
    "tags":   ["..."],
    "key_focus": "..."
  }
}

要求：
* differentiation 至少包含 2 条画像驱动的点（用户独有资产）
* execution.hook 需对标 top_videos 中的开场设计
* key_focus 是一句中文锚点描述：明示 retro 阶段最该重点观察的指标或现象
  （例如"新增粉丝中考研兴趣标签占比"、"中段 12 秒后的留存曲线"）。
  这个字段是 strategy → retro 的契约，retro agent 据此挑选 is_key_indicator
  的 DataCard 并放大讨论
```

### 5.5 PRESENT_STRATEGY Prompt

```
任务：把以下结构化策略整理成对用户友好的自然语言。

[STRATEGY_DRAFT]
{{strategy_draft_json}}

要求：
* 分四段：
  第一段：idea 评估（一句话给出 fit + heat 综合判断）
  第二段：差异化机会（你的独特角度，每点标注来源）
  第三段：执行要点（hook、pacing、CTA、tags）
  第四段：可观察的成功指标（重点看哪个数据，预期范围）
* 总长度 250 至 350 字
* 每条建议都要可追溯到画像或趋势的具体依据
* 结尾留对话钩子："这版策略你觉得哪里需要调整？"
```

### 5.6 REFINE Prompt

```
任务：根据用户对策略的反馈，输出对 strategy_draft 的修改回复。

[CURRENT_STRATEGY_DRAFT]
{{strategy_draft_json}}

[USER_FEEDBACK]
{{user_text}}

[FEEDBACK_TYPE]
{{feedback_type}}  ← 已由 §5.7 分类 prompt 预先决定（challenge | adjust | approve）

要求：
* feedback_type = challenge：基于 profile / trends / history 给出推理链解释，
  不修改 strategy_draft 字段
* feedback_type = adjust：更新对应字段；按改动范围决定回退重跑：
  - hook / pacing / cta / tags 调整 → 回 STRATEGIZE 重跑 execution
  - heat / fit 重评 → 回 SCORE 重跑评分
* feedback_type = approve：进入 FINALIZE

回复正文末尾必须有 source tag 行（[画像驱动] / [趋势驱动] / [数据驱动] / [历史复盘] /
[用户偏好驱动]），单条或空格分隔多条。
```

### 5.7 Feedback 分类 Prompt（轻量前置分类）

`backend/prompts/strategy/06a_classify_feedback.txt`：

```
任务：把用户对策略草稿的反馈分类为以下三类之一。

[USER_TEXT]
{{user_text}}

输出严格 JSON：

{ "feedback_type": "challenge | adjust | approve" }

判定指引：
* 用户在质疑某条建议的依据（"为什么 hook 要这样"、"这个评分对吗"）→ challenge
* 用户在提具体修改要求（"hook 改成 X"、"pacing 慢一点"、"换个 cta"）→ adjust
* 用户表达认可、想保存、想继续下一步（"行就这样"、"OK"、"提交吧"）→ approve
```

实现拆为两段是因为：分类是一次极轻 LLM 调用（200ms 内、flash 无 thinking、`json_mode`），失败可 retry；REFINE 主回复用 flash-thinking 流式，避免在主流式里夹结构化分类。

## 6. Demo 中实现什么 / Mock 什么

### 6.1 Demo 实现的部分

* 三种进入模式中至少演示 idea-driven，可选演示 discovery-driven
* 完整的 ANALYZE → SCORE → STRATEGIZE → PRESENT → REFINE → COMMIT 流转
* 至少 1 轮 REFINE 交互（展示用户追问 + agent 调整）
* 最终 strategy snapshot JSON 的产出
* 与 onboarding 模块的衔接（消费 profile_v1.json）

### 6.2 Demo Mock 的部分

| Mock 文件 | 内容 | 来源 |
|---|---|---|
| `profile_v1.json` | 完整 KOC 画像 | onboarding agent 输出 |
| `external_trends.json` | 2 至 3 个候选话题的趋势数据（含 trend_score、direction、supply_demand_ratio、top_videos） | 预制 |
| `historical_videos.json` | 历史视频（用于"复用资源"建议） | 与 onboarding 共享 |

**预跑固化建议**：

* SCORE 与 STRATEGIZE 两个结构化输出阶段可预跑并缓存，演示时直接加载，避免现场 LLM 输出方差
* PRESENT_STRATEGY 与 REFINE 实时生成，体现对话感
* 至少准备 2 个不同的用户 idea：一个高 fit + 高 heat（顺风局），一个画像与趋势冲突（用来展示 agent 的取舍逻辑）

### 6.3 Demo 不涉及的部分

* 真实 trend 数据接入（爬虫 / 平台 API）
* 多用户并发的 strategy 生成
* strategy 与发布工具的对接
* 自动化的 strategy A/B 测试

### 6.4 演示故事线建议

承接 onboarding demo 中"小A 还在思考是否把考研作为长期主轴"这一 to_explore 项：

第一步，用户带着 idea "考研期间一日三餐怎么吃" 进入 strategy agent。

第二步，agent 拉出 profile 与 matched trend "考研一日三餐"（rising，supply 低于 demand）。

第三步，SCORE 阶段同时点亮"高 fit + 高 heat"组合，并显式连接到 to_explore_validation：这条内容能用来验证"考研内容能否与既有素材自然融合"这个假设。

第四步，STRATEGIZE 强调差异化点，"你正在考研"是其他博主没有的真实身份资产。

第五步，execution.key_focus 锚点设为"新增粉丝中考研兴趣标签占比"，为后续 retro 留下可验证锚点。

第六步，PRESENT 阶段用四段式自然语言呈现完整策略。

第七步，用户追问"hook 太苦情了，能不能轻松一点"。

第八步，REFINE 输出新 hook 设计并解释取舍。

第九步，COMMIT 写入 strategy snapshot，作为 retro 模块的输入。

这条故事线把 onboarding 的 to_explore 项接续到 strategy 的 to_explore_validation，再传递给后续 retro 阶段做闭环验证，是 demo 最有传播力的因果链。
