# 阶段复盘 · M3 · 5 Scene 静态实现

> 通过日期：2026-04-28
> 分支：`feat/m3-scenes`（基于 `feat/m0-bootstrap` worktree，含 M0 / M1 / M2 全部代码）
> 提交范围：`a06de38..1ed38f9`（6 个 commit）

---

## 1. 做了什么

按 hi-fi prototype（`frontend_design/prototype/components/*.jsx`）静态复刻 6 个 view，全部不接 LLM。
Source tagging（PRD §6.7）通过 `_shared/SourceBadge` 在 view 内强制渲染；
chat dock 通过 `useOnAsk` 钩子统一接入（M3 版打 `console.log` 留痕，M7 接 orchestrator 时替换）。

| 任务 | 文件 / 模块 | 一句话说明 |
|---|---|---|
| T16 共用 | `frontend/src/views/_shared/{Sparkline,Score,SourceBadge,SectionTitle,useOnAsk}.{ts,tsx}` | 5 个原子 view primitives；移植自 prototype/primitives.jsx |
| T16 共用 | `frontend/tsconfig.app.json` | 启用 `resolveJsonModule`，view 直接 import seed JSON |
| T16 共用 | `frontend/src/index.css` | 加 `@keyframes beacon-pulse`（onboarding LIVE 信号） |
| T16 | `frontend/src/views/EmptyHomeView.tsx` | profileReady=false 时的 home：760px 居中列 / 三 locked 预览卡 / primary CTA |
| T17 | `frontend/src/views/OnboardView.tsx` | 双列对话面板 + sticky LIVE rail；setTimeout 1.2s 逐条播放 mock 消息；finish CTA 同时 `setProfileReady(true)+setScene('profile')` |
| T17 | `frontend/src/data/onboarding_turns.json` | 围绕小A 故事线（食堂探店主轴 + 考研融合身份 + 待探索项） |
| T18 | `frontend/src/views/ProfileView.tsx` | 头部信息条 + 3 Pillar 网格 + 受众卡 + History strip |
| T18 | `frontend/src/views/profile/PillarColumn.tsx` | 三态列容器（confirm 绿 / person 琥珀 / explore 紫） |
| T18 | `frontend/src/views/profile/AudienceCard.tsx` | 年龄柱图 + 区域 Score + 关键词权重 chip（chip 大小 = 权重） |
| T18 | `frontend/src/views/profile/HistoryStrip.tsx` | 画像更新频次（v0..v6 迷你柱图） |
| T18 | `frontend/src/data/profile_seed.json` | 围绕小A：6 项确定 / 4 项个性化 / 3 项待探索 |
| T19 | `frontend/src/views/IdeateView.tsx` | Idea 输入卡 + 4 ScoreCard + tab 内容 |
| T19 | `frontend/src/views/ideate/{ScoreCard,FitBar,TrendTab,EvalTab,DiffTab,PacingTab}.tsx` | 4 tab 各自的面板组件 |
| T19 | `frontend/src/data/strategy_seed.json` | 围绕 demo idea「考研期间一日三餐怎么吃才能不困」 |
| T20 | `frontend/src/views/RetroView.tsx` | 视频选择 strip + KPI + 策略 vs 实际 + 3 Insight + 评论聚类 |
| T20 | `frontend/src/views/retro/{VideoList,StrategyVsReality,InsightCard,CommentClusters,KPI}.tsx` | 5 个子组件 |
| T20 | `frontend/src/data/insights_seed.json` | 围绕 mock vid_020：完播 39%（-4pp）/ 547 新粉中 83% 是考研画像 |
| T21 | `frontend/src/views/HomeView.tsx` | profileReady=true 时的 home：greeting + 3 action 卡 + 30 天数据卡 |
| T21 | `frontend/src/data/home_summary.json` | hero headline、3 个 action 配置、30 天指标 |
| T21 集成 | `frontend/src/views/SceneRouter.tsx` | 替换全部 stub；保留 profileReady=false 时的 gate 兜底 useEffect |

### 设计红线兑现

- **每条 AI 消息至少 1 个 source tag**：`onboarding_turns.json` 每条 ai 都带 `sources` 数组；strategy 与 insights seed 每条 note/insight 带 `source` 字段渲染为 `<SourceBadge/>`。
- **三态独立成列**：`ProfileView` 里待探索项是单独的 `PillarColumn tone="explore"`，dashed border + 紫色调。
- **Onboarding gate**：`SceneRouter` 保留 useEffect，profileReady=false 时强制 profile/ideate/retro 跳回 home。
- **演示路径全 mock**：M3 阶段无任何 LLM 调用，全部 5 份 seed JSON 静态加载。

