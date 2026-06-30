# Echo · KOC 成长伙伴

> AI 驱动的视频类 KOC 成长助手 — 画像建立 → 选题策略 → 复盘洞察 闭环

**Tech stack**: React 18 + Vite + Tailwind + Zustand 前端 / FastAPI + DeepSeek v4 后端

---

## 这是什么

Echo 是为早期视频类 KOC（粉丝 1K–10K）设计的 AI 成长伙伴。它不是一个剪辑工具或发布工具——它帮你**理解自己是谁、该做什么内容、以及做得怎么样**。

核心闭环：`onboarding（画像）→ ideate（选题）→ retro（复盘）→ profile 更新`

### 四个核心差异

1. **AI 先做功课** — Onboarding 不发空白问卷，先消化历史视频再提带证据的假设
2. **三态画像** — 确定项 / 个性化项 / 待探索项并存，"还在思考的方向"是一等公民
3. **双轴策略 + Source Tagging** — 每条建议标注来源（画像驱动 / 趋势驱动 / 数据驱动）
4. **闭环验证** — 策略预测 vs 实际数据对比，验证结果回写画像

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- DeepSeek API key（[申请地址](https://platform.deepseek.com/api_keys)）

### 安装

```bash
# 克隆仓库
git clone https://github.com/<your-username>/echo-koc-growth.git
cd echo-koc-growth

# 后端
python -m venv .venv
.venv/Scripts/pip install -e "./backend[dev]"   # Windows
# .venv/bin/pip install -e "./backend[dev]"     # macOS/Linux

# 前端
cd frontend && npm ci && cd ..

# 配置
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 启动

```bash
# 方式 A：分别启动
.venv/Scripts/uvicorn backend.main:app --reload --port 8000   # 后端
cd frontend && npm run dev                                      # 前端 (http://localhost:5173)

# 方式 B：Docker Compose 一键启动
docker compose up
```

### 自检

```bash
.venv/Scripts/python backend/scripts/check_env.py    # 配置检查
.venv/Scripts/python -m pytest backend/tests/        # 后端测试
cd frontend && npx tsc --noEmit && npm run build     # 前端类型检查
```

---

## 项目结构

```
.
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 环境变量配置
│   ├── agents/
│   │   ├── _llm/               # LLM 客户端（含 tenacity 重试）
│   │   ├── _common/            # 共享工具（source tag 校验）
│   │   ├── _fallback/          # 硬编码兜底响应
│   │   ├── onboarding/         # Onboarding Agent（六状态 FSM）
│   │   ├── strategy/           # Strategy Agent（八状态 FSM）
│   │   ├── retro/              # Retro Agent（九状态 FSM）
│   │   └── orchestrator/       # Chat Dock 路由层
│   ├── prompts/                # 各 Agent 的 prompt 模板
│   ├── api/                    # HTTP 路由
│   ├── schemas/                # Pydantic v2 数据模型
│   ├── mock_data/              # Demo 用 mock 数据
│   ├── scripts/                # 缓存预跑 + 环境检查
│   └── tests/                  # pytest 测试
├── frontend/
│   └── src/
│       ├── views/              # 5 个 Scene（EmptyHome/Onboard/Profile/Ideate/Retro/Home）
│       ├── components/         # ChatDock + 共享组件
│       ├── store/              # Zustand 状态管理
│       ├── api/                # SSE 流式 API 调用
│       ├── lib/                # 工具函数 + fallback
│       └── types/              # TypeScript 类型
├── cache/                      # 预跑缓存（ANALYZE/SCORE/STRATEGIZE/SYNTHESIZE）
├── runtime_data/               # Agent 输出（profile/snapshot/insights）
├── docs/                       # 文档 + 阶段复盘
├── scripts/                    # 应急切换脚本
└── .env.example                # 环境变量模板
```

---

## 架构

```
用户输入 → 前端（React + Zustand）
  ↓
Chat Dock（Orchestrator · 常驻右侧 · 上下文感知）
  ↓
Agent 层（FastAPI）
  ├─ Onboarding Agent  ─ 六状态 FSM · 三层 memory
  ├─ Strategy Agent    ─ 八状态 FSM · 三层 memory
  ├─ Retro Agent       ─ 九状态 FSM · 三层 memory
  └─ Orchestrator Agent ─ 路由层 · 通用对话
  ↓
LLM（DeepSeek v4 · 三档：flash / flash-thinking / pro-thinking）
  ↓
数据层
  ├─ Profile Store     (profile_v{n}.json)
  ├─ Strategy Store    (strategy_snapshot_{id}.json)
  ├─ Insights Store    (insights_report_{id}.json)
  └─ Mock Data Store   (mock_data/*.json)
```

---

## LLM 配置

| 阶段 | 模型档位 | 说明 |
|------|---------|------|
| Onboarding ANALYZE | pro-thinking | 深度分析，质量优先 |
| Onboarding PRESENT/EXPLORE/SUMMARIZE | flash-thinking | 对话式生成 |
| Strategy SCORE/STRATEGIZE | pro-thinking | 复杂联合推理 |
| Retro COMPARE/ATTRIBUTE/SYNTHESIZE | pro-thinking | 归因质量决定价值 |
| Orchestrator chat | flash-thinking | 实时对话 |

预跑缓存：`USE_CACHED_ANALYSIS=true` 时直接读 `cache/*.json`，避免 LLM 输出方差。

---

## 弹性机制

- **LLM 重试**：tenacity 指数退避（429/5xx/网络错误，最多 2 次重试）
- **超时控制**：首 token 8s / 总调用 30s
- **Source tag 保底**：每条 AI 消息至少 1 个 tag，无 tag 时自动注入
- **Fallback 模式**：`USE_FALLBACK_ALL=true` 时走 hardcoded 响应
- **应急切换**：`scripts/switch_to_fallback.sh` 5 秒内切到全缓存模式

---

## 技术栈

### 前端
- React 18 + Vite + TypeScript
- Tailwind CSS + Radix Primitives + shadcn/ui
- Zustand（状态管理）
- Lucide React（图标）
- fetch + ReadableStream（SSE 流式）

### 后端
- Python 3.11 + FastAPI + uvicorn
- Pydantic v2（数据校验）
- openai SDK（DeepSeek 兼容接口）
- tenacity（重试）
- structlog（日志）
- pytest + pytest-asyncio（测试）

---

## 文档

- [PRD](./PRD.md) — 产品需求文档
- [CLAUDE.md](./CLAUDE.md) — 开发协作规范
- [Onboarding Agent Spec](./onboarding_agent_demo_spec.md)
- [Strategy Agent Spec](./content_strategy_agent_demo_spec.md)
- [Retro Agent Spec](./retro_insight_agent_demo_spec.md)
- [演示脚本](./docs/demo-script.md)

---

## License

MIT
