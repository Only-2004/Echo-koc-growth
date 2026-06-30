# Orchestrator Agent 设计规范

## 1. 这个 Agent 做什么

### 1.1 调用时机

Chat dock 是 Beacon 常驻在 web app 右侧的对话面板。任何 scene 下用户在 chat dock 里发一句话，或者在主面板任意可点击数据卡 / 标签 / 数据点上调用 `onAsk(text)`，都会进入这条 chat 链路。

为减少前端复杂度并保证"chat-everything"模型一致，前端按 scene + 业务上下文做轻量分流（详见 §1.3），其余全部由 Orchestrator agent 兜底。

### 1.2 核心职责

把"用户在 chat dock 的一句话"转化为一段带 source tag 的中文 AI 回复，并给出可选的 follow-up 建议。具体五件事：

* **意图分类**：识别用户这一轮是数据请求、追问、闲聊还是动作请求
* **切片装配**：按需把 profile / strategy / retro 切片注入下游 chat prompt（不挂无关切片，省 token）
* **场景化语气**：根据当前 scene + tone 决定主语风格（home 简短给方向、profile 解释三态、ideate 双轴拆解、retro 共情归因）
* **Source tag 强校验**：每条 AI 回复末尾必须有方括号 source tag 行；缺则 retry 1 次，仍缺注入 fallback `[数据驱动]`
* **Follow-up 建议**：当 `expect_suggestions=true` 时在回复前一行追加 `SUGGESTIONS: 建议1 | 建议2 | 建议3`，前端解析为 chip

### 1.3 设计原则

**两阶段 LLM**。先跑一次极轻 router（`flash` 无 thinking · ≤200 tokens prompt · ≤100 tokens 输出 · 平均 300–600ms），再跑主 chat（`flash-thinking` SSE 流式）。Router 阶段不挂业务切片，避免给 thinking 模型塞无关数据浪费 token；主 chat 按 router 决策的 needs_slices 子集挂切片。

**前端硬路由 + orchestrator 兜底**。出于演示稳定性与 token 成本考虑，前端 `useChatSend.ts` 对两条已经成熟的专属路径直接走专门 endpoint：

* `scene = ideate` 且 `snapshotId` 存在 → `POST /api/strategy/refine`（走 strategy agent 的 REFINE 阶段）
* `scene = retro` 且 `reportId` 存在 → `SSE /api/retro/drill`（走 retro agent 的 DRILL 阶段）
* 其余全部 → `SSE /api/orchestrator/chat`（home / onboard / profile / ideate-pre-snapshot / retro-pre-report）

这样 strategy / retro agent 内部的状态机与 source 校验保持自洽，orchestrator 只兜底"通用 chat"语境。

**Source tag 是产品红线**。PRD §6.7 要求每条 AI 消息至少一个 source tag。Chat 阶段流式结束后用 `_common.source_tag` 校验末行；缺则附加"请严格按格式输出"约束 retry 1 次；仍缺注入保守 fallback `[数据驱动]`，并在 `done` 事件里设 `used_fallback=true`，便于离线分析触发率。

**不假装有数据**。系统 prompt 中明确：用户问的具体数字 / 事实如果切片里没有，回复必须承认"这一项现在没接到数据"，并提示用户去 ideate / retro 看，不能编造。

## 2. Workflow

```
[ROUTE]                       (LLM · flash · ≤200 token · 300-600ms)
  ↓ 输出 RouteDecision { intent, needs_slices, tone, expect_suggestions }
[BUILD_CONTEXT]               (本地文件 IO · 0ms)
  ↓ 按 needs_slices 子集从 runtime_data/ 抽取 profile / strategy / retro 切片
[CHAT_STREAM]                 (LLM · flash-thinking · SSE)
  ↓ system + scene_<scene> + slices + chat_history + user_text
  ↓ 流式 yield delta
[SOURCE_GUARD]                (校验末行 source tag)
  ↓ 缺 tag → retry 1 次 → 仍缺则 fallback [数据驱动]
[DONE]                        (yield {sources, suggestions, used_fallback})
```

