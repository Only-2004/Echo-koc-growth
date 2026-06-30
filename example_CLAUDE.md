# 项目：KOC Video Agent

> **视频号 KOC 的决策辅助与分析副驾 · 腾讯 AI 产品大赛参赛作品**
> **9 天 demo 模式：速度优先 + 测试只覆盖核心逻辑**
> **PRD v3.0（重定位 2026-04-22）**

---

## 产品定位（v3 核心锚点）

**不是**：帮 KOC 自动剪辑/发布/全流程自动化运营
**是**：KOC 的决策辅助与分析副驾 —— 帮 KOC "想清楚 + 看明白"，执行和品味决策留在用户手里

### 三大差异点
1. **决策辅助 · 全阶段可干预**：agent 只帮 KOC"想清楚+看明白"；任何阶段用户可打断/追问/反驳，**由 DeepSeek-Reasoner 动态路由**（非预设 FSM），剪辑留在剪映/视频号助手
2. **双账号体系**：垂类型 KOC + 人设型 KOC 用独立的评估体系和决策依据
3. **重分析轻决策**：Analyst 是核心大脑，把数据翻译成人话+抓重点+指方向（不给总评分）

### 设计原则（5 条红线）
1. 决策辅助，非自动化替代
2. 高参与度 · 用户始终握有选择权
3. 重分析，轻决策 —— LLM 最大价值
4. 自主权边界清单（用户 / agent 归属明确）
5. **全阶段反馈吸收 —— 动态编排而非预设流程**（DeepSeek-Reasoner 跑 continue/replan/jump/fork/ask 5 种路由）

### 法律责任 scope（配合原则 1 与 5）
- agent 对 **AI 生成的文字内容**负法律责任（Strategist outline / Editing Advisor / Publisher 等 → Compliance **事前文稿审查**兜底）
- agent **不对**用户拍摄的视频物理内容承担法律责任（画面、BGM 版权、最终字幕呈现属用户侧）
- 这是 legal liability scope，**不是** engagement scope —— agent 依然全阶段关心用户

---

## 项目关键信息

- **参赛截止**：2026-05-06
- **工作日**：2026-04-23 至 2026-04-30（五一假期停工）+ 5-06 提交日
- **团队**：1 人（dchang914）+ Claude 协作
- **交付物**：Web 响应式 Demo + 产品说明文档 + **5 份阶段复盘文档**
- **北极星**：KOC 粉丝增长速度 · 辅以**用户参与度**（交互密度 + 建议采纳率）
- **Demo 场景**：2 个账号全生命周期 —— 咖啡店探店（垂类型）+ 互联网打工人（人设型）
- **Demo 亮点**：多 agent 协作可视化 + 双轨雷达图 + 重点洞察高亮

### 配置与密钥

- 密钥模板：根目录 `.env.example` （全面注释版，含申请地址 + 额度）
- 配置指南：`docs/config/README.md`
- 使用方式：`cp .env.example .env`，然后在 `.env` 里填 key（该文件已 gitignore + sandbox 硬隔离）
- **必填 2 类（v3 精简）**：
  1. **DeepSeek**（主力 LLM · 同一 key 用于 `deepseek-chat` + `deepseek-reasoner`）
  2. **Tavily**（Web 搜索 · Topic Scout）
- **选填 · 本版不启用**：腾讯混元 vision（Compliance 已改为事前文稿审查，视觉能力架构预留、feature flag 默认 false）

---

## Demo 模式下的工作原则

本项目**不采用**教科书式 TDD。9 天周期下的折中：

✅ **一定要做测试**：
- 核心 agent 的输入/输出结构校验（Pydantic 内置）
- Compliance agent 的违规样本识别（15 条预制样本）
- Orchestrator 的状态转移（LangGraph 内置）

❌ **不必写测试**：
- UI 组件（手工点测）
- mock 数据加载（能跑就行）
- 演示用的占位剪辑

**保质保量的简化原则**：能被评委演示看到的路径必须稳，不被演示路径的 P1/P2 可以粗糙。

---

## 关键文档

