# Handoff: Echo — koc成长

## Overview
Echo is an AI agent product for early-stage KOCs (1K–10K followers, mostly student creators on Douyin/Xiaohongshu) that helps them grow by combining four capabilities behind a single conversational orchestrator:

1. **KOC 画像引擎** — a living creator profile with three states: 确定项 (confirmed), 个性化项 (personal/distinctive), 待探索项 (still-being-tested).
2. **选题策略 Copilot** — idea evaluation across four dimensions (热度 / 贴合 / 差异 / 执行) plus pre-publish strategy (hook, pacing, CTA).
3. **复盘 Dashboard** — per-video attribution with strategy-vs-reality compare, finish-rate curve drilldown, and comment-cluster summaries.
4. **AI Orchestrator** — a persistent right-side chat dock that is always context-aware. Every number, every recommendation in the structured UI is a clickable handle into the conversation; every AI suggestion is tagged with its source (画像驱动 / 趋势驱动 / 数据驱动) so nothing is a black box.

The product gates everything behind a first-time **Onboarding** that builds the initial 画像 in a 4-step conversation. Until 画像 is created, the other three modules are locked.

## About the Design Files
The files in `prototype/` are **design references created in HTML/JSX** — high-fidelity prototypes showing intended look and behavior, not production code to copy directly. They run in the browser via in-page Babel transpilation purely for reviewability.

The implementation task is to **recreate these designs in your target codebase's existing environment** (likely React + Tailwind / a component library, but pick what fits your stack) using its established patterns and libraries. If no environment exists yet, React + Tailwind + a headless component library (Radix / shadcn) is a sensible default.

## Fidelity
**High-fidelity (hifi)** — colors, typography, spacing, layout, and interaction details are intentional and should be reproduced closely. Specific hex values, font sizes, radii, and copy are all listed below.

## Screens / Views

### 0. Empty Home (new user, before 画像 exists) — `components/empty-home-view.jsx`
- **Purpose**: Force-funnel new users into 画像 creation. The other three modules are visibly locked.
- **Layout**: Centered max-width 760px column. Three locked preview cards in a 1×3 grid. One large primary CTA card. Soft alternative actions below.
- **Key copy**:
  - H1: "我先帮你建一个 **KOC 画像**。所有别的事都从它长出来。"
  - Body: "画像不是问卷，也不是标签云。它是你这个创作者「是谁、为谁创作、还在试什么」的实时记录…"
  - CTA card: "开始创建你的 KOC 画像 · 一段对话 · 大约 5 分钟 · 你随时可以暂停。"
  - Button: "开始对话 →"
- **Locked cards**: each shows the module's icon, title, and a 1-sentence preview, with a small lock badge top-right and `opacity: 0.62`. Border is dashed.
- **Behavior**: Clicking the primary CTA navigates to onboarding (`scene = "onboard"`), opens the chat dock.

### 1. Onboarding — `components/onboard-view.jsx`
- **Purpose**: Build the initial 画像 in a chat-driven flow. Show the user *in real time* what the AI is recording.
- **Layout**: Two columns — `1fr 360px`. Left = conversation surface (white card, radius 20px, padding 24/28). Right = sticky "LIVE · 我正在构建" rail listing each profile tick the AI has captured, with a colored dot per state (green = confirm, amber = person, purple = explore) and a timestamp.
- **Conversation pattern**: AI alternates between open-ended questions and 3-4 suggestion chips. When the user picks a chip OR types freely, the AI responds with reasoning + sometimes data citations (e.g. "我注意到一件事：你这 12 条视频里，有 3 条提到了考研…平均完播率是 41%；其他校园 vlog 平均是 33%").
- **Top progress strip**: "第 1 步 / 共 4 步" + 4 small bars (active = accent color, inactive = `--bg-3`).
- **Finish CTA**: After ~7 ticks, an accent-tinted bar appears: "已经够了。我已经收集到 7 个信号，可以先生成第一版画像。剩下的我们可以在使用中慢慢补。" + button "生成画像 →".

### 2. Profile (我的画像) — `components/profile-view.jsx`
- **Purpose**: Show the living KOC profile in three columns by state.
- **Layout**: Header strip with avatar, name, fan count, last-update timestamp, and an "Update profile" pill. Below: a 3-column grid of "Pillars" (确定项 / 个性化项 / 待探索项), each a card with kicker label + count + a list of items. The 待探索项 column items are dashed-bordered and clickable — opening them in the right chat as "把这一项展开聊聊".
- **Audience hypothesis card**: full-width, lists the hypothesized audience segments with weighted chips (size+saturation = weight).
- **History strip**: a 7-bar mini chart "画像更新频次".

