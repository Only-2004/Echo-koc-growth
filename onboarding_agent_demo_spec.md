# Onboarding Agent 设计规范

## 1. 这个 Agent 做什么

Onboarding agent 是 KOC 画像引擎的入口模块。它的目标是：在用户初次进入产品时，通过 5 至 8 轮高密度对话，从已有账号数据出发，产出一份带证据的、可演化的三态 KOC 画像（profile）。

这份画像将作为后续 ideation 与 retro 模块的输入，因此其结构、来源、置信度都必须可被下游模块明确消费。

### 1.1 核心设计原则

**AI 先做功课**。在第一轮对话之前，agent 已经分析过用户全部历史数据并形成假设草稿。绝不使用空白问卷式提问。

**三态意识**。每条画像信息明确归入 confirmed（已被数据反复验证）、personalized（个性化但尚未量化验证）、to_explore（用户尚未明确表态或存在分歧）三类之一。判定不清时优先放入 to_explore。

**引导而非引诱**。用户犹豫时，agent 的职责是帮他识别顾虑、把模糊问题转化为可验证假设，而不是替他做决定，也不是说服他选某一边。

**证据驱动**。每条 claim 必须挂靠到具体的视频、评论或用户回复，可被下游引用与解释。

## 2. Workflow

Agent 由八个状态构成的有限状态机驱动。其中 ANALYZE 是离线 LLM 推理（无用户介入），中段四个对话阶段为在线交互，FINALIZE 与 DONE 是落盘与终态。实际代码见 `backend/agents/onboarding/state_machine.py`。

```
[INIT]
  ↓ 加载账号数据
[ANALYZE]            (离线 LLM 调用，一次)
  ↓ 产出 candidate_claims 与 draft_profile
[PRESENT]            (在线 LLM 调用，一次)
  ↓ 等待用户响应
[VALIDATE]           (在线 LLM 调用，处理用户回复并更新 draft_profile)
  ↓ 是否还有高优先级 to_explore 项未触碰
       ├─ 是 → [EXPLORE] ──→ 回到 VALIDATE
       └─ 否 → [SUMMARIZE]
[SUMMARIZE]          (在线 LLM 调用，总览呈现)
  ↓ 用户点"生成画像"
[FINALIZE]           (在线 LLM 调用，把 draft_profile 翻译成 profile schema 落盘)
  ↓
[DONE]               (终态)
```

### 2.1 各状态职责

**INIT**：加载账号原始数据，初始化空 draft_profile（含三态结构）与空对话历史。

**ANALYZE**：消费全部账号数据，产出候选 claims 列表。每条 claim 自带 proposed_state、confidence、evidence。confidence 达到阈值的项写入 draft_profile 对应三态。

**PRESENT**：从 draft_profile 中选 3 至 4 条最有代表性的 confirmed 与 personalized claims，外加 1 条 to_explore claim，生成自然语言的"假设呈现"发给用户。

**VALIDATE**：解析用户响应，对每条被提及的 claim 输出处理指令（确认 / 修正 / 否认 / 转 to_explore），并提取用户回复中的新观察，更新 draft_profile。

**EXPLORE**：从 draft_profile.to_explore 中按 priority 选第一条，生成聚焦提问。退出条件是高优先级 to_explore 项已全部触碰，或用户连续 2 轮显示疲劳。

**SUMMARIZE**：将 draft_profile 翻译成自然语言总览（按"我对你的理解"格式分确定项、个性化项、待探索项三段呈现），请用户确认。前端在该状态显示明确的"生成画像 →"按钮。

**FINALIZE**：`/api/onboarding/finalize` 端点的专属态。把 draft_profile 严格翻译为符合 Echo Profile schema（pydantic `extra="forbid"`）的 JSON，并落盘为 `runtime_data/profile_v1.json`。该阶段一次性、不与用户交互。

**DONE**：终态。前端 store 把 `profileReady = true`，触发 onboarding gate 解锁 profile / ideate / retro 三个模块。

## 3. Memory

Memory 分三层，按"是否进入每次 prompt"和"生命周期"两个维度划分。

### 3.1 Layer 1：会话工作记忆（in-context）

每次 LLM 调用时进入 prompt 的内容，每次都根据当前阶段裁剪。包括：

* 当前状态名
* draft_profile 的相关切片（PRESENT 阶段用 candidate_claims 摘要，VALIDATE 阶段用上轮被讨论的 claim，EXPLORE 阶段用 to_explore 列表）
* 最近 4 至 6 轮对话
* 上一步内部计算或解析的输出

### 3.2 Layer 2：会话持久化记忆

不进入每次 prompt，但 session 全程保留：

* draft_profile：完整画像草稿
* candidate_claims：ANALYZE 阶段产出的全部候选（含未进入 draft 的低 confidence 项）
* 完整对话历史
* 状态切换日志

### 3.3 Layer 3：跨 session 记忆（schema 预留）

为后续 refresh 与再 onboarding 留口子。每条 claim 增加 `session_origin` 字段，记录其首次出现的 session。本期不实现。