---

## 2. 如何测试

### 前置

- [x] M0/M1/M2 已 merge 到本 worktree（依赖 Shell / Chat Dock / SideNav / store / tokens）
- [x] node_modules 已安装（`cd frontend && npm install`）
- [x] backend 不依赖（M3 是纯前端静态）

### 用例清单

| # | 用例 | 操作 | 预期结果 |
|---|---|---|---|
| 1 | typecheck | `cd frontend && npx tsc --noEmit` | 0 errors（exit 0） |
| 2 | build | `cd frontend && npm run build` | 输出 `dist/`，无 error |
| 3 | dev server | `cd frontend && npm run dev` | http://localhost:5173 加载 EmptyHomeView |
| 4 | EmptyHome H1 | 浏览器打开根路径 | 显示「我先帮你建一个 KOC 画像。所有别的事都从它长出来。」 |
| 5 | EmptyHome CTA | 点「开始对话 →」 | scene 切到 onboard，chat dock 自动打开 |
| 6 | Onboard 流式 | 进 onboard 等 5-7 秒 | 消息逐条出现（约 1.2s 间隔），LIVE rail 同步增 ticks |
| 7 | Onboard finish | 等 ticks ≥ 7 出现「已经够了」横条，点「生成画像 →」 | profileReady=true，跳到 profile |
| 8 | Profile 三态 | profile 页面 | 三列：确定项（绿点）/ 个性化项（琥珀）/ 待探索项（紫点 + dashed border） |
| 9 | Profile 探索点击 | 点「考研内容是否作为长期主轴？」卡 | console 输出 `[onAsk] 把「...」这一项展开聊聊`，chat dock 打开 |
| 10 | Profile 受众 | 滚动到受众卡 | 5 段年龄柱图、4 个区域 Score 条、关键词 chip 大小随权重变化 |
| 11 | Ideate tab 切换 | 点 4 个 ScoreCard | 下方面板内容随 tab 切换 |
| 12 | Ideate source tag | 任 tab 的 note/角度 | 每条都有 SourceBadge（画像驱动 / 趋势驱动 / 探索驱动） |
| 13 | Retro 视频切换 | 点视频 strip 的不同卡 | active 高亮，但 KPI 当前用 active_video_id（vid_020）展示 |
| 14 | Retro Insight | Insight 02 的 follow-up chip 「下一条建议继续考研...」 | console 输出 onAsk 文本，chat dock 打开 |
| 15 | Home 切换 | 在 profileReady=true 状态点 nav「首页」 | 显示 HomeView（hero greeting + 3 action 卡 + 30 天数据） |
| 16 | Home action 卡 | 点「复盘这条视频」 | scene 切到 retro |
| 17 | Gate 兜底 | DEV toggle 把 profileReady=false，再点 nav「我的画像」 | nav 项 disabled，无法进入；URL 强切也会被 useEffect 弹回 home |

---

## 3. 测试结果

### 实测

| # | 用例 | 实测 | 状态 |
|---|---|---|---|
| 1 | typecheck | exit 0，无 error | ✅ |
| 2 | build | `dist/index-*.js 262.19kB / gzip 82.28kB`，1.00s built | ✅ |
| 3-17 | 浏览器交互 | **由用户在 USER-TEST 阶段手测**（CLAUDE.md 短周期不写 UI 自动化） | ⏳ 待用户验证 |

### 失败 / 降级项

无失败。已知降级：

- **OnboardView 自动播放消息无暂停 / 重置控件**：刷新页面会重置；M3 阶段不实现暂停/快进。
- **Retro 视频切换不更新 KPI / Insights**：当前 KPI/Insight 数据来自 `active_video_id`（vid_020）固定，切换视频只是高亮 active；M3 未拆分多视频 metrics（mock_data 也只有 vid_020 完整数据）。其它视频是占位。
- **`onAsk` 行为是 console.log + openChat()**：M7 orchestrator 接入时替换为 `appendChatTurn(scene, ...)` + 调对应 agent。
- **`tsconfig.app.json` 加了 `resolveJsonModule`**：原本未启用，view 无法 import JSON。这是单行配置改动，回归风险低。
- **Sparkline 与 Score 用 inline `style={{ background: ... }}`**：因为 tailwind 不能动态生成「带 CSS var 颜色的进度条 width」。这是与 tw-only 的偏离，但保留了 tokens 的可主题化能力。