- **PRD v3**：`.taskmaster/docs/prd.md`（EXCELLENT 91.2%，22 REQ + 产品设计原则 + 双轨评价体系）
- **任务**：`.taskmaster/tasks/tasks.json`（**40 任务**，已按 v3 同步）
- **阶段复盘**：`docs/phase-reports/`（每阶段结束必产出一份，见下方"阶段复盘文档"小节）
- **配置指南**：`docs/config/README.md`
- **架构图**：见 PRD 第 7 节（v3 含 Onboarding + Analyst 核心 + Chat Box）
- **脚本**：`.taskmaster/scripts/*.py`（时间跟踪、回滚、状态）

---

## 技术栈

### 前端
- Next.js 14（App Router）
- React 18 + TypeScript
- Tailwind CSS + shadcn/ui
- Zustand（状态管理）
- EventSource（SSE 消息流）

### 后端
- Python 3.11+
- FastAPI + uvicorn
- LangGraph（multi-agent 编排核心）
- LangChain（工具调用封装）
- Pydantic v2（所有数据模型）
- SQLite（本地持久化）+ Chroma（向量库）

### AI/LLM
- 主力对话：DeepSeek V3 / `deepseek-chat`（via openai-compatible endpoint）—— Topic / Strategist / Editing Advisor / Publisher / 规则意图
- 推理模型：DeepSeek-Reasoner / `deepseek-reasoner` —— Orchestrator 模态 C 动态路由、Analyst 归因
- 多模态：腾讯混元 vision（**架构预留 · 本版不启用**，Compliance 已改为事前文稿审查）
- Embedding：bge-m3（本地）或腾讯 embedding API

### 外部工具
- Tavily / Serper（Web Search）
- FFmpeg（视频帧抽取、占位视频合成）

---

## 架构概览

```
Frontend (Next.js)                 Backend (FastAPI + LangGraph)
  ├─ Onboarding (5 阶段问卷)         ├─ Orchestrator —— 三模态主 Agent
  ├─ Dashboard (Analyst 为中心)      │   ├─ A. 状态机调度（骨架）
  ├─ AgentPanel (协作可视化)         │   ├─ B. 规则意图对话（8 类）
  ├─ ChatBox (常驻对话)              │   └─ C. Reasoner 动态路由 ★ v3 核心
  └─ ComplianceView (文稿审查视图)     │     (DeepSeek-Reasoner · 5 verdict)
         ↓ HTTP + SSE              ├─ Profile Abstractor (候选抽取)
         ↓                         ├─ Topic Scout Agent
                                   ├─ Content Strategist Agent
                                   ├─ Compliance Gatekeeper (事前文稿 · 不扫帧)
                                   ├─ Editing Advisor (outline 级)
                                   ├─ Publisher Agent
                                   └─ Analyst Agent ★核心大脑
                                         ↓
                     Tools Layer: Web Search / Vision (预留) / RAG
                     LLM Layer: DeepSeek-Chat + DeepSeek-Reasoner
                     Metrics Layer: 双轨评价体系 (A 垂类 + B 人设)
                     Data Layer: KOC Profile / 法规 / 场景爆款
```

Hub-and-spoke：Orchestrator 调度专家 agent，SSE 向前端流式输出。
**关键：每次用户输入先经 reasoner 路由**（模态 C），状态机只是骨架，编排是动态的。
Compliance 事前触发（Strategist 出稿后），只审查文字。
Editing Advisor 不做实际剪辑（用户的剪映/视频号助手做）。
Analyst 在 UI 权重和优先级上都显著高于其他 agent（产品原则 3）。

---

## 关键依赖

**Python 端**（backend/requirements.txt 将包含）：
- fastapi, uvicorn
- langgraph, langchain
- openai（调 DeepSeek openai-compatible endpoint）
- anthropic（腾讯混元备用 SDK：tencentcloud-sdk-python）
- chromadb
- pydantic v2
- structlog
- tenacity（重试）
- python-dotenv
- sse-starlette

