# 阶段复盘 · M7 · Orchestrator + Source Tagging

> USER-TEST 通过后归档。`git tag m7-pass`。
> 实施计划：`/Users/zhiyao/.claude/plans/m7-gleaming-seal.md`（仅 Claude 侧持久化）。

---

## 1. 做了什么

| 任务 | 文件 / 模块 | 一句话说明 |
|---|---|---|
| Step 0 | `.claude/worktrees/feat+m7-orchestrator` | 基于 `feat/m4-m6-loop` (96a95e2) 开新 worktree；清理 6 个 M0–M6 旧 worktree（分支保留） |
| Step 1 | `backend/agents/_common/source_tag.py` | 抽出 `extract_sources` + `validate_and_extract` 共享 util，PRD §6.7 canonical 3 tag |
| Step 2 | `backend/prompts/orchestrator/{route_system,route_examples,system,scene_*}.txt` | 8 份 prompt：route 阶段 system + 8 组 few-shot；chat 阶段 system + 5 段 scene-specific 角色补充 |
| Step 3 | `backend/agents/orchestrator/context_builder.py` | 按 `needs_slices` 子集装配 profile / strategy / retro 切片，单 slice 截 1500 字 |
| Step 4 | `backend/agents/orchestrator/{handlers,service}.py` | flash-thinking 流式 + source guard：流末 extract，无 tag complete retry，再无 fallback `[数据驱动]` |
| Step 4a | `backend/agents/orchestrator/router.py` | flash 无 thinking + JSON：解析 `RouteDecision{intent,needs_slices,tone,expect_suggestions}`，retry 1 次 + 保守 fallback |
| Step 5 | `backend/api/orchestrator.py` + `backend/main.py` | `POST /api/orchestrator/chat` SSE 端点，事件 `route/delta/done/error`；注册到 app.state |
| Step 6 | `backend/tests/test_{source_tag_util,orchestrator_router,orchestrator}.py` | 29 个新增测试（13 + 9 + 7），全套 70 个 backend 测试无回归 |
| Step 7 | `frontend/src/api/orchestrator.ts` | `chatOrchestrator(...)` SSE 消费，复刻 `drillRetro` retry 模式 |
| Step 8 | `frontend/src/components/chat/useChatSend.ts` | 把原 `else` 分支换成调 orchestrator，把 chatLog 转 `ChatTurnPayload` 送回后端，done 事件写入 sources/suggestions |
| Step 9 | `frontend/src/components/chat/ChatDock.tsx` | suggestion `<button>` 加 `onClick={() => send(s)}`，建议作为新一轮 user turn 提交 |

**核心设计决策**：
1. **显式两阶段** route → chat（PRD §7.2 范式：分类用 flash 无 thinking，对话用 flash-thinking）
2. **不重构 M4–M6 既有 source tag 校验**——三家格式（`[tag]` / `<source:tag>` / `SOURCES:`）维持现状
3. **chitchat 也强制 source tag**（红线无例外，fallback 注 `[数据驱动]`）
4. **流式不回退正文**：第一次 stream 无 tag 时**不重写**前端文字，而是用 complete 拿一段单独的 tag → 注入 done 事件的 sources，UX 平滑
5. **chat-everything 任务 #39 不补埋点**：现有 `onAsk(...)` 已遍布 5 scene，M7 只让 home/profile/onboard 真能出回复

---

## 2. 如何测试

### 前置

- [x] `.env` 已配置（主仓库 `/Users/zhiyao/Claude/koc-agent-v2/.env`），含 `DEEPSEEK_API_KEY`
- [x] 主仓库 `.venv` 已 `pip install -e backend[dev]`
- [x] 主仓库 `frontend/node_modules` 已 `npm ci`
- [x] worktree 通过 symlink 复用主仓库 node_modules
- [x] 用户在主仓库 detached HEAD：`git fetch origin && git checkout origin/feat/m7-orchestrator`

### 自动化测试用例