### 3. Ideate (选题策略) — `components/ideate-view.jsx`
- **Purpose**: Evaluate a specific idea against the user's 画像 + market trends, then produce pre-publish strategy.
- **Layout**: Idea input card at top (composer with optional voice/image). Below: tabs ("评估 / 趋势 / 差异化 / 节奏 + CTA"). Active tab content card below.
  - 评估 tab: 4 metric cards (热度 / 贴合 / 差异 / 执行) each with score + 1-line explanation. Below them, FitBar rows showing each pillar of the 画像 vs this idea.
  - 趋势 tab: 13-day trend chart + supply/demand ratio.
  - 差异化 tab: 3 angle cards.
  - 节奏 tab: timeline (0s, 3s, 12s, 25s, …) with content for each beat + CTA card.
- **All cards are click-to-chat**: clicking any metric or row opens the right dock with "展开「<label>」这个数据".

### 4. Retro (复盘) — `components/retro-view.jsx`
- **Purpose**: Per-video post-mortem with attribution.
- **Layout**:
  - Left: video list (last 5), each row = thumbnail placeholder + title + finish-rate chip ("低于基线" / "超出基线"). Active row highlighted.
  - Main: "Strategy vs Reality" card — two side-by-side panels (发布前假设 dashed, 实际数据 solid) with a divider arrow.
  - Below: 3 Insight cards (each is the unit of attribution — title, body, embedded follow-up question chips).
  - Below: Comment cluster card — 4 themed clusters with sample comments.
- **Click model**: Each Insight card is the entry point into a deeper chat thread.

### 5. Home (returning user) — `components/home-view.jsx`
- **Purpose**: Daily landing. The "今日要做什么" view.
- **Layout**: Hero greeting + headline insight (data point in accent color). Below: 3 "next-action" cards (复盘 / 选题 / 画像 update). Below that: 30-day numbers card (粉丝增长 / 总播放 / 平均完播率 / 已发视频) with sparklines.

## App Shell — `components/shell.jsx`
- **Grid**: `220px 1fr 420px` (left rail / main / right chat dock). When chat is hidden: third column collapses to 0px with a 250ms transition.
- **Left rail**: logo+wordmark, "工作区" header, 4 nav buttons (首页 / 我的画像 / 选题策略 / 复盘), spacer, user card (avatar + 小A · 1,238 粉丝 · 抖音 + settings).
- **Locked nav**: When `locked={true}`, nav items other than 首页 render with `opacity: 0.55`, color `--fg-3`, a small lock icon, and `cursor: not-allowed`. Click handler is no-op.
- **Top bar (sticky)**: kicker label per scene, search button (`⌘K`), and an "打开 AI 助手" button when chat is closed. Background is `rgba(250,249,246,0.85)` with `backdrop-filter: blur(12px)`.

## Right Chat Dock (Orchestrator) — `components/chat-dock.jsx`
- Always context-aware: header shows the current scene's "Orchestrator role" name (e.g. "今天我能帮你做什么", "画像编辑器").
- Each AI message can have:
  - Body text (supports `\n`)
  - Optional **source tags** rendered as a row of small chips below the body. Sources surface where the recommendation came from: `画像驱动` (green), `趋势驱动` (blue), `数据驱动` (amber).
  - Optional **suggestion chips** ("→ 先看那条视频的复盘") that on click submit as a new user turn.
- Composer at bottom: textarea + image button + send button. Footer microcopy: "AI 引用你的画像与最近发布。了解隐私"

## Interactions & Behavior