实际实现见 `backend/agents/orchestrator/{router,context_builder,handlers,service}.py`。

### 2.1 各阶段职责

**ROUTE**：极轻 LLM 分类。读 `system_route` + `route_examples`（few-shot）+ 当前 scene + 最近 2 轮 user/ai history + 当前 user_text，输出严格 JSON。失败 retry 1 次（附加"上一次输出 JSON 不合法"约束）；仍失败回退保守 `FALLBACK_DECISION`（挂全部三个切片 + concise + 给建议），让下游不会因为 router 故障 cascade 失败。

**BUILD_CONTEXT**：纯本地文件读取，按 needs_slices 从 `runtime_data/` 抽：

* `profile`：读 `profile_v{max_n}.json`，提取三态前 3 项 + 最近 3 条 audit。**显式约束**：待探索项独立成段（PRD §3 红线），不与确定项 / 个性化项合并
* `strategy`：读最新 `strategy_snapshot_*.json`（按 mtime），提取 idea + heat + fit_score + 前 3 条 differentiation + execution（含 key_focus）
* `retro`：读最新 `insights_report_*.json`，提取前 4 张 data_cards + 前 3 条 strategy_review + 前 3 条 insights

每个 slice 文本上限 1500 字符；超长截断尾部加 `…(已截断)`。文件不存在时该 key 不出现在 dict 中（不报错）。

**CHAT_STREAM**：拼装 prompt：

```
system: backend/prompts/orchestrator/system.txt
       + backend/prompts/orchestrator/scene_<scene>.txt
       + slices（profile / strategy / retro，按 needs_slices）
       + tone hint
       + expect_suggestions hint
user:   chat_history（最近若干轮）+ 当前 user_text
```

模型固定 `flash-thinking`，SSE 流式 yield `{type: "delta", delta: "..."}`。

**SOURCE_GUARD**：流结束后取末段文本，正则匹配 `[xxx yyy]` 形式的 source tag 行。命中则 yield `{type: "done", sources: [...], suggestions: [...], used_fallback: false}`；未命中 → 重跑 CHAT_STREAM 一次（system 末尾追加"上一次输出缺 source tag，请严格按格式补齐"）；二次仍缺 → fallback `sources = ["数据驱动"]`、`used_fallback: true`。

## 3. Memory

Orchestrator 是 stateless 路由 + 单轮对话 agent，不持有跨 session 状态。

### 3.1 Layer 1：会话工作记忆（in-context）

每次 `/api/orchestrator/chat` 调用前端把以下内容塞回来：

* `scene`：当前 scene
* `user_text`：当前轮用户发言（≤ 2000 字符）
* `chat_history`：最近若干轮 `ChatTurn{role, text, sources?, suggestions?}`，后端 router 实际只看末 6 项里的最近 2 轮 user/ai
* `focused_element`：可选的"当前点击的元素 id"（预留字段，当前实现不消费）

### 3.2 Layer 2：会话持久化记忆

无。Demo 单 persona 单机，对话历史完全由前端 zustand store 持有（按 scene 分隔的 `chatLog: Record<Scene, ChatMessage[]>`）。后端不持久化任何对话。

### 3.3 Layer 3：跨模块共享

无独立存储。Orchestrator 通过 `BUILD_CONTEXT` 从 `runtime_data/` 实时读其他 agent 写下的产物（profile_v*.json / strategy_snapshot_*.json / insights_report_*.json），不持有任何缓存。

## 4. RouteDecision Schema

```json
{
  "intent": "data_request | clarification | chitchat | action",
  "needs_slices": ["profile" | "strategy" | "retro"],
  "tone": "concise | explainer | encouraging",
  "expect_suggestions": true
}
```

字段说明（详见 `backend/agents/orchestrator/router.py:RouteDecision`）：

