# 阶段复盘 · M6 · Retro Insight Agent

> M6 后端 Retro Insight Agent 实现完成。前端接入（T34）、DRILL/UPDATE_PROFILE 前端
> 显式化（T35）、USER-TEST 闭环（T36）留给下一阶段。
> 文件名：`phase-6-retro.md`，对应 tag `m6-retro-pass`（合并到 main 后再打）。

---

## 1. 做了什么

> 交付清单。每行一个：[任务编号] - [文件 / 模块] - [一句话]。

| 任务 | 文件 / 模块 | 一句话说明 |
|---|---|---|
| T32 | `backend/agents/_llm/client.py` | LLMClient ABC + DeepSeekClient（openai-compatible）+ MockLLMClient（fixture 驱动 · M4/M5/M6 共享） |
| T32 | `backend/agents/retro/state_machine.py` | 九状态 FSM：LOAD → COMPARE → ATTRIBUTE → EXTRACT_SIGNALS → SYNTHESIZE → PRESENT → DRILL → UPDATE_PROFILE → FINALIZE |
| T32 | `backend/agents/retro/memory.py` | 三层 memory（inputs / 中间产物 / DRILL 4 条 deque buffer） |
| T32 | `backend/agents/retro/handlers.py` | 8 段 prompt 调用 + JSON 校验 + source-tag 强约束 + retry/fallback |
| T32 | `backend/agents/retro/profile_merger.py` | ProfileDelta → Profile_v2 合并器（add_evidence / promote / new_observations / audit_entries · 单条视频禁 graduated） |
| T32 | `backend/agents/retro/service.py` | RetroService 门面（缓存兜底 / Session / 写盘 / FINALIZE schema 校验） |
| T32 | `backend/prompts/retro/01–08_*.txt` | 8 段 prompt（按 spec §5 + source-tag chip 占位约束） |
| T32 | `backend/api/retro.py` | 4 个端点：`POST /load/{video_id}` SSE、`POST /drill` SSE、`POST /update-profile` JSON、`GET /report/{id}` |
| T32 | `backend/main.py` | 挂载 RetroService 到 `app.state` + include retro router |
| T32 | `backend/schemas/insights.py` | `AudienceSignal.category` 字段补齐（4 类 Literal） |
| T32 | `backend/tests/test_retro_agent.py` | 8 个测试，全部 MockLLMClient |
| T33 | `backend/scripts/prepare_retro_cache.py` | COMPARE+ATTRIBUTE+EXTRACT_SIGNALS+SYNTHESIZE 预跑脚本（**未执行**，留主仓库 venv 跑） |

---

## 2. 如何测试

### 前置

- [x] 主仓库 `/Users/zhiyao/Claude/koc-agent-v2/.venv` 已就绪
- [x] 必填环境变量已配置（仅运行 `prepare_retro_cache.py` 需要；pytest 全部走 mock，不需要）
- [ ] T34 之后：前端 dev server `npm run dev`

### 用例清单

| # | 用例 | 操作 | 预期结果 |
|---|---|---|---|
| 1 | 后端 pytest 全套 | `pytest backend/tests/` | 15 passed（含 8 个 retro + 7 个原有） |
| 2 | FastAPI 路由注册 | `python -c "from backend.main import create_app; ..."` | 4 个 `/api/retro/*` 出现 |
| 3 | 9 状态 FSM 全流程 | `pytest test_retro_agent.py::test_state_machine_full_flow` | LOAD→…→FINALIZE 走通，InsightsReport 通过 schema |
| 4 | DRILL evidence 链 | `pytest ::test_drill_evidence_chain` | 输出含 `cmt_201` 与时点引用 |
| 5 | SYNTHESIZE retry | `pytest ::test_synthesize_json_validation` | 第一次缺字段 → 第二次成功 |
| 6 | profile v1 → v2 | `pytest ::test_update_profile_v1_to_v2` | h001 supported + persona_trait 新增 + audit-log 含 version-bump |
| 7 | source-tag fallback | `pytest ::test_source_tag_enforcement` | 两次无 chip → fallback 兜底「（系统兜底）」 |
| 8 | 4+ cluster | `pytest ::test_audience_signals_clustering` | clusters 长度 ≥ 4 |

---

## 3. 测试结果

### 实测

