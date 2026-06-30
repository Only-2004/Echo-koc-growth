# 阶段复盘 · M5 · Strategy Agent

> 范围限于 M5 后端（agent 八状态 FSM + 三层 memory + service + API + 预跑脚本 + 单元测试）。
> 前端接入（T29）、chat dock REFINE（T30）、端到端 USER-TEST（T31）留给下一阶段。

---

## 1. 做了什么

| 任务 | 文件 / 模块 | 一句话说明 |
|---|---|---|
| T27.1 | `backend/agents/_llm/{__init__,client}.py` | LLMClient ABC + DeepSeekClient（openai SDK）+ MockLLMClient（测试桩，按 marker 消费 fixture 队列） |
| T27.2 | `backend/prompts/strategy/0[1-6,6a].txt` | 6 段 spec prompt + 1 段反馈分类 prompt |
| T27.3 | `backend/agents/strategy/state_machine.py` | 8 状态 StrEnum + 白名单转移表（含 REFINE → SCORE/STRATEGIZE 回退） |
| T27.4 | `backend/agents/strategy/memory.py` | 三层 memory（ShortTerm in-context / Working session / 跨模块由 service 持久化） |
| T27.5 | `backend/agents/strategy/handlers.py` | 各状态 handler；模型档位按 PRD §7.2 |
| T27.6 | `backend/agents/strategy/service.py` | StrategyService 门面：FSM 编排 + cache 兜底 + JSON retry + source-tag 强约束 + snapshot 落库（版本化） |
| T27.7 | `backend/api/strategy.py` | `/submit` (SSE) `/refine` `/snapshot/{id}` |
| T27.8 | `backend/main.py` | startup 注入 service；无 key 降级 MockLLMClient |
| T27.9 | `backend/tests/test_strategy_agent.py` | 5 个核心用例全 Mock |
| T28 | `backend/scripts/prepare_strategy_cache.py` | SCORE+STRATEGIZE 预跑（写好不执行） |

**Commit 链**（feat/m5-strategy 分支，本地，未 push）：

```
6be68cb  feat(m5): LLM client 抽象层
f7dac12  feat(m5): 6 段 prompt 模板
f9a24c5  feat(m5): FSM + 三层 memory + handler
29c4079  feat(m5): StrategyService 门面 + API
e08e9f3  test(m5): 5 个核心用例
cf4afdb  feat(m5): 预跑脚本
```

---

## 2. 如何测试

### 前置

- [x] 主仓库 `.venv` 已含 `pytest`、`pytest-asyncio`（M0 配置）
- [x] mock_data/*.json schema 已通过 M1 校验

### 用例清单

| # | 用例 | 操作 | 预期结果 |
|---|---|---|---|
| 1 | 完整 FSM | 跑 `test_state_machine_full_flow` | 8 状态走通，落盘后 StrategySnapshot pydantic 校验通过 |
| 2 | REFINE 三类 | 跑 `test_refine_classification` | challenge/adjust 不写盘，approve 落 v1 |
| 3 | JSON retry | 跑 `test_score_json_validation` | SCORE 第一次坏 JSON → retry → 主流程继续 |
| 4 | source tag 兜底 | 跑 `test_source_tag_enforcement` | PRESENT 无 tag → retry → fallback `画像驱动`，不抛错 |
| 5 | snapshot 持久化 | 跑 `test_snapshot_persistence` | 文件落盘 + GET 返回字段一致 |

### 跑测试

```bash
cd /Users/zhiyao/Claude/koc-agent-v2/.claude/worktrees/feat+m5-strategy
/Users/zhiyao/Claude/koc-agent-v2/.venv/bin/python -m pytest backend/tests/test_strategy_agent.py -v
/Users/zhiyao/Claude/koc-agent-v2/.venv/bin/python -m pytest backend/tests/ -v
```

---

## 3. 测试结果

### 实测

| # | 用例 | 实测 | 状态 |
|---|---|---|---|
| 1 | test_state_machine_full_flow | passed | ✅ |
| 2 | test_refine_classification | passed | ✅ |
| 3 | test_score_json_validation | passed | ✅ |
| 4 | test_source_tag_enforcement | passed | ✅ |
| 5 | test_snapshot_persistence | passed | ✅ |

```
backend/tests/test_strategy_agent.py  5 passed
全 backend/tests/                     12 passed (含 M0/M1 既有 7 个)
ruff check                            All checks passed
```

### 失败 / 降级项

无失败项。已知降级：

- `submit_idea` 当前一次性 yield 完整 PRESENT 文本（而非 chunk）。原因：service 内部需先拼完整文本做 source tag 校验。前端 SSE 仍能正常拆 event；真"逐字流式"留给 M9 部署阶段优化。
- GENERATE_IDEAS handler 已实现但未挂入 submit_idea（demo 默认 idea-driven）。discovery 模式 API 留给 M8 故事线打磨阶段补充。

### 性能数据

未测真实 LLM 延迟（worktree 无 .env）。MockLLMClient 路径 5 个用例总耗时 0.12s。

---

## 4. 如何复现

### 从零步骤

```bash
# 1) 切到分支
git fetch origin && git checkout origin/feat/m5-strategy   # 或本地 commit cf4afdb

# 2) 跑测试
cd /Users/zhiyao/Claude/koc-agent-v2/.claude/worktrees/feat+m5-strategy
/Users/zhiyao/Claude/koc-agent-v2/.venv/bin/python -m pytest backend/tests/ -v

# 3) 启动服务（在主仓库 .env 配齐 DEEPSEEK_API_KEY 后）
cd /Users/zhiyao/Claude/koc-agent-v2
.venv/bin/uvicorn backend.main:app --reload --port 8000

# 4) （可选）预跑 cache
.venv/bin/python backend/scripts/prepare_strategy_cache.py

# 5) 手动 smoke 测 API
curl -N -X POST http://localhost:8000/api/strategy/submit \
  -H 'content-type: application/json' \
  -d '{"idea_text":"考研期间一日三餐怎么吃才能不困"}'
```

### 耗时

| 步骤 | 时长 |
|---|---|
| 实施 + 调试 + 落 commit | 约 90 分钟 |
| 跑 pytest | 0.3s |
| 跑 ruff | < 1s |

### 已知坑

- worktree 内 sandbox 禁读 `.env`，所以 prepare_strategy_cache.py 必须切到主仓库执行。
- service 当前缓存到内存 `_snapshots / _snapshot_versions`；进程重启后旧 snapshot 文件仍在但 service 不会自动恢复内存索引——`/refine` 调用旧 id 会 404。生产化方案是启动时扫 runtime_data/ 目录恢复，但 demo 单 session 不需要，留作 M9 改造。
- ANALYZE_IDEA 文本未做 source tag 校验（spec 不要求；它只是内部上下文，不直接对用户）。