### Onboarding gate flow
1. New user lands on Empty Home. Chat dock is **closed by default** (focus on the empty state's CTA).
2. User clicks "开始对话" → `scene = "onboard"`, chat dock opens.
3. Onboarding chat shows finish CTA after ~7 ticks. User clicks "生成画像" → `setNewUser(false)`, `scene = "profile"`, chat dock open.
4. After this point, all 4 nav items are unlocked. Returning users see the regular Home.

### Chat-everything model
Any clickable data point in any module passes a string into `onAsk(text)`. This:
- Opens the chat dock if closed.
- Appends a user turn.
- Generates a synthetic AI response (`synthReply` in `app.jsx`) with sources from `synthSources`.

### Source tagging is non-optional
Every AI recommendation in this product must declare its origin. This is the trust mechanism. Implement source tagging as a first-class field on `AiMessage`, not a string suffix.

## State Management

Top-level state (in `App`):
```ts
type AppState = {
  scene: "home" | "profile" | "ideate" | "retro" | "onboard";
  chatOpen: boolean;
  chatLog: Record<Scene, Message[]>;
  tweaks: {
    accent: "lime" | "orange" | "cyan" | "violet";
    density: "compact" | "cozy" | "roomy";
    layout: "split" | "focus";
    newUser: boolean; // gate flag
  };
};

type Message =
  | { role: "system"; text: string }
  | { role: "user"; text: string }
  | { role: "ai"; text: string; sources?: string[]; suggestions?: string[] };
```

`profileReady = !tweaks.newUser`. When `false`, redirect any non-home/non-onboard scene back to home.

In production, replace `tweaks.newUser` with real backend state: `user.profile_id != null`. The same gate pattern applies.

## Design Tokens (`styles/tokens.css`)

### Colors (light theme — warm off-white)
```
--bg-0:        #faf9f6     /* page */
--bg-1:        #ffffff     /* card */
--bg-2:        #f3f1ec     /* nested card */
--bg-3:        #e8e5dd     /* hover / chip */
--bg-inset:    #f7f5f0     /* chat input wells */

--fg-0:        #1a1814     /* primary text */
--fg-1:        #46433c     /* secondary */
--fg-2:        #807c72     /* tertiary / labels */
--fg-3:        #b3afa5     /* hint / placeholder */
--fg-4:        #d9d5cb     /* divider */

--line-0:      rgba(26,24,20,0.06)
--line-1:      rgba(26,24,20,0.10)
--line-2:      rgba(26,24,20,0.18)

--accent:      #5d7a1a     /* deep olive — works on light */
--accent-ink:  #ffffff
--accent-soft: rgba(93,122,26,0.10)
--accent-line: rgba(93,122,26,0.32)

/* Pillar tints — the three画像 states */
--pillar-confirm:  #3d8a3a
--pillar-person:   #b87a1a
--pillar-explore:  #7a4ec4

/* Semantic */
--pos:    #3d8a3a
--neg:    #c44a3a
--warn:   #b87a1a
--info:   #2d6cb4
```

### Typography
```
--font-sans:  "Inter", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui
--font-mono:  "JetBrains Mono", "SF Mono", ui-monospace
--font-serif: "Source Serif 4", "Songti SC", "Noto Serif SC", Georgia
```
- Display: 28–38px, weight 600, letter-spacing -0.02em
- Body: 13–15px, line-height 1.6–1.7
- Eyebrow / kicker labels: 10–11px mono, uppercase, letter-spacing 0.08em, color `--fg-2`

### Radii
`--r-sm 6` `--r-md 10` `--r-lg 14` `--r-xl 20` `--r-2xl 28` `--r-pill 999`

### Spacing
4-based scale: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 56 / 72.

## Recommended Stack for Implementation
- **Framework**: React (Next.js or Vite + React Router)
- **Styling**: Tailwind CSS — port the tokens above to `tailwind.config.ts` as CSS custom properties + Tailwind theme extension.
- **Components**: Radix Primitives + shadcn/ui for buttons, dialogs, scroll areas, tabs.
- **Icons**: Lucide React (the prototype's hand-rolled SVG icon set in `components/primitives.jsx` is named to match Lucide where possible — `Sparkle`, `User`, `Lightbulb`, `Chart` (`BarChart3`), `Brain`, `Lock`, `ArrowRight`, etc.).
- **State**: For the gated routing, plain React + URL state (`/onboarding` vs `/`). For chat: Zustand or React Context.
- **AI**: Stream LLM responses; preserve the source-tagging contract — your prompt must instruct the model to emit `{text, sources[]}` JSON.

## Files
Everything you need is in `prototype/`:
- `Echo - KOC Agent Prototype.html` — main app entry. **Open this first** to see all 5 scenes.
- `Echo - Design Canvas.html` — side-by-side comparison with two alternative layouts (B = conversation-first, C = dashboard-first). Variant A is the recommended/built one.
- `styles/tokens.css` — design tokens (the source of truth for the color/type/radius values listed above).
- `components/` — all React/JSX modules:
  - `app.jsx` — root, scene routing, gate logic, demo nav
  - `shell.jsx` — 3-column layout, nav rail, top bar
  - `chat-dock.jsx` — right-side conversation
  - `primitives.jsx` — icons + Avatar + Score
  - `empty-home-view.jsx` — new-user empty state (the gate)
  - `onboard-view.jsx` — 4-step conversation w/ live profile rail
  - `profile-view.jsx` — 3-pillar 画像
  - `ideate-view.jsx` — idea evaluation + strategy
  - `retro-view.jsx` — per-video post-mortem
  - `home-view.jsx` — daily landing
  - `variations.jsx` — alternative layouts (Conversation-first, Dashboard-first), reference only

## Open Questions for Product
1. **Multi-account / multi-platform**: how does 画像 sync across Douyin + Xiaohongshu accounts owned by the same KOC?
2. **Brand-deal matching**: not designed yet. The user mentioned 商单 as the core monetization goal. Where does this surface — a dedicated module, or an extension of 选题策略?
3. **Proactive AI**: when does the AI initiate (push / inline banner / silent prep)? Trigger conditions need product input.
4. **Privacy**: chat history retention, profile data ownership, export rights.
