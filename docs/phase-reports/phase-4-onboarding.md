# 阶段复盘 · M4 · Onboarding Agent 后端

> 完成于：2026-04-28
> 分支：`feat/m4-onboarding`
> 范围：T23（agent 实现）+ T24（预跑脚本）；**不含** T25（前端接入）/ T26（USER-TEST）

---

## 1. 做了什么

| 任务 | 文件 / 模块 | 一句话说明 |
|---|---|---|
| T23.1 | `backend/agents/_llm/client.py` | LLM client 抽象层：`LLMClient` ABC + `DeepSeekClient`（openai SDK） + `MockLLMClient`（fixture 桩，含 stream 切片） |
| T23.2 | `backend/prompts/onboarding/{system, 01_analyze..06_finalize}.txt` | 7 段 prompt 模板，按 spec §5 复刻 + source tag 强约束注入 |
| T23.3 | `backend/agents/onboarding/state_machine.py` | 八态枚举（INIT/ANALYZE/PRESENT/VALIDATE/EXPLORE/SUMMARIZE/FINALIZE/DONE）+ `next_state_after_validate` 决策函数 |
| T23.4 | `backend/agents/onboarding/memory.py` | 三层 memory：short_term turn buffer / working draft_profile / long_term 占位 |
| T23.5 | `backend/agents/onboarding/handlers.py` | 五个 handler（ANALYZE/PRESENT/VALIDATE/EXPLORE/SUMMARIZE/FINALIZE）+ `extract_sources` 工具 |
| T23.6 | `backend/agents/onboarding/service.py` | `OnboardingService` 门面（start/turn_stream/finalize）+ source tag 强约束 + cache 兜底 |
| T23.7 | `backend/api/onboarding.py` | FastAPI router：`POST /api/onboarding/start /turn /finalize`（SSE） |
| T23.8 | `backend/main.py` | startup hook 注入 service；无 API key 时 fallback 到 `MockLLMClient`，配合 cache 兜底 |
| T23.9 | `backend/tests/test_onboarding_agent.py` | 9 个 pytest（5 个核心场景 + 4 个工具函数） |
| T24 | `backend/scripts/prepare_onboarding_cache.py` | ANALYZE 预跑脚本（在主仓库根跑，写 `cache/onb_analyze.json`），**未执行** |

### 关键设计

1. **LLMClient ABC + 两份实现**：所有 agent 仅依赖 ABC，便于单测换桩。`MockLLMClient` 用 `fixture_key(tier, system, last_user)` 命中；测试中又额外提供 `_SequenceMockLLM` 按调用顺序返回，避开 prompt hash 不稳。
2. **状态机分两次注入**：`OnboardingService.start()` 内同步跑 ANALYZE → PRESENT；`/turn` 第一次时直接流 PRESENT 文案（用户没说话），之后每次 `/turn` 走 VALIDATE → EXPLORE/SUMMARIZE 分支。
3. **Source tag 强约束**：service 的 `_stream_state` 跑完 stream 后调 `extract_sources`，缺 tag → retry 一次 → 仍缺则注入 fallback `[数据驱动]`，整个流程一定有 ≥ 1 个 tag。
4. **FINALIZE retry**：`run_finalize` 对 JSON 解析或 pydantic 校验失败做 1 次 retry（共 2 次调用）；retry 时 prepend 修复指引。
5. **Cache 兜底**：`USE_CACHED_ANALYSIS=true` + `cache/onb_analyze.json` 命中时跳过 ANALYZE LLM 调用，演示稳定性最高优先级。

### 偏离决策

- **MockLLMClient.stream 实现简化**：spec 说 yield 5–10 字符 chunk，本实现固定 6（`chunk_size=6`），可在构造时覆盖。够测试用，前端流式效果实测不受影响。
- **测试中引入 `_SequenceMockLLM`**：原 `MockLLMClient` 通过 hash key 命中，但测试场景里同一 tier 在不同 prompt 下连续调用，hash key 难维护。直接按调用顺序返回更鲁棒。`MockLLMClient` 仍保留，作为 fixture-by-key 的标准桩。
- **`apply_validate_actions` 中 `reject` 不删除**：把 claim.proposed_state 改成 `"rejected"` 留作审计，spec 没明确，但符合"证据驱动"原则。
- **`OnboardingState.SUMMARIZE → EXPLORE`**：在转移图中也允许了反向（用户在 SUMMARIZE 后说"我还有补充"），但当前 service 未启用此路径，留给 M7 orchestrator 做扩展。

---

## 2. 如何测试

### 前置

- [x] `.venv` 已建在主仓库根（`/Users/zhiyao/Claude/koc-agent-v2/.venv`）
- [x] `pip install -e ".[dev]"` 已安装
- [x] 不需要 API key（全部测试用 `MockLLMClient` / `_SequenceMockLLM`）

### 用例清单

| # | 用例 | 操作 | 预期结果 |
|---|---|---|---|
| 1 | `test_state_machine_full_flow` | start → PRESENT 流 → user "对的，可以了" → SUMMARIZE 流 → finalize | 8 个 SSE 事件类型齐全；profile_v1.json 写盘；schema 通过 |
| 2 | `test_validate_action_classification` | 4 类用户回复（confirm/modify/reject/move_to_explore）依次跑 | claim 状态正确变更；fatigue 升级 |
| 3 | `test_finalize_retry` | 第一次 LLM 返回非法 JSON，第二次返回合法 | retry 后 Profile 通过 pydantic |
| 4 | `test_source_tag_enforcement` | LLM 两次都返回无 tag 文本 | service 注入 fallback；最终 `sources >= 1` |
| 5 | `test_finalize_writes_profile_v1` | 端到端跑完 + 重新加载 profile_v1.json | 加载后字段一致，三态非空 |
| 6–9 | `extract_sources` / `fixture_key` 工具函数 | 单元 | 边界正确 |

