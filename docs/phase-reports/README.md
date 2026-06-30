# 阶段复盘文档（phase-reports）

每个 USER-TEST 通过后必产出一份，否则该阶段不算完成、不能开下一阶段。

## 流程

```bash
cp docs/phase-reports/TEMPLATE.md docs/phase-reports/phase-N-<slug>.md
# 按四章节填写：做了什么 / 如何测试 / 测试结果 / 如何复现
git add docs/phase-reports/phase-N-<slug>.md
git commit -m "docs(phase-N): <slug> 复盘"
git tag m{N}-pass
```

## 索引

| 阶段 | 文件 | 状态 |
|---|---|---|
| M0 项目初始化 | `phase-0-bootstrap.md` | ⏳ 待写 |
| M1 Mock 数据 + Schema | `phase-1-mock-schema.md` | ⏳ |
| M2 设计 Tokens + Shell | `phase-2-shell.md` | ⏳ |
| M3 5 Scene 静态 UI | `phase-3-scenes.md` | ⏳ |
| M4 Onboarding Agent | `phase-4-onboarding.md` | ⏳ |
| M5 Strategy Agent | `phase-5-strategy.md` | ⏳ |
| M6 Retro Agent | `phase-6-retro.md` | ⏳ |
| M7 Orchestrator + Source Tagging | `phase-7-orchestrator.md` | ⏳ |
| M8 闭环演示打磨 | `phase-8-demo.md` | ⏳ |
| M9 部署 | `phase-9-deploy.md` | ⏳ |
| M10 风险演练 | `phase-10-resilience.md` | ⏳ |

## 写作要点

- 每章不要省略，宁可写"无"也别留空
- 测试结果中的失败项要写清原因与缓解方案
- 复现步骤要让"另一台机器、另一个人"能照抄
- 性能数据要尽量量化（毫秒、字节、行数）