| # | 用例 | 操作 | 预期结果 |
|---|---|---|---|
| 1 | source_tag util | `pytest backend/tests/test_source_tag_util.py` | 13 全绿 |
| 2 | router 4 intent + retry/fallback | `pytest backend/tests/test_orchestrator_router.py` | 9 全绿 |
| 3 | chat 端到端 + retry/fallback + slice 注入 | `pytest backend/tests/test_orchestrator.py` | 7 全绿 |
| 4 | M4–M6 无回归 | `pytest backend/tests/` | 70 全绿 |
| 5 | 前端 typecheck | `cd frontend && npx tsc -b --noEmit` | 0 error |
| 6 | API 路由注册 | `python -c "from backend.main import create_app; ..."` | `/api/orchestrator/chat` 出现 |

### 手工 USER-TEST 用例（5 scene 验收）

| # | 场景 | 操作 | 预期结果 |
|---|---|---|---|
| 1 | home | 在 chat dock 输入「我下一步该做什么」 | AI 回复 + 至少一个 source chip（绿/蓝/琥珀任一） |
| 2 | onboard | onboarding 进行中点 chat dock 追问某条假设 | AI 回复带 chip，**不**推进 onboarding 状态机 |
| 3 | profile | 点待探索项 chip → onAsk | AI 解释依据，sources 含「画像驱动」 |
| 4 | ideate | 没 snapshot 时输入「双轴是什么意思」 | AI 走 orchestrator（不是 strategy/refine），有 chip |
| 5 | retro | 没 report 时输入「我应该放弃这个方向吗」 | AI 走 orchestrator，tone 应该是 encouraging |
| 6 | suggestion | done 事件返回 ≥1 条 suggestion 时点击 | 触发新一轮 user turn，AI 再次回复带 chip |
| 7 | source 红线 | 故意把 LLM 切到 mock + 让 mock 不打 tag | 后端日志能看到 retry → fallback；前端仍渲染一个 chip |

---

## 3. 测试结果

### 实测（自动化）

| # | 用例 | 实测 | 状态 |
|---|---|---|---|
| 1 | source_tag util 13 | 13 passed in 0.02s | ✅ |
| 2 | router 9 | 9 passed in 0.10s | ✅ |
| 3 | chat 端到端 7 | 7 passed in 0.12s | ✅ |
| 4 | M4–M6 全套 | 70 passed in 0.50s（含 M7 新 29 个） | ✅ |
| 5 | 前端 typecheck | exit 0 | ✅ |
| 6 | 路由注册 | `/api/orchestrator/chat` 出现 | ✅ |

### 实测（手工 USER-TEST）

> 用户在主仓库 detached HEAD @ 2d58228 跑完，全绿。

| # | 场景 | 实测 | 状态 |
|---|---|---|---|
| 1 | home 追问 | AI 回复 + source chip 出现 | ✅ |
| 2 | onboard 追问 | AI 回复带 chip，未推进状态机 | ✅ |
| 3 | profile 追问 | sources 含「画像驱动」，依据可追溯 | ✅ |
| 4 | ideate 无 snapshot | 走 orchestrator，chip 正常 | ✅ |
| 5 | retro 无 report | 走 orchestrator，tone 符合预期 | ✅ |
| 6 | suggestion 点击 | 触发新一轮 user turn，AI 再次回复带 chip | ✅ |
| 7 | source 红线 | mock 模式下 retry/fallback 路径如期触发，chip 始终在 | ✅ |

### 失败 / 降级项

- 三个老 agent 的 source tag 格式不统一（`[tag]` / `<source:tag>` / `SOURCES:`）保持现状未重构 —— **理由**：M4–M6 已稳，重构 ROI 低；orchestrator 已有独立、统一的实现；M7 的"后端校验"在 orchestrator 端达成。**影响**：演示中三个老 agent 的 source tag 渲染由各自服务负责，hand-off 时不会出现"格式漂移"，但开发者读代码时会有 confusion。
- `focused_element` 字段后端预留但未消费 —— **理由**：当前前端 `useOnAsk(text)` 只传文本，被点击元素的 ID/数据切片未结构化。**影响**：M8 演示打磨时若需精准追问，需补一次接口字段填充。