* **intent**
  * `data_request`：用户问数据 / 画像 / 策略 / 复盘的具体问题（"为什么这条建议排第一？"）
  * `clarification`：对前一轮 AI 回复追问 / 让换说法 / 表达没看懂
  * `chitchat`：打招呼、问"你能干啥"、闲聊、元交互
  * `action`：用户想让你执行操作（"把这条加进画像"、"标记为已采纳"）
* **needs_slices**：`profile / strategy / retro` 任意子集；chitchat 或与数据无关时返回 `[]`。当前 scene 隐含一个偏向（profile scene → 倾向挂 profile），但用户问的内容才是判断主依据
* **tone**
  * `concise`：home / onboard / 简短问答的默认
  * `explainer`：profile / ideate 里追问"为什么"——需要解释推理链
  * `encouraging`：retro 复盘语境，当用户表现出挫败感时
* **expect_suggestions**：data_request / clarification 后给 follow-up 建议有用；chitchat / action 通常 false（不要无意义建议）

`FALLBACK_DECISION`（router 两次失败时的兜底）：

```json
{
  "intent": "data_request",
  "needs_slices": ["profile", "strategy", "retro"],
  "tone": "concise",
  "expect_suggestions": true
}
```

多挂切片只是浪费 token，不会出错。

### 4.1 SSE 事件协议（API 层）

`POST /api/orchestrator/chat` 返回 `text/event-stream`，事件 schema：

| 事件 type | 字段 | 说明 |
|---|---|---|
| `route` | `decision` | 路由结果（debug 用，前端可忽略） |
| `delta` | `delta` | 流式 token |
| `done` | `text`, `sources`, `suggestions`, `used_fallback` | 最终回复（已 strip source tag 行）+ 解析后的 source 列表 + suggestions chip + 是否走了 fallback |
| `error` | `message` | LLM 异常 / 参数错误 / 服务未挂载 |

实际实现见 `backend/api/orchestrator.py`。

## 5. Prompts

### 5.1 System Prompt（贯穿全部 chat 调用）

完整内容见 `backend/prompts/orchestrator/system.txt`。核心约束：

```
1. 上下文感知。只引用切片里出现过的事实，切片缺则诚实说"这条我现在还没数据"
2. 简洁。一次发言不超过 3 个核心要点。中文。语气平等、温和、专业
3. Source tag 强制契约。每条回复最后一行用方括号标注来源：
       [画像驱动] [趋势驱动] [数据驱动] 等（多 tag 空格分隔）
   不可省略，下游有强校验
4. SUGGESTIONS（条件性）。expect_suggestions=true 时在 source tag 行之前追加：
       SUGGESTIONS: 建议1 | 建议2 | 建议3
   每条 ≤ 12 字，3 条以内，必须具体不空洞
5. 引导而非引诱。给选项不下处方
6. 不假装有数据。chitchat 也要打 source tag（兜不到用 [数据驱动]）

输出格式（严格）：
    [正文段落，中文，简洁]
    [可选] SUGGESTIONS: 建议1 | 建议2 | 建议3
    [tag1 tag2]
```

### 5.2 Router System Prompt + Few-shot

`backend/prompts/orchestrator/route_system.txt` 定义 schema 与字段含义；`route_examples.txt` 提供 9 条 few-shot 校准 intent / needs_slices / tone / expect_suggestions（覆盖 home 闲聊、profile 数据请求、profile action、ideate 解释、ideate clarification、retro 共情、retro 闲聊收尾、onboard 不同意上轮等典型场景）。

### 5.3 Scene Prompts（5 个）

按当前 scene 注入更具体的角色补充：