| # | 用例 | 实测 | 状态 |
|---|---|---|---|
| 1 | 后端 pytest 全套 | `15 passed in 0.25s` | ✅ |
| 2 | FastAPI 路由注册 | `/api/retro/{drill, load/{video_id}, report/{report_id}, update-profile}` 全部出现 | ✅ |
| 3 | 9 状态 FSM 全流程 | passed（含 PRESENT chunk + DRILL chunk + InsightsReport schema 重 validate） | ✅ |
| 4 | DRILL evidence 链 | passed | ✅ |
| 5 | SYNTHESIZE retry | passed（mock 客户端记录到 2 次 synthesize 调用） | ✅ |
| 6 | profile v1 → v2 | passed | ✅ |
| 7 | source-tag fallback | passed（fallback 文本 `（系统兜底）` 生效） | ✅ |
| 8 | 4+ cluster | passed | ✅ |

### 失败 / 降级项

- 无失败项。
- **降级 1（明确）**：`backend/api/retro.py` 中 `_stub_profile` / `_stub_strategy_snapshot`
  暂时硬编码，等 M4 / M5 完成后改为读 `runtime_data/profile_v1.json` 与
  `runtime_data/strategy_snapshot_*.json`。Demo 路径下不影响核心闭环。
- **降级 2（明确）**：预跑脚本未执行（CLAUDE.md 红线 + 主仓库才有 `.env`）。
  脚本已通过 `python -c "import ..."` 静态校验过 import 路径。

### 性能数据

| 指标 | 目标 | 实测 |
|---|---|---|
| 后端 pytest 全套 | < 5s | 0.25s |
| 9 状态 FSM mock 跑完 | < 1s | mock 同步路径 < 50ms |
| LLM 首 token | ≤ 5s（生产） | 待 prepare_retro_cache 实跑后填 |

---

## 4. 如何复现

### 从零步骤

```bash
# 步骤 1：在主仓库切到 worktree 当前 commit
cd /Users/zhiyao/Claude/koc-agent-v2
git fetch origin
git checkout origin/feat/m6-retro

# 步骤 2：跑测试（venv 在主仓库）
.venv/bin/python -m pytest backend/tests/ -v

# 步骤 3：（可选）启动后端，观察 /api/retro/load/{video_id} SSE
cd backend && uvicorn main:app --reload --port 8000
# 在另一终端：
curl -N -X POST http://localhost:8000/api/retro/load/vid_020

# 步骤 4：（可选）预跑缓存（需有真实 DEEPSEEK_API_KEY）
.venv/bin/python backend/scripts/prepare_retro_cache.py
```

### 耗时

| 步骤 | 时长 |
|---|---|
| 8 个新 prompt 文件 | 20 分 |
| LLMClient + Mock | 30 分 |
| state_machine + memory + handlers + profile_merger | 60 分 |
| service + API + main 集成 | 30 分 |
| pytest 编写与调通 | 40 分 |
| schema 修补（AudienceSignal.category） | 5 分 |

### 已知坑

- `AudienceSignal.category` 是 M6 才发现 schema 缺字段，已在本里程碑补齐，
  下游 strategy/onboarding 可能需要同步（只是新增可选字段，不破坏向下兼容）。
- `_stub_profile` 与 `_stub_strategy_snapshot` 在 M4/M5 落地后必须替换为读盘版本，
  否则 closed-loop 演示将断在 retro 这一环之前。
- DeepSeekClient 懒加载 openai SDK；测试环境若安装了 openai 仍 OK，
  生产环境务必通过 `pip install -e .` 把 `openai>=1.30` 一起装上。
- `drill_history` deque 容量 4，与 spec 中"最近 3-4 轮"对齐；超出会自动裁剪。
- profile_merger 主动追加一条 `version bump v{n} -> v{n+1}` 的 AuditLogEntry，
  spec 没有明确，但保持画像版本可追溯。

### T34 / T35 / T36 边界（留给下次）

- **T34**：前端 `/retro` scene 接入 SSE，渲染 InsightsReport 的 4 段式 Present。
- **T35**：DRILL 与 UPDATE_PROFILE 的前端按钮 + chip 渲染（绿/蓝/琥珀）+ profile_v2 写盘后的 visual diff。
- **T36**：USER-TEST 走通完整闭环（mock_data → onboard → strategy → retro → profile_v2），
  通过后回到本文档补 §3 性能数据，并打 `m6-retro-pass`。