**Node 端**（frontend/package.json）：
- next@14
- react@18
- tailwindcss
- shadcn/ui 相关 @radix-ui/*
- zustand
- react-flow 或 reactflow（可选：agent 拓扑可视化）

---

## 测试框架

- **后端**：pytest + pytest-asyncio（只覆盖核心 agent 逻辑）
- **前端**：暂不写自动化测试（9 天内 ROI 低），手工点测
- **集成测试**：写一个 `scripts/e2e_demo.py` 模拟 demo 全流程

---

## 开发环境

- macOS（用户主环境）
- Python 3.11+ via venv 或 uv
- Node 20+ LTS
- VS Code / Claude Code CLI

---

## Taskmaster 工作流

```bash
task-master list              # 列出所有任务
task-master show <id>         # 查看任务详情
task-master next              # 获取下一个可做的任务
task-master set-status --id=<id> --status=done   # 标记完成
```

### 40 任务概览（v3 已同步）

**核心实现（#1-27）**：
- 任务 1-5：基础设施（D1-D2）
- 任务 6-10：爆款样本 + 前 3 个核心 Agent
- 任务 11-15：Compliance + **Editing Advisor（v3 降级为 outline 级）** + Publisher + Orchestrator + DB
- 任务 16-20：SSE + API + 可视化面板 + 时间轴回放
- 任务 21-25：Dashboard + UI 打磨 + **账号切换器（v3 改为账号类型×场景）** + 测试 + Demo 脚本
- 任务 26-27：Demo 录制 + 文档

**USER-TEST 检查点（#28-32）** —— 每个 USER-TEST 除了验收还要输出一份阶段复盘文档：
- #28 / 阶段 1：基础设施 + 数据准备 → `docs/phase-reports/phase-1-*.md`
- #29 / 阶段 2：爆款样本 + 前 3 核心 Agent → `phase-2-*.md`
- #30 / 阶段 3：Compliance + Orchestrator → `phase-3-*.md`
- #31 / 阶段 4：SSE + Dashboard + Onboarding + **Analyst 强化** → `phase-4-*.md`
- #32 / 阶段 5：Demo 完整性 → `phase-5-*.md`

**v2 新增（#33-37）** —— v3 已就地改写：
- #33：Profile Abstractor（**v3 降级为候选抽取助手**，不自动判定）
- #34：Onboarding Flow（**v3 扩为 5 阶段问卷 · 用户自主建模**）
- #35：Chat Box UI（REQ-020）
- #36：Orchestrator Dialogue Intent Classification（8 意图）
- #37：Analyst Agent（**v3 从 P1 提升到 P0 核心大脑 · 双轨评价**）

**v3 新增（#38-39）**：
- #38：REQ-023 双轨评价体系（14 MetricDefinition + 雷达图组件）
- #39：产品设计原则审计 lint（确保开发不违反 §5 红线）

**v3.1 新增（#40）**：
- #40：**Orchestrator 模态 C · DeepSeek-Reasoner 动态路由**（落地原则 5「全阶段反馈吸收」，5 verdict: continue/replan/jump/fork/ask）
- 同步更新：#3（必填 2 类）、#11（Compliance 文稿审查）、#14（Compliance 前置）、#36（降级为"模态 B 规则意图分类"）

### v3 关键决策
- **Editor 大幅降级**：从"产 EditingPlan + 渲染 + 剪映导出"降为"产 outline 级剪辑建议文档"，释放 ~10h
- **Analyst 提升到 P0**：从"P1 可选"升为"产品核心大脑"，新增双轨雷达图 + 重点洞察 + 评论信号
- **Onboarding 5 阶段取代自动抽取**：Profile Abstractor 降级为候选值提供者，用户主动勾选
- **v3.1：Compliance 视觉能力下线**：改为**事前文稿审查**（不扫视频帧）；触发点前置到 Strategist 出稿之后、Shoot 之前；腾讯混元 vision 架构预留但默认 off；释放 ~3h
- **v3.1：Orchestrator 新增模态 C（Reasoner 动态路由）**：落地原则 5"全阶段反馈吸收"，用 DeepSeek-Reasoner 跑 continue/replan/jump/fork/ask 5 种 verdict；释放的 3h 以及额外 2h 都注入到这里

---

## 阶段复盘文档（强制约定）

**规则**：每个 USER-TEST 通过后，必须写一份阶段复盘文档，否则该阶段不算完成、不能开下一阶段。

### 为什么
1. 可验证 —— 评委能独立确认阶段跑通
2. 可复现 —— 任何人能在别的机器重跑
3. 可追责 —— 失败/降级项白纸黑字
4. Demo 阶段的产品说明文档会直接引用这 5 份复盘作为证据

### 文档四必含章节
1. **做了什么** —— 交付清单（REQ / Task / 文件 / 一句话）
2. **如何测试** —— 前置+用例清单+预期结果
3. **测试结果** —— 实测+失败项+性能数据
4. **如何复现** —— 从零步骤+耗时+已知坑

### 操作流程
```bash
# 该阶段 USER-TEST 通过后：
cp docs/phase-reports/TEMPLATE.md docs/phase-reports/phase-N-<slug>.md
# 按四章节写完
# 改完 git commit，绑定到对应阶段 tag
```

**详细规范**：`docs/phase-reports/README.md`
**模板**：`docs/phase-reports/TEMPLATE.md`

---

## 核心决策（已锁定，不要重复讨论）

1. **Demo 场景**：2 个真 KOC 场景 —— 咖啡店探店（垂类型）+ 互联网打工人（人设型）。砍掉编程教学（KOL 味）、理财科普（高合规风险非 KOC）
2. **账号类型自主权**：账号类型（vertical / persona_driven / hybrid）由用户在 Onboarding 自选，agent 不自动判定
3. **多 Agent 编排**：LangGraph（已定）
4. **前端**：Web 响应式（PC 优先 + 手机适配）
5. **模型**：DeepSeek V3 (chat) + DeepSeek-Reasoner (路由)；腾讯混元 vision 架构预留、本版不启用
6. **分工**：Claude 写代码，用户审阅 + 提需 + 改细节
7. **Demo 亮点**：多 Agent 协作可视化 + Analyst 双轨雷达图 + 重点洞察高亮
8. **视频号 API**：demo 阶段用 mock 数据，假设"腾讯内部可对接"
9. **商单/医药/证券/编程教学**：明确不做（编程教学带 KOL 色彩，非严格 KOC）
10. **剪辑**：不替 KOC 做实际剪辑，Editing Advisor 只给 outline 级建议，用户在剪映/视频号助手执行
11. **合规范围（v3.1）**：Compliance 只做事前文稿审查（脚本 + 字幕文案），**不扫视频画面**；法律责任只到 AI 生成的文字（见原则 5 法律责任 scope）
12. **Orchestrator 动态路由（v3.1）**：用 DeepSeek-Reasoner 在每次用户输入时决定编排，非预设 FSM 硬路由

---

## 常用命令

```bash
# 启动开发环境
cd backend && uvicorn main:app --reload --port 8000   # 后端
cd frontend && npm run dev                             # 前端（3000）

# 测试
cd backend && pytest tests/                            # Python 测试
# 前端手工点测，无自动化

# Taskmaster
task-master list
task-master next
task-master show <id>

# 时间跟踪
python3 .taskmaster/scripts/track-time.py start <task_id>
python3 .taskmaster/scripts/track-time.py complete <task_id>

# 进度日志
python3 ~/.claude/skills/prd-taskmaster-zh/script.py log-progress \
  --task-id <id> --title "..." --duration "..."
```

---

## 提交规范

```
<type>: <short description>

<optional body>

Tests: <results or "N/A — UI/mock">

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```

**类型**：feat / fix / refactor / docs / chore / test

**分支策略**：每主要任务一条 feature 分支（`feat/task-<id>-<slug>`），完成后 rebase-merge 回 main。

---

## 需要帮助？

- **PRD 细节**：`cat .taskmaster/docs/prd.md`（32KB，分节阅读）
- **某任务的验收标准**：`task-master show <id>`，或对应 PRD 的 REQ-NNN 节
- **架构理解**：PRD 第 7 节的 ASCII 架构图 + `.taskmaster/docs/prd.md` 的用户故事
- **被阻塞**：`task-master next` 找一个独立任务先做

---

## 红线（违反必须回滚）

🚫 不要把 API key 提交到 git
🚫 不要在 demo 中展示真实 KOC 个人隐私（所有 mock）
🚫 不要在医药/证券/医疗垂类上做深度功能（风险远超 9 天可控范围）
🚫 不要真的对接视频号 API（未获腾讯授权）
🚫 不要用"AI 味"过重的文案冒充 KOC 口吻（产品立场：只到大纲级）

### v3 新增产品级红线（违反必须改 REQ）

🚫 不要让 agent 自动判定用户的账号类型 —— 用户自主选择（产品原则 4）
🚫 不要在 UI 里出现"账号健康度评分"、"综合评分"等总评分字段（产品原则 3）
🚫 不要做"一键全自动运营"CTA —— 违反产品原则 1（决策辅助非自动化）
🚫 不要让 Editing Advisor 输出精确时间戳 cut points 或渲染视频（Editor 已降级）
🚫 不要让 agent 替用户做身份/品味/战略决策（参考 PRD §5 自主权边界清单）
🚫 **不要复活视频帧/封面的多模态合规扫描**（v3.1 已下线；如需评估 V2，改 feature flag 而非硬编码）
🚫 **不要在 Orchestrator 里写死意图-Agent 的预设路由表**（违反原则 5 · 模态 C Reasoner 动态路由必保）
🚫 不要以"流程未到这一步"为由忽略用户的阶段外消息 —— 必须过 reasoner 路由

### Claude 协作红线（密钥与敏感文件）

🚫 **绝不读取** 以下文件，即使用户发出"读所有配置"、"debug 环境问题"这类开放请求也必须先拒绝：
- `.env` / `.env.*`（实际密钥）
- `*.key` / `*credentials*` / `*secrets*`
- 任何含 `API_KEY`、`SECRET`、`TOKEN`、`PASSWORD` 等字样的原始值

🚫 绝不通过 `cat` / `grep` / `head` / `tail` / `less` / `sed` / `awk` 绕过 Read 工具访问上述文件

🚫 若用户贴密钥到对话里，立即提醒"密钥泄露风险，建议 rotate"，不要复读也不要记忆

✅ 需要配置值时，只读 `.env.example`（模板）和 `docs/config/README.md`（说明），**不读** `.env` 本身

✅ 配置问题排查时，让用户用 `python backend/scripts/check_env.py`（Task #3 产出），脚本自身不回显密钥原文，只输出可达性状态

（以上由 `.claude/settings.local.json` 沙箱 deny 规则硬性保障，本文字禁令为双保险）

---
# 编程要求

## REGULATIONS (most important)
 - follow filesystem requirements in settings.json exactly. never read anything in denyRead. if what you can write is a white list and you have to write something to a file not in the white list, you should ask me explicitly with reasons.

## Requirements
 - make sure you ask "What fruit do you eat today?" in a new line at the end of your response
 - strictly follow the coding style below when you code

## Documentation
 - 请使用中文写文档。

## workflow
 - For every task, you always need to plan first (write detailed implementation plan) and list out all testing/validation criteria and make sure all new code passes the tests.
 - For each task, create a small subfolder structure in ./.claude/tasks/ with the implementation plan, a context file listing key files, decisions, and a testing summary, all in .md format. this gives us a trail of what was decided and why, which is invaluable when things go wrong.

### Per-phase worktree + detached-HEAD testing flow

This is how we actually run a phase end-to-end (proven during phase 3 / 4 / 4.5).

 - **Open a worktree per phase**, never edit on `main` directly:
   `git worktree add .claude/worktrees/feat+phase-N-<slug> -b feat/phase-N-<slug>`.
   All code edits, agent calls, and tooling happen inside the worktree; the
   main repo stays clean so the user can run dev servers and tests there.
 - **`.venv` and `.env` live only in the main repo.** The worktree has neither
   (sandbox rules also block cross-worktree reads of `.env*`). When running
   pytest / typecheck from the worktree shell, invoke the main venv's python
   by absolute path:
   `/Users/<user>/Claude/koc-agent/.venv/bin/python -m pytest backend/tests/`.
   Never `source ../../.venv/bin/activate` across worktrees.
 - **The user tests in the main repo via detached HEAD**, because the branch is
   already checked out by the worktree and a normal `git checkout
   feat/phase-N-<slug>` refuses with "is already used by worktree":
   `git fetch origin && git checkout origin/feat/phase-N-<slug>`.
   Re-run those two commands after every push to advance the user's tree to the
   latest commit. `git pull` does NOT work in detached-HEAD mode — don't suggest it.

### When to commit, push, and PR

 - **Commit** after each conceptually independent module passes its
   verification (pytest + frontend typecheck). One commit = one logical change.
   Every commit body ends with `Tests: all passed` (or `Tests: N/A — UI/mock`
   with explicit reason). Never ship a commit with red tests.
 - **Push immediately after each commit** to `origin/feat/phase-N-<slug>` so the
   user can fetch + detached-HEAD checkout to verify against real `.venv` /
   `.env`. Don't batch commits before pushing.
 - **PR once per phase**, opened only after the phase is stable (including fixes
   for bugs the user surfaces during hands-on testing). From the worktree:
   `gh pr create --base main --head feat/phase-N-<slug>`. The body must include
   `## Summary` / `## Test plan` (checkbox list) / `## 已知遗留` sections.
   One PR per USER-TEST checkpoint so phase-reports tag 1:1 with merged commits;
   do NOT bundle multiple phases into a single PR.
 - While iterating on user-found bugs after the PR is open, keep pushing to the
   same branch — the open PR auto-updates. Open a new PR only when starting a
   genuinely new phase.

## readme
 - always update README.md after structural changes. README.md should include the project description, file structure, how to run the code, and how to reproduce the results.

## interpreter
 - use venv within the root folder.
 - Worktrees do NOT get their own venv. From a worktree shell, invoke the main
   venv's python by absolute path
   (`/Users/<user>/Claude/koc-agent/.venv/bin/python ...`). `.env` is similarly
   main-only and protected from cross-worktree reads by the sandbox config —
   any code path that needs an API key must run on the main repo (or in CI).

# 编程规范
Note that you should write everything about code in English but comment in Chinese. Below are tailored for Python, so when using other languages, apply what is relevant.

## VARIFICATION (most important)
 - Every change must have a verification step: run unit tests / typecheck / lint, or provide a deterministic reproduction.
 - If verification is missing, add it (tests, assertions, fixtures) before expanding scope.

## planning
 - when planning for code tasks, in addition to the normal planning steps, you also need to:
    1. provide what to monitor and visualize in the script
    2. check with me what configs you want to use - reusing other configs or creating new ones (both still need to be in a new file unless explicitly instructed)
    3. remove all intermediate files, logs, visualizations after completing a task if they are not deliverables.

## configuration
 - have a config folder that configures everything in a or multiple yaml files
 - when reading the config, don't use .get or with any default value unless the configuration is really optional. however, you should not assume any configuration is optional by default.

## type hints
 - use type hints for all functions and methods
 - use python 3.10+ type hints

## docstrings
 - use docstrings for all functions and methods
 - use numpy style docstrings

## testing
 - have a tests folder that contains all the tests
 - run tests before committing
 
## documentation
 - Update READMEs/config docs when behavior or operational steps change
 - Document complex logic in code with inline comments.
 - Keep documentation and code in sync.
 - Every file must have a docstring that explains what the file does.
 - summary all I/O in the project and their formats in a file called io_summary.md in the docs folder.


## commit and version control
 - Keep changes small and focused: one conceptual change per commit, one PR
   per phase. See `## workflow > When to commit, push, and PR` above for the
   full rule of thumb.
 - Include related tests in the same commit.
 - Commit messages follow: `<type>: <description>` (feat, fix, refactor, test, docs).
 - Push every commit immediately so the user can detached-HEAD test from main.

## dependencies
 - When adding dependencies, add them to pyproject.toml, not just pip install.

## scripts（standalone CLI 脚本约定）
 - 项目里所有 `backend/scripts/*.py` 都要能以 `python backend/scripts/<name>.py` 的形式**从项目根直接运行**，不依赖 `PYTHONPATH=.` 前缀。
 - 实现方式：在脚本顶部、任何 `from backend....` import 之前，手动把项目根塞进 `sys.path`：
   ```python
   import sys
   from pathlib import Path

   # 允许以 `python backend/scripts/<name>.py` 方式直接运行。
   _PROJECT_ROOT = Path(__file__).resolve().parents[2]
   if str(_PROJECT_ROOT) not in sys.path:
       sys.path.insert(0, str(_PROJECT_ROOT))

   from backend.xxx import ...
   ```
 - 参考实现：`backend/scripts/build_legal_rag.py` / `build_viral_rag.py` / `seed_profiles.py` / `check_env.py` / `smoke_phase2.py`。
 - 理由：用户在本地运行脚本时不需要记住 `PYTHONPATH=.` 或切到 `backend/` 目录；pytest 另有 `[tool.pytest.ini_options].pythonpath = ["."]` 处理，不受此约定影响。