## 4. Profile Schema（Agent 的输出目标）

```json
{
  "meta": {
    "user_id": "user_a_001",
    "version": 1,
    "created_at": "...",
    "session_id": "onb_001"
  },
  "confirmed": {
    "audience_baseline": { },
    "content_pillars": [
      { "name": "...", "evidence_video_ids": [], "validated_at": "..." }
    ],
    "content_style": { }
  },
  "personalized": {
    "persona_traits": [
      { "trait": "...", "evidence": [], "confidence": 0.78 }
    ],
    "life_context": [
      { "context": "...", "valid_until": "...", "evidence": [] }
    ],
    "unique_assets": []
  },
  "to_explore": {
    "open_questions": [
      {
        "question": "...",
        "options": ["...", "还没想好"],
        "priority": 1,
        "user_concerns": []
      }
    ],
    "hypotheses": [
      {
        "hypothesis": "...",
        "status": "pending",
        "evidence_for": [],
        "evidence_against": []
      }
    ],
    "aspirations": []
  },
  "audit_log": [
    { "ts": "...", "source": "ANALYZE", "change": "added", "claim_id": "c001" }
  ]
}
```

## 5. Prompts

### 5.1 System Prompt（贯穿全部 LLM 调用）

```
你是一个专门帮助早期视频类 KOC 构建账号画像的 AI 助手。
你的目标是用最少的对话轮次，产出一份准确、个性化、可演化的画像。

你必须遵守以下原则：

1. AI 先做功课。在向用户提问前，你已经分析过他的全部历史数据，
   并形成了带证据的假设。绝不使用空白问卷式提问。

2. 三态意识。任何关于用户的判断必须明确归入：
   confirmed（已被数据反复验证）、
   personalized（个性化但尚未量化验证）、
   to_explore（用户尚未明确表态或存在分歧）。
   宁可多放 to_explore，不要强行归类。

3. 引导而非引诱。用户犹豫时，你的任务是帮他想清楚顾虑、
   把模糊问题转化为可验证的假设，而不是替他做决定，
   也不是说服他选择某一边。

4. 证据驱动。每个判断都要可以追溯到具体的视频、评论或用户回复。

5. 简洁。一次发言不超过 3 个核心要点，每轮 100 至 150 字。

6. 中文回复。语言风格平等、温和、专业。
```

### 5.2 ANALYZE Prompt（离线，输入全部账号数据）

```
任务：阅读以下 KOC 账号数据，输出候选画像 claims。

[ACCOUNT_SNAPSHOT]
{{account_snapshot_json}}

[HISTORICAL_VIDEOS]
{{historical_videos_json}}

[TOP_COMMENTS]
{{top_comments_json}}

[AUDIENCE_SNAPSHOT]
{{audience_snapshot_json}}

[BASELINE_METRICS]
{{baseline_metrics_json}}

请严格按以下 JSON 格式输出：

{
  "candidate_claims": [
    {
      "claim_id": "c001",
      "claim_text": "约六成视频聚焦食堂或学校周边餐饮场景",
      "category": "content_pillar",
      "proposed_state": "confirmed",
      "confidence": 0.82,
      "evidence": [
        {"source_type": "video", "source_id": "vid_001", "snippet": "..."},
        {"source_type": "video", "source_id": "vid_004", "snippet": "..."}
      ]
    }
  ]
}

category 取值：content_pillar / persona_trait / life_context / aspiration / open_question
proposed_state 取值：confirmed / personalized / to_explore

判定规则：
* confirmed：至少 5 条独立证据，且无明显反例
* personalized：至少 3 条一致证据，但尚未经数据验证
* to_explore：用户态度暧昧、证据矛盾、属于未来意向
* 至少识别 1 条 open_question 类 claim
* confidence 严格基于证据强度
```

### 5.3 PRESENT Prompt（在线，第一次面对用户）

```
任务：把以下候选 claims 整理成一段对用户友好的"假设呈现"。

[HIGH_CONFIDENCE_CLAIMS]
{{filtered_claims_json}}

[ONE_OPEN_QUESTION]
{{primary_open_question}}

要求：
* 用"我看完了你的 X 条视频，初步感受到..."开头
* 包含 3 至 4 个核心点：覆盖至少 1 个 content_pillar、
  1 个 persona_trait 或 life_context、1 个 to_explore 类观察
* 每点用具体数字或具体素材支撑（"你最近 8 条里有 5 条..."）
* 结尾用开放式确认："这些感受准确吗？哪部分需要修正？"
* 总长度 100 至 150 字
* 用自然段，不用列表
```

### 5.4 VALIDATE Prompt（在线，处理用户回复）