### 性能数据

| 指标 | 目标 | 实测 |
|---|---|---|
| route 首响应 | ≤ 1s | 用户实测通过 ✅ |
| chat 首 token | ≤ 5s | 用户实测通过 ✅ |
| chat 总耗时 | ≤ 30s | 用户实测通过 ✅ |
| 自动化套件总耗时 | ≤ 1s | 0.42s（M7 head 主仓库重跑） ✅ |

---

## 4. 如何复现

### 从零步骤

```bash
# 1) 用户在主仓库（detached HEAD）拉到 M7 最新
cd /Users/zhiyao/Claude/koc-agent-v2
git fetch origin
git checkout origin/feat/m7-orchestrator

# 2) 启动后端（主仓库 venv + .env）
.venv/bin/uvicorn backend.main:app --reload --port 8000

# 3) 启动前端（另一个 terminal）
cd frontend
npm run dev      # 默认 5173

# 4) 浏览器打开 http://localhost:5173
#    切到任一 scene，在 chat dock 输入文字 / 点击任意 onAsk 元素

# 5) 跑完整自动化套件验证
.venv/bin/python -m pytest backend/tests/ -q
cd frontend && npx tsc -b --noEmit
```

### 耗时

| 步骤 | 时长 |
|---|---|
| Step 0 worktree 清理 + 新建 | ~10 min |
| Step 1 共享 source_tag util + 13 测试 | ~30 min |
| Step 2 8 份 prompt | ~50 min |
| Step 3 context_builder | ~40 min |
| Step 4 + 4a service / handlers / router | ~2.5h |
| Step 5 API 端点 + 路由注册 | ~30 min |
| Step 6 backend 测试 (router 9 + chat 7) | ~50 min |
| Step 7-9 frontend API + useChatSend + suggestion | ~50 min |
| **小计（不含 USER-TEST）** | **~6.5h** |

### 已知坑

1. **worktree 没有 venv / .env**：从 worktree shell 跑 python 必须用主 venv 绝对路径
   `/Users/zhiyao/Claude/koc-agent-v2/.venv/bin/python`，绝不要 `source .venv/bin/activate`
   跨 worktree。
2. **worktree 没有 node_modules**：用 `ln -s ../../../../frontend/node_modules ./node_modules`
   建相对软链复用主仓库依赖（注意路径深度）。
3. **DeepSeek thinking 与 json_mode 不兼容**：`flash-thinking` 档强 JSON 会让 content 为空。
   router 用 `flash`（无 thinking）+ `json_mode=True` 是正确组合；chat 用
   `flash-thinking` 但**不**强 JSON。
4. **chitchat 没 tag 时 fallback 是 PRD 红线**：`[数据驱动]` 是兜底而非默认；任何
   "AI 消息无 chip" 的 UI 表现都是产品缺陷，回看 `validate_and_extract`。
5. **suggestion 解析靠 `SUGGESTIONS:` 单行**：模型偶尔会把建议混到正文里（"我建议你..."）
   而不是单独成行——属于 prompt 调优问题，不是代码 bug；M8 演示打磨时若高频出现需调
   `system.txt` few-shot。

---

## 后续

- 用户跑完手工 USER-TEST 7 项，回填 §3 实测表 + 性能数据 → `git tag m7-pass`
- 若手工测发现 prompt 输出问题（建议太空 / source tag 错配 / tone 不准），在
  `backend/prompts/orchestrator/` 调整后回归 `pytest backend/tests/test_orchestrator.py`
- M8 演示打磨阶段考虑：把 `focused_element` 字段对接前端 `onAsk(text, element)` 二参版本，
  让 chat dock 显示"你正在问的元素：xxx"
