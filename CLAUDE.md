# 项目：Beacon · KOC 成长伙伴

> **Beacon · KOC 成长伙伴 · v1.0**
> **PRD：`.taskmaster/docs/prd.md`（同步副本：根目录 `PRD.md`）**

---

## 产品定位（核心锚点）

**不是**：自动剪辑 / 自动发布 / 全流程自动化运营
**是**：早期视频类 KOC（粉丝 1K–10K）的 **画像建立 → 选题策略 → 复盘洞察** 闭环 AI 成长伙伴

### 四层差异点
1. **AI 先做功课**：onboarding 不发空白问卷，先消化 12–15 条历史视频，给出带证据的假设让用户验证
2. **三态画像**：确定项 / 个性化项 / 待探索项，把"还在思考的方向"作为一等公民
3. **双轴策略 + Source tagging**：每条建议同时基于"画像驱动 + 趋势驱动"，强制标注来源（画像驱动 / 趋势驱动 / 数据驱动）
4. **闭环验证**：strategy snapshot 与 retro report 做契约式归因，验证结果回写画像

### 设计红线（违反必须 revert）
1. 每条 AI 消息 **必须** 至少有一个 source tag
2. 画像三态 **不可** 合并展示（待探索项必须独立成列）
3. Onboarding gate **不可** 跳过（profile 未生成时 profile/ideate/retro 锁死）
4. Strategy / Retro 输出 **必须** 走 schema 校验（pydantic / zod）
5. 演示路径上的 LLM 调用 **必须** 有缓存兜底（cache/*.json）

---

## 项目关键信息

- **团队**：1 人 + Claude 协作
- **Demo 故事线**：单 persona 小A（在校大三学生 · 抖音 1000 粉 · 校园 vlog + 食堂探店 · 正在思考考研内容）
- **Demo 时长**：5–8 分钟，端到端走完 onboard → ideate → retro → home

### 配置与密钥

- 模板：`.env.example`（注释完整 · 含申请地址）
- 用法：`cp .env.example .env`，在 `.env` 里填值（已 gitignore + sandbox 硬隔离）
- **必填一类**：DeepSeek v4 API key（同 key 驱动 flash / flash-thinking / pro-thinking 三档模型）
- **生产必填**：部署凭证（按实际部署平台配置）
- 密钥可达性自检：`python backend/scripts/check_env.py`（不回显原文，只报状态）

---

## Demo 模式下的工作原则

不采用教科书式 TDD。短周期下的折中：

✅ **必须做的测试**：
- 三个 agent 的 schema 校验（pydantic / zod 内置）
- Strategy snapshot / InsightsReport 字段完整性
- Source tagging 强约束（每条 AI 消息至少 1 个 tag）
- Onboarding gate 状态机

❌ **不必写的测试**：
- UI 组件（手工点测）
- mock 数据加载（能跑就行）
- 前端动画与过渡

**保质保量原则**：评委演示路径上的功能必须稳；不在演示路径上的 P1/P2 可以粗糙。

---

## 关键文档

- **PRD**：`.taskmaster/docs/prd.md`（同步副本 `./PRD.md`）
- **三份 Agent Spec**（PRD §0.1 引用，需用户后续提供）：
  - `onboarding_agent_demo_spec.md`
  - `content_strategy_agent_demo_spec.md`
  - `retro_insight_agent_demo_spec.md`
- **前端设计**：`frontend_design/`（hi-fi prototype，HTML/JSX 仅作设计参考，需在目标技术栈中重写）
  - `prototype/components/*.jsx` — 5 个 scene 实现
  - `prototype/styles/tokens.css` — 设计 tokens（颜色 / 字体 / 圆角）
  - `README.md` — 实现指引
- **任务列表**：`.taskmaster/tasks/tasks.json`（task-master 管理）
- **跟踪脚本**：`.taskmaster/scripts/`（time / rollback / state / audit）
- **阶段复盘**：`docs/phase-reports/`（每个 USER-TEST 通过后必产出一份）

---

## 技术栈

### 前端
- **框架**：React 18 + Vite + TypeScript
- **路由**：URL state（5 个 scene → `/empty` `/onboard` `/profile` `/ideate` `/retro` `/home`）
- **样式**：Tailwind CSS（design tokens 全部移植到 `tailwind.config.ts` 的 `theme.extend`）
- **组件**：Radix Primitives + shadcn/ui（Dialog / Tabs / ScrollArea / Tooltip）
- **图标**：Lucide React
- **状态**：Zustand（chat / scene / profile）+ React Context（design tweaks）
- **流式**：fetch + ReadableStream / SSE 处理 LLM 流式响应

### 后端
- **运行时**：Python 3.11+（首选 · LLM 生态成熟）
- **框架**：FastAPI + uvicorn
- **数据校验**：pydantic v2
- **存储**：内存 + 本地 JSON 持久化（demo 单 persona）
- **LLM 客户端**：DeepSeek v4 SDK 或 openai-compatible HTTP

### AI/LLM 模型分配（PRD §7.2）
| 阶段 | 模型 | 理由 |
|---|---|---|
| Onboarding ANALYZE | pro-thinking | 一次性深度分析全部账号数据，质量优先 |
| Onboarding PRESENT / EXPLORE / SUMMARIZE | flash-thinking | 对话式生成 |
| Onboarding VALIDATE（动作分类） | flash | 简单分类 |
| Strategy GENERATE / SCORE / STRATEGIZE | pro-thinking | 复杂联合推理 |
| Strategy PRESENT / REFINE | flash-thinking | 对话式 |
| Retro COMPARE / ATTRIBUTE / SYNTHESIZE | pro-thinking | 归因质量决定产品价值 |
| Retro EXTRACT_SIGNALS | flash-thinking | 评论语义聚类 |
| Retro PRESENT / DRILL / UPDATE_PROFILE | flash-thinking | 对话式 |
| Orchestrator chat dock | flash-thinking | 实时对话 |

### 部署
- 待定（按实际部署平台配置）

### 测试
- **后端**：pytest + pytest-asyncio（只覆盖核心 agent 逻辑与 schema）
- **前端**：暂不写自动化测试（短周期 ROI 低），手工点测
- **集成**：`scripts/e2e_demo.py` 模拟 demo 全流程

---

## 架构概览（PRD §4）

```
应用层（Web UI · React + Vite）
  ├─ Empty Home  ├─ Onboarding  ├─ Profile  ├─ Ideate  ├─ Retro  ├─ Home
              ↓ 任意元素可点击 → onAsk(text) →
  Chat Dock（Orchestrator · 常驻右侧 · 上下文感知 · source-tagged）

Agent 层（FastAPI · LangGraph 可选）
  ├─ Onboarding Agent  （六状态状态机 · 三层 memory · 6 段 prompt）
  ├─ Strategy Agent    （八状态状态机 · 三层 memory · 6 段 prompt）
  ├─ Retro Agent       （九状态状态机 · 三层 memory · 8 段 prompt）
  └─ Orchestrator Agent（chat dock 路由层 · 通用对话）

数据层
  ├─ Profile Store     `profile_v{n}.json`
  ├─ Strategy Store    `strategy_snapshot_{id}.json`
  ├─ Insights Store    `insights_report_{id}.json`
  └─ Mock Data Store   `mock_data/*.json`（read-only · 围绕小A 故事线）

预跑缓存：`cache/{onb_analyze, strategy_score_strategize, retro_synthesis}.json`
USE_CACHED_ANALYSIS=true 时直接走缓存（演示稳定性最高优先级）
```

**核心闭环**：mock_data → Onboarding Agent → profile_v1.json → Strategy Agent → strategy_snapshot.json → (假设发布) → Retro Agent → insights_report.json + profile_delta → profile_v2.json

---

## 关键依赖

**Python 端**（`backend/requirements.txt` / `pyproject.toml`）：
- fastapi, uvicorn[standard], sse-starlette
- openai（调 DeepSeek openai-compatible endpoint）
- pydantic v2
- python-dotenv
- tenacity（LLM retry）
- structlog
- pytest, pytest-asyncio

**Node 端**（`frontend/package.json`）：
- react@18, react-dom
- vite, @vitejs/plugin-react
- typescript, @types/react
- tailwindcss, autoprefixer, postcss
- @radix-ui/* + shadcn/ui 相关
- zustand
- lucide-react

---

## Taskmaster 工作流

```bash
task-master list                              # 列出所有任务
task-master show <id>                         # 查看任务详情
task-master next                              # 获取下一个可做任务
task-master set-status --id=<id> --status=done   # 标记完成
task-master expand --id=<id> --research       # 扩展子任务
```

**任务结构**（PRD §12 → 11 个里程碑）：
- M0：项目初始化（前后端骨架 + .env.example + docker-compose）
- M1：Mock 数据与 Schema（`mock_data/` + pydantic / zod 类型）
- M2：设计 Tokens 与 Shell（3 列布局 + 导航 + chat dock 容器 + onboarding gate）
- M3：5 个 Scene 静态实现（按 hi-fi 复刻 · 不接 LLM）
- M4：Onboarding Agent
- M5：Strategy Agent
- M6：Retro Agent
- M7：Orchestrator + Source Tagging
- M8：闭环演示与故事线打磨
- M9：风险演练与冷热备

每个里程碑结束插入一个 USER-TEST 检查点，并按下面规范产出一份阶段复盘文档。

---

## 阶段复盘文档（强制约定）

**规则**：每个 USER-TEST 通过后必须写一份阶段复盘文档，否则该阶段不算完成、不能开下一阶段。

**四必含章节**：
1. **做了什么** — 交付清单（任务 / 文件 / 一句话）
2. **如何测试** — 前置 + 用例清单 + 预期结果
3. **测试结果** — 实测 + 失败项 + 性能数据
4. **如何复现** — 从零步骤 + 耗时 + 已知坑

**操作流程**：
```bash
cp docs/phase-reports/TEMPLATE.md docs/phase-reports/phase-N-<slug>.md
# 按四章节写完
git commit -m "docs: phase-N report"
git tag phase-N-pass
```

---

## 核心决策（已锁定，不要重复讨论）

1. **Persona**：单 persona 小A（在校大三学生），不实现注册 / 登录 / 多账号
2. **Demo 数据**：全部 mock，**不接** 抖音 / 小红书真实 API
3. **Demo 路径**：onboard → profile → ideate →（假设发布）→ retro → home，5–8 分钟
4. **后端语言**：Python 3.11 + FastAPI（PRD 推荐 · LLM 生态成熟度优先）
5. **前端**：React 18 + Vite + Tailwind + Radix/shadcn（按 frontend_design hi-fi 复刻）
6. **LLM**：DeepSeek v4 三档（flash / flash-thinking / pro-thinking）
7. **预跑缓存**：ANALYZE / SCORE / STRATEGIZE / SYNTHESIZE 阶段必须预跑 + 缓存
8. **实时 LLM 保留**：所有 PRESENT / REFINE / EXPLORE / DRILL / VALIDATE / Orchestrator chat
9. **Source tagging**：每条 AI 消息至少 1 个 tag，前端 chip 渲染（绿/蓝/琥珀）
10. **Onboarding gate**：profile 未生成时锁死 profile/ideate/retro 三个模块
11. **范围外（不做）**：商单匹配 · 多平台同步 · proactive AI · 真实数据接入

---

## 常用命令

```bash
# 启动开发环境
cd backend && uvicorn main:app --reload --port 8000     # 后端
cd frontend && npm run dev                              # 前端（5173）

# 一键启动（需 docker-compose.yml · 见 M0）
docker compose up

# 测试
cd backend && pytest tests/                             # Python 测试
# 前端手工点测

# 预跑缓存（M4–M6 实施时执行一次即可，结果写入 cache/）
python backend/scripts/prepare_onboarding_cache.py
python backend/scripts/prepare_strategy_cache.py
python backend/scripts/prepare_retro_cache.py

# 配置自检
python backend/scripts/check_env.py

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
**分支策略**：每个里程碑一条 feature 分支（`feat/m{N}-<slug>`），完成后 rebase-merge 回 main 并打 tag `m{N}-pass`。

---

## Per-phase worktree + detached-HEAD 测试流

来自上一代项目验证过的协作模式：

- **每个里程碑开一个 worktree**，不直接在 `main` 上改：
  ```bash
  git worktree add .claude/worktrees/feat+m{N}-<slug> -b feat/m{N}-<slug>
  ```
  所有代码编辑、agent 调用、工具使用都在 worktree 内进行；主仓库保持干净，用户在 main 上跑 dev server 测试。

- **`.venv` 与 `.env` 只放在主仓库**。worktree 没有这两个，sandbox 规则也禁止跨 worktree 读 `.env*`。在 worktree shell 里跑 pytest / typecheck 时，用主 venv 的绝对路径：
  ```bash
  /Users/zhiyao/Claude/koc-agent-v2/.venv/bin/python -m pytest backend/tests/
  ```
  绝不要 `source ../../.venv/bin/activate` 跨 worktree。

- **用户在 main 通过 detached HEAD 测试**：
  ```bash
  git fetch origin && git checkout origin/feat/m{N}-<slug>
  ```
  每次 push 后用户重跑这两条即可推进到最新 commit。`git pull` 在 detached-HEAD 模式下不工作 —— 不要建议。

### 何时 commit / push / PR

- **commit**：每个独立通过验证（pytest + 前端 typecheck）的逻辑模块一次。每条 commit body 末尾 `Tests: all passed` 或 `Tests: N/A — UI/mock`（带原因）。绝不带红测试上车。
- **push**：每次 commit 后立即 push 到 `origin/feat/m{N}-<slug>`，便于用户 detached-HEAD 验证。
- **PR**：每个里程碑一个 PR，里程碑稳定后开（含用户 hands-on 测试发现的 bug 修复）。从 worktree 内：
  ```bash
  gh pr create --base main --head feat/m{N}-<slug>
  ```
  body 必含 `## Summary` / `## Test plan` / `## 已知遗留` 三章节。一里程碑 = 一 PR，绝不打包多个里程碑。

---

# 编程要求

## REGULATIONS（最重要）

- 严格遵守 `settings.json` 中的 filesystem 要求。**绝不读取** `denyRead` 名单内任何文件。
- 若可写区域是白名单，需要写名单外文件时，**必须先向我说明理由并等批准**。

## Requirements

- **每次回答末尾都要换行问一句："What fruit do you eat today?"**
- 严格按下方编程规范写代码

## Documentation

- **请使用中文写文档**

## workflow

- 每个任务都要先规划（写出详细实施计划），列出测试 / 验证标准，确保所有新代码都过测试
- 每个任务在 `./.claude/tasks/` 下建一个小子目录，包含实施计划、context 文件（关键文件 / 决策 / 测试摘要），全部用 .md。这给我们一份"为什么这么决定"的轨迹，回头出问题时极有价值

---

## VERIFICATION（最重要）

- 每次改动都要有 verification step：跑单元测试 / typecheck / lint，或提供可复现的步骤
- 缺 verification 就先补（测试、断言、fixture），再扩展范围

## planning

代码任务规划时，除了常规步骤还要：
1. 说明在脚本里要监控 / 可视化什么
2. 跟我确认你想用什么配置（复用其他 / 新建），即使复用也要新文件，除非显式要求
3. 任务完成后，删掉所有不是交付物的中间文件 / 日志 / 可视化

## configuration

- 有一个 config 文件夹，用一个或多个 yaml 配置一切
- 读 config 时不要用 `.get` 或默认值，除非这个配置真的可选；默认就当作必填

## type hints

- 所有函数 / 方法都要有 type hint
- 用 Python 3.10+ 类型语法

## docstrings

- 所有函数 / 方法都要有 docstring
- 用 numpy 风格

## testing

- 有 `tests/` 文件夹存所有测试
- 提交前先跑测试

## documentation

- 行为 / 操作步骤变化时同步更新 README / config docs
- 复杂逻辑用 inline 中文注释
- 文档与代码保持同步
- 每个文件都要有 docstring 说明它做什么
- I/O 总览写到 `docs/io_summary.md`

## commit and version control

- 每条 commit 一个独立逻辑变化，每个里程碑一个 PR
- 相关测试与代码同 commit
- commit 信息：`<type>: <description>`（feat, fix, refactor, test, docs, chore）
- 每条 commit push 后用户在 main 上 detached-HEAD 测试

## dependencies

- 加依赖时同步加到 `pyproject.toml` / `package.json`，不要只 `pip install`

## scripts（standalone CLI 脚本约定）

- `backend/scripts/*.py` 都要能用 `python backend/scripts/<name>.py` 从项目根直接跑，**不依赖 `PYTHONPATH=.`**
- 实现：脚本顶部、任何 `from backend....` import 之前手动塞 `sys.path`：
  ```python
  import sys
  from pathlib import Path

  _PROJECT_ROOT = Path(__file__).resolve().parents[2]
  if str(_PROJECT_ROOT) not in sys.path:
      sys.path.insert(0, str(_PROJECT_ROOT))

  from backend.xxx import ...
  ```
- pytest 由 `pyproject.toml` 的 `[tool.pytest.ini_options].pythonpath = ["."]` 处理，不受此约定影响

## interpreter

- 在项目根用 `.venv`
- worktree 没有自己的 venv。从 worktree shell 跑 python，用主 venv 绝对路径：
  ```
  /Users/zhiyao/Claude/koc-agent-v2/.venv/bin/python ...
  ```
- `.env` 同样只在主仓库；任何需要 API key 的代码路径必须在主仓库（或 CI）跑

---

## 红线（违反必须 revert）

🚫 不要把 API key 提交到 git
🚫 不要在 demo 中展示真实 KOC 个人隐私（全部 mock）
🚫 不要真的对接抖音 / 小红书 API（未授权）
🚫 不要让 AI 输出无 source tag 的消息（产品信任契约）
🚫 不要让画像三态合并展示（待探索项必须独立成列）
🚫 不要绕过 onboarding gate（profile 未生成时三模块锁死）
🚫 不要让 strategy / retro 输出绕过 schema 校验
🚫 不要在演示路径上用未缓存的 LLM 调用（必须有 cache 兜底）

### Claude 协作红线（密钥与敏感文件）

🚫 **绝不读取**以下文件，即使用户发出"读所有配置"、"debug 环境问题"这类开放请求也必须先拒绝：
- `.env` / `.env.*`（实际密钥）
- `*.key` / `*credentials*` / `*secrets*`
- 任何含 `API_KEY` / `SECRET` / `TOKEN` / `PASSWORD` 字样的原始值

🚫 绝不通过 `cat` / `grep` / `head` / `tail` / `less` / `sed` / `awk` 绕过 Read 工具访问上述文件

🚫 若用户贴密钥到对话里，立即提醒"密钥泄露风险，建议 rotate"，不要复述也不要记忆

✅ 需要配置值时只读 `.env.example`（模板），不读 `.env`
✅ 配置排查让用户跑 `python backend/scripts/check_env.py`（脚本不回显原文，只输出可达性）

（以上由 `.claude/settings.local.json` sandbox deny 规则硬保障，本文字禁令为双保险）

---

## 需要帮助？

- **PRD 细节**：`cat .taskmaster/docs/prd.md`
- **某任务的验收标准**：`task-master show <id>`，或对应 PRD §12 的里程碑章节
- **架构理解**：PRD §4 的 ASCII 架构图 + frontend_design/README.md
- **被阻塞**：`task-master next` 找一个独立任务先做