| Scene | 角色 | 行为约束 |
|---|---|---|
| `scene_home.txt` | "今天我能帮你做什么"助手 | 短、给方向、不啰嗦；主动引导去 ideate / retro。可调切片：profile + retro |
| `scene_onboard.txt` | "画像 onboarding · 我在听"副助手 | 不推进 onboarding 状态机；只引用已成型 candidate_claims；鼓励用户回主流程。可调切片：profile（中间状态） |
| `scene_profile.txt` | "画像编辑器" | 解释三态判定标准；待探索项独立成列（PRD §3 红线）；增删改提示用户用 UI 编辑按钮。可调切片：profile |
| `scene_ideate.txt` | "选题顾问" | 双任务：A 选题探索（snapshot 未生成时，磨尖标题/角度/思路 → 在 SUGGESTIONS 行加 `[GENERATE_BRIEF]<标题>` 触发器）；B 策略解读（snapshot 已生成时，把双轴拆开讲）。可调切片：profile + strategy |
| `scene_retro.txt` | "复盘分析师"副线 | 主场是 retro/drill；orchestrator 只在 report 未生成或用户问情绪/元层面问题时被呼叫。共情后再分析。可调切片：retro + profile |

### 5.4 `[GENERATE_BRIEF]` 跨模块跳转

ideate scene 中，当用户在 chat 里磨清选题方向后，scene_ideate prompt 要求 LLM 在 SUGGESTIONS 行加入 `[GENERATE_BRIEF]<选题标题>` 触发器；前端 chat dock 解析到该 prefix 后渲染为"生成拍摄简报 →"按钮，点击后通过 zustand `pendingIdeaFromChat` 把对话中的"标题 + 核心角度 + 拍摄思路"自动回填到 IdeateView 的 idea 输入框，触发完整 strategy 流程。

这是 chat-everything 模型的反向案例：从 chat 跳回主面板，让对话沉淀为可执行 idea，对应 PRD §6.4 末尾"Chat → Ideate 回填"机制。

## 6. Demo 中实现什么 / Mock 什么

### 6.1 Demo 中实际实现的部分

* 完整 ROUTE → BUILD_CONTEXT → CHAT_STREAM → SOURCE_GUARD → DONE 流转（M7 backend 全部就绪）
* 5 个 scene prompt 全部上线，可被路由
* RouteDecision schema 校验 + 失败 fallback
* Source tag 强校验 + retry + fallback
* `POST /api/orchestrator/chat` SSE 端点
* 前端 `useChatSend.ts` 中"orchestrator 兜底"路径已接入（home / onboard / profile / ideate-pre-snapshot / retro-pre-report 全部走 orchestrator）
* `[GENERATE_BRIEF]` 跨模块跳转

### 6.2 Demo 中 Mock 的部分

* 无独立 mock 数据。orchestrator 只读其他 agent 写下的 `runtime_data/profile_v*.json` / `strategy_snapshot_*.json` / `insights_report_*.json`，所以演示前必须先走完 onboarding 才能让 profile slice 有内容
* `focused_element` 字段定义但当前实现不消费（前端尚未传入；预留给未来"点哪条数据卡 chat 里 highlight"功能）

### 6.3 Demo 不涉及的部分

* 跨 session 的对话历史持久化（demo 单 persona 单机，前端 zustand 即足够）
* 多模型 ensemble（router 与 chat 都固定走 DeepSeek v4 单家）
* `action` intent 的实际执行（当前 LLM 会回答"这是 action 类请求，请在 UI 上点编辑按钮"，不真改文件）

### 6.4 已知未完成 / 路线图

* **`focused_element` 消费**：当前前端未传，后端未读。下版本可让用户点 profile 某条 claim 时自动把 claim_id 传过来，scene_profile prompt 直接定位
* **Tone = encouraging 的覆盖**：当前 retro scene 在 chat dock 内主要走 retro/drill 专属路径；orchestrator 的 encouraging tone 主要服务于"用户表达挫败感但 report 还没生成"这种边缘场景
* **多 turn action 链**：当前 action intent 不真改后端状态。未来可让 orchestrator 调 profile.update / strategy.persist 等 endpoint 闭环

---

文档完。Orchestrator 与 onboarding / strategy / retro 三个核心 agent 平级，作为 chat dock 的统一兜底层。本 spec 的实施进度对应 PRD §12 Milestone 7。