```
任务：根据用户回复，输出对每条被提及 claim 的处理指令。

[CLAIMS_PRESENTED_LAST_TURN]
{{claims_in_last_present_json}}

[USER_REPLY]
{{user_reply_text}}

请严格输出 JSON：

{
  "actions": [
    {
      "claim_id": "c001",
      "action": "confirm | modify | reject | move_to_explore",
      "new_text": "...（仅 modify 时填）",
      "reason": "用户原话或意图概括"
    }
  ],
  "new_observations": [
    {
      "category": "...",
      "claim_text": "...",
      "proposed_state": "...",
      "evidence": [{"source_type": "user_reply", "snippet": "..."}]
    }
  ],
  "user_signals": {
    "fatigue_level": "none | mild | strong",
    "engagement_topics": ["..."]
  }
}

判定指引：
* 用户明确说"对"或确认 → confirm
* 用户说"对但..." → modify，提取修正部分
* 用户说"不对" → reject
* 用户说"还没想好"或表达犹豫 → move_to_explore
* 用户提供新信息（新顾虑、新意向）→ 写入 new_observations
* 短回复 / 跳过 / 要求结束 → fatigue_level 升级
```

### 5.5 EXPLORE Prompt（在线，循环执行）

```
任务：从 to_explore 列表中选优先级最高的一条，
用最适合的方式向用户提问。

[CURRENT_OPEN_QUESTIONS_RANKED]
{{to_explore_questions}}

[RECENT_CONVERSATION]
{{recent_turns}}

要求：
* 一次只问一件事
* 如该问题适合用选项辅助，提供 2 至 3 个候选 + 一个"还没想好"
* 提问前承接上一轮（"你刚才提到 X，我想顺着这个聊..."）
* 若上轮显示疲劳，主动收口：
  "我想问的差不多了，要不我先把目前的理解整理给你看看？"
* 总长度 60 至 100 字
```

### 5.6 SUMMARIZE Prompt（在线，结束前总览）

```
任务：把当前 draft_profile 翻译成自然语言总览，请用户确认。

[DRAFT_PROFILE]
{{draft_profile_json}}

要求：
* 分三段呈现：
  第一段："关于你已经清晰的部分..."（confirmed + 高 confidence personalized）
  第二段："你身上让我印象深刻的特质..."（其余 personalized）
  第三段："你还在思考的方向..."（to_explore）
* 每段 2 至 3 句话，引用具体证据
* 结尾："这是我目前的理解，还有需要补充或修正的吗？"
* 总长度 200 至 280 字
```

### 5.7 FINALIZE Prompt（离线，落盘）

```
任务：把当前 draft_profile 转换为符合 Echo Profile schema 的最终 JSON，
准备落盘为 profile_v1.json。

[DRAFT_PROFILE]
{{draft_profile_json}}

[ACCOUNT_CONTEXT]
user_id: {{user_id}}
session_id: {{session_id}}
generated_at: {{generated_at}}

请严格输出符合 Echo Profile schema 的 JSON 对象（pydantic 严格 extra="forbid" 校验），
顶层字段：meta / confirmed / personalized / to_explore / audit_log。

约束：
* meta.user_id / meta.session_id / meta.created_at 必须使用 ACCOUNT_CONTEXT 提供的值
* meta.version 固定为 1
* 所有 datetime 用 ISO8601 字符串
* 严禁出现 schema 外字段（extra="forbid"）
* audit_log.source 取值必须是 ANALYZE | VALIDATE | EXPLORE | RETRO_UPDATE | USER

仅输出 JSON 对象，不要任何其他文字（包括代码围栏）。
```

完整 prompt 模板见 `backend/prompts/onboarding/06_finalize.txt`。

## 6. Demo 中实现什么 / Mock 什么

### 6.1 Demo 中实际实现的部分

* 八状态 workflow 的完整流转（INIT → ANALYZE → PRESENT → VALIDATE ⇄ EXPLORE → SUMMARIZE → FINALIZE → DONE）
* 六个 LLM 调用阶段（ANALYZE / PRESENT / VALIDATE / EXPLORE / SUMMARIZE / FINALIZE）
* draft_profile 在三态间的构建、修改、提交
* 最终 profile_v1.json 的产出 + onboarding gate 解锁

### 6.2 Demo 中 Mock 的部分

**全部账号原始数据**通过预制 JSON 文件提供，覆盖一个完整的用户故事（小A，校园 vlog 与食堂探店混合，正在考虑是否把考研作为长期内容主轴）：

| Mock 文件 | 内容 |
|---|---|
| `account_snapshot.json` | 账号身份信息（粉丝量、bio、自报标签等） |
| `historical_videos.json` | 10 至 15 条历史视频（含元数据、文案、指标、drop_off_curve） |
| `comments.json` | 每条视频的 5 至 10 条评论，含可触发 insight 的伏笔 |
| `audience_snapshot.json` | 粉丝画像（年龄、性别、地域、兴趣标签分布） |
| `account_baseline.json` | 历史指标基线（按 pillar 分组） |

**ANALYZE 阶段输出建议预跑固化**为 candidate_claims.json，避免演示现场 LLM 输出方差影响后续阶段稳定性；用户对话部分（PRESENT 之后）实时生成。

### 6.3 Demo 不涉及的部分

* 真实平台 API 接入与数据拉取
* 跨 session 的画像版本管理与 refresh
* 与 ideation / retro 模块的实时联动（demo 末尾仅展示 profile_v1.json 作为下一阶段的输入接口示例）