### 性能数据

| 指标 | 目标 | 实测 |
|---|---|---|
| typecheck | < 5s | ~ 1.5s |
| vite build | < 5s | 1.00s |
| build 产物 | gzip < 100kB | 82.28kB |
| modules transformed | — | 1766 |

---

## 4. 如何复现

### 从零步骤

```bash
# 1) 切到 M3 worktree（在 main 上 detached-HEAD 测试）
cd /Users/zhiyao/Claude/koc-agent-v2
git fetch origin     # 用户 push 后
git checkout origin/feat/m3-scenes

# 2) 装前端依赖（一次）
cd frontend
npm install

# 3) typecheck + build 验证
npx tsc --noEmit          # 期望 exit 0
npm run build             # 期望 ~1s 内 built

# 4) 跑 dev server
npm run dev               # 期望 http://localhost:5173

# 5) 浏览器手测（按用例 4-17 走一遍）
#   - EmptyHome → onboard → 等消息播放 → finish → profile → ideate → retro → home
#   - DEV 按钮（右下角）切换 profileReady 验证 gate
```

### 耗时

| 步骤 | 时长（参考） |
|---|---|
| npm install（首次） | ~ 25 s |
| typecheck | ~ 1.5 s |
| vite build | ~ 1 s |
| 手测全 17 用例 | ~ 8-12 min |

### 已知坑

1. **lucide-react 没有 `Refresh` 图标**：用 `RefreshCw` / `RefreshCcw`。我用了 `RefreshCw`。
2. **`Chart` 在 lucide 里叫 `BarChart3` / `ChartLine`**：HomeView 用 `BarChart3`（条形图）+ `ChartLine`（折线）。
3. **JSON import 需要 `resolveJsonModule`**：tsconfig.app.json 已加。
4. **OnboardView 的逐条释放是 setTimeout**：组件卸载有 cleanup，但没做 React StrictMode 双调用兼容；如果在 dev 看到消息跳动，是 StrictMode 双 mount 导致的（生产 build 不会）。
5. **TrendTab 等组件接受 props 时用了 `_verdict` 转 void**：因为有些 verdict 字段当前没用上但接口预留；TS 严格模式 `noUnusedParameters` 要求显式 void。
6. **未做的 prototype 细节**：EmptyHome 底部「直接导入我的视频」「看一份示例画像」是占位按钮（无 onClick），M8 故事线打磨时再决定是否实现。
7. **HistoryStrip 是 M3 新增**：prototype 里没有完全等价物，是把 PRD §6.3「画像更新历史」做了一个 7 柱迷你版；M4 接 onboarding agent 后需把 ticks 接 runtime_data。

---

## 用户 hands-on 测试清单（USER-TEST · M3 检查点）

请按以下顺序在浏览器手测；任何用例失败请记录到本文件「失败 / 降级项」并打回。

1. EmptyHome 加载 → CTA 文案 + 三 locked 预览 + chat dock 关闭状态
2. 点「开始对话 →」→ scene=onboard，chat dock 打开
3. Onboard 等 5-8 秒，消息逐条出现，右侧 ticks 同步增加（圆点颜色 = 三态）
4. ticks ≥ 7 时「已经够了 · 生成画像 →」CTA 出现
5. 点「生成画像 →」→ profileReady=true，跳到 profile
6. Profile 三列布局正确：确定项 / 个性化项 / 待探索项（紫色 dashed）
7. 点待探索项任一卡 → chat dock 打开（console 有 onAsk log）
8. Profile 受众卡：年龄柱图最高那柱 18-22 是 accent 色
9. 切到 ideate → 4 ScoreCard，热度 74 / 贴合 84 / 差异 78 / 执行 READY
10. 点 4 个 tab，每个面板都有 SourceBadge 可见
11. 切到 retro → 视频 strip + KPI + 策略 vs 实际 + 3 Insight + 4 评论聚类
12. 任一 Insight 的 follow-up chip 可点击打开 chat dock
13. 切到 home（profileReady=true）→ HomeView：headline accent 高亮「83% 是考研画像」
14. 点「复盘这条视频」action 卡 → 跳 retro
15. 右下角 DEV toggle 切 profileReady=false → nav 后 3 项 disabled，强制回 home
16. 重新切 true → 全部解锁

确认通过后：
```bash
git tag m3-pass <last-commit-hash>
```