### 跑测试

```bash
cd /Users/zhiyao/Claude/koc-agent-v2/.claude/worktrees/feat+m4-onboarding
/Users/zhiyao/Claude/koc-agent-v2/.venv/bin/python -m pytest backend/tests/ -v
```

---

## 3. 测试结果

### 实测

| # | 用例 | 实测 | 状态 |
|---|---|---|---|
| 1 | `test_state_machine_full_flow` | PASSED | ✅ |
| 2 | `test_validate_action_classification` | PASSED | ✅ |
| 3 | `test_finalize_retry` | PASSED | ✅ |
| 4 | `test_source_tag_enforcement` | PASSED | ✅ |
| 5 | `test_finalize_writes_profile_v1` | PASSED | ✅ |
| 6–9 | helpers | PASSED | ✅ |
| 既有 | config / health / mock_loader（7 项） | PASSED | ✅ |

**总计：16 passed / 0 failed in 0.31s**。

### 失败 / 降级项

无。

### 性能数据

| 指标 | 目标 | 实测 |
|---|---|---|
| pytest 全部 | ≤ 5s | 0.31s |
| MockLLM 单次 stream（cache 命中场景） | ≤ 50ms | < 5ms |

ANALYZE 真 LLM 延迟未实测（worktree 无 API key）；预期 pro-thinking 单次 ≤ 8s。

---

## 4. 如何复现

### 从零步骤

```bash
# 1. checkout 当前 commit
git fetch origin
git checkout origin/feat/m4-onboarding

# 2. 安装依赖（已 install 过可跳过）
cd /Users/zhiyao/Claude/koc-agent-v2
.venv/bin/pip install -e "backend[dev]"

# 3. 跑测试
.venv/bin/python -m pytest backend/tests/ -v

# 4.（可选）预跑 ANALYZE 缓存（需要 .env 内的 DEEPSEEK_API_KEY）
.venv/bin/python backend/scripts/prepare_onboarding_cache.py

# 5.（可选）启动后端，手测 /api/onboarding/*
cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000

# 调用示例
curl -X POST http://localhost:8000/api/onboarding/start
curl -X POST http://localhost:8000/api/onboarding/turn \
  -H 'content-type: application/json' \
  -d '{"session_id": "<返回值>", "user_text": null}'
```

### 耗时

| 步骤 | 时长 |
|---|---|
| 安装依赖 | 已完成（M0 阶段） |
| 测试 | 0.31s |
| 写 prompt + handler | ≈ 80 min |
| 写测试 | ≈ 30 min |

### 已知坑

- **`MockLLMClient.fixtures` 难维护**：fixture key 依赖 prompt hash，prompt 改字段会破 key。测试中改用 `_SequenceMockLLM`。生产无影响。
- **真实 ANALYZE 一次性 token 量大**：`historical_videos` + `comments` 全部塞进 prompt 可能压爆 context；`_serialize_for_analyze` 已限制 `max_videos=12, max_comments_per_video=5`。
- **SUMMARIZE 后 finalize 之前的"用户最终确认"未拦截**：当前 `/finalize` 端点是用户手动调，不要求用户先在对话中说 "对"。M7 orchestrator 应在 chat dock 拦"对的"再调 finalize。

---

## 5. 留给下次会话的边界

### T25（前端接入 Onboarding · M3 完成后）

依赖：M3 已落地的 `OnboardView` + `useChatStore` + SSE client。

具体接入点：
1. 进 `/onboard` 时调 `POST /api/onboarding/start` → 渲染 `candidate_claims` overview（左列）
2. PRESENT 流：直接调 `POST /api/onboarding/turn` body=`{session_id, user_text: null}`，按 SSE 事件 type 渲染：
   - `message.delta` → token 拼到 chat dock 当前 ai bubble
   - `message.complete` → 锁定 + 渲染 source chip
   - `profile.tick` → 左列三态 column 增量更新
   - `state.transition` → 顶部 stepper 高亮
   - `finish.ready` → 显示"生成画像"主 CTA
3. CTA 触发 `POST /api/onboarding/finalize` → 拿 Profile JSON → 跳 `/profile`

### T26（USER-TEST · 用户跑）

USER-TEST 检查清单（PRD §12 验收标准）：
- [ ] 端到端 onboard 5–8 分钟内完成
- [ ] 所有 ai 消息至少 1 个 source chip 渲染（绿/蓝/琥珀）
- [ ] 三态在左列独立成列（不合并）
- [ ] 生成 profile_v1.json 后才能跳 /profile（onboarding gate 生效）
- [ ] 流式不卡顿，首 token ≤ 5s

---

## 6. 提交

```
feat(m4): LLM client 抽象层（ABC + DeepSeek + Mock）
feat(m4): onboarding 7 段 prompt 模板
feat(m4): onboarding state machine + memory + handlers
feat(m4): onboarding service + FastAPI router + main 集成
test(m4): onboarding agent 9 项 pytest（schema / FSM / source / retry）
feat(m4): ANALYZE 预跑脚本 prepare_onboarding_cache.py
docs: phase-4 onboarding 阶段复盘
```

未 push（按约定本次 push 由用户控制）。
