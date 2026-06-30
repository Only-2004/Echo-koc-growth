# Retro & Insight Agent 设计规范

## 1. 这个 Agent 做什么

### 1.1 调用时机

三种进入模式：

**Manual-triggered**（用户主动复盘）：用户在视频发布后点击"复盘这条视频"。

**Auto-triggered**（自动复盘）：视频发布后 N 小时（例如 24 至 48 小时）数据相对稳定时，系统自动生成复盘报告并推送给用户。

**Batch-review**（周期复盘）：每周 / 每月对一组近期视频做 meta 级复盘，识别跨视频的共性规律。Demo 不演示此模式。

### 1.2 核心职责

把"已发布的一条视频"转化为一次结构化学习，并把学习沉淀回画像。具体六件事：

* **数据翻译**：把原始指标转化为带参照系的判断（与基线、与同 pillar 历史、与策略预测对照）
* **策略归因**：逐条对照 strategy_snapshot 中的预测与实际表现，识别 hit / miss / partial
* **受众信号挖掘**：从评论中提取真实诉求、隐藏内容方向、关键人群反馈
* **画像反哺**：生成 profile 更新指令，验证或推翻 to_explore 中的假设
* **前瞻建议**：给出下一步选项（迭代 / 转向 / 测试 / 保持），不给处方
* **可对话洞察**：dashboard 上每个元素都是对话入口，用户可向下追问任意一条数据、insight、建议

### 1.3 设计原则

**对不确定性诚实**。一条视频不是结论。Agent 必须明确区分"这个数据点支持了某假设"和"这个假设已被验证"。早期 KOC 最怕被 AI 误导着 over-correct。

**证据可追溯**。每条 insight 必须挂靠到具体的数据片段（指标、drop_off 时点、评论 ID）。

**给选项不下处方**。Suggestions 总是以"你可以考虑 A / B / C"形式呈现，决策权留给用户。

**契约式归因**。COMPARE 阶段严格对照 strategy_snapshot 中 `execution.key_focus` 锚点与各项策略意图（hook / pacing / cta），并以 `baseline_pillar`（同 pillar 历史基线）作为判断 verdict 的参考系，闭环可验证。

## 2. Workflow

```
[LOAD]
  ↓ 加载 profile / strategy_snapshot / video_data / comments / baseline
[COMPARE]                    (在线 LLM 调用)
  ↓ 输出多维 strategy 意图 vs 实际表现对比表（基于 baseline_pillar）
[ATTRIBUTE]                  (在线 LLM 调用)
  ↓ 对显著偏差做归因（drop_off / 受众错配 / 评论矛盾）
[EXTRACT_SIGNALS]            (在线 LLM 调用)
  ↓ 从评论中挖掘受众信号
[SYNTHESIZE]                 (在线 LLM 调用)
  ↓ 组装为 InsightsReport 三层结构（data_cards / insights / suggestions）
[PRESENT]                    (在线 LLM 调用)
  ↓ 自然语言总览呈现
[DRILL]                      (在线 LLM 调用，循环 / 也可从 PRESENT 直接跳过)
  ↓ 用户对任意 card / insight / suggestion 追问
       └─ 用户点"写回画像" → [UPDATE_PROFILE]
[UPDATE_PROFILE]             (在线 LLM 调用)
  ↓ 生成 profile_delta（hypotheses 状态变更、to_explore 更新、新观察）
[FINALIZE]                   (写入 InsightsReport + profile_delta，终态)
```

实际实现见 `backend/agents/retro/state_machine.py`。`PRESENT → UPDATE_PROFILE` 与 `PRESENT → DRILL → UPDATE_PROFILE` 都是合法路径，前者用于评委不追问的快速演示。

### 2.1 各状态职责

**LOAD**：加载本次复盘需要的全部输入（profile_v1、strategy_snapshot、new_video 数据含 metrics 与 drop_off_curve、comments、account_baseline）。

**COMPARE**：构造策略意图 vs 实际表现的对比表。对每个核心指标计算 `value` / `baseline_overall` / `baseline_pillar` / `verdict`（`hit | miss | exceed | within_noise | partial`），verdict 主要参照 `baseline_pillar` 判断（同 pillar 历史基线）。同时单独高亮 strategy 中 `execution.key_focus` 对应的指标卡（`is_key_indicator=true`）。

**ATTRIBUTE**：对所有 verdict ≠ hit 的指标做归因分析。归因来源包括 drop_off_curve 的形状特征、评论中的相关反馈、与历史同类内容的对比、受众画像与目标受众的偏差。

**EXTRACT_SIGNALS**：独立通道挖掘评论。识别三类信号：未被满足的内容请求、新粉群体的画像特征、对策略某条的具体反馈（正向或负向）。

**SYNTHESIZE**：把上述输出组装为 InsightsReport 的三层结构。data_cards 是最外层（原始数据 + 判断），insights 是中层（解释 + 证据链），suggestions 是最内层（行动选项 + 关联 insight）。每个 insight 必须挂载到至少一个 data_card 或 strategy 字段。

**PRESENT**：把 InsightsReport 翻译成自然语言总览。结构按"成功的部分 / 没达预期的部分 / 受众告诉我们的事 / 你可以考虑的下一步"四段。

**DRILL**：循环阶段。用户点击或提及任意 dashboard 元素（card / insight / suggestion），agent 根据元素的 evidence 链路给出深入回答。退出条件：用户主动结束、或连续 2 轮无追问。

**UPDATE_PROFILE**：基于本次复盘生成 profile_delta：哪些 hypotheses 应增加 evidence_for 或 evidence_against、哪些 to_explore 项可以收敛到 personalized 或 confirmed、是否有新观察需要加入 personalized 或 to_explore。生成的 delta 会立即写入 `profile_v{n+1}.json`，前端 chat dock 收到 `profile_updated` 事件后自动拉取新版本。

**FINALIZE**：终态。将 InsightsReport 写入 `runtime_data/insights_report_{id}.json`，profile_delta 已在 UPDATE_PROFILE 阶段直接落盘到新版 profile。Session 结束。

## 3. Memory

### 3.1 Layer 1：会话工作记忆（in-context）

每次 LLM 调用时按当前阶段裁剪：

* current_state
* 与当前阶段相关的输入切片（COMPARE 阶段用 metrics + predicted；ATTRIBUTE 阶段用 deviations + drop_off_curve；DRILL 阶段用被追问元素的 evidence 链路）
* InsightsReport 的当前草稿
* 最近 3 至 4 轮对话（仅 PRESENT 之后阶段使用）

### 3.2 Layer 2：会话持久化记忆

* 全部输入数据（profile / strategy / video / comments / baseline）
* comparison_grid：COMPARE 阶段产出
* attribution_results：ATTRIBUTE 阶段产出
* audience_signals：EXTRACT_SIGNALS 阶段产出
* insights_report_draft：完整草稿
* drill_history：所有追问与回答的轨迹

### 3.3 Layer 3：跨模块共享

* insights_store：所有 commit 的 InsightsReport，按 user_id 与 video_id 索引，支撑 dashboard 渲染
* profile_delta_queue：待应用到 profile 的更新指令，画像引擎按队列消费

## 4. InsightsReport Schema（输出目标）

实际 schema 见 `backend/schemas/insights.py`（pydantic v2，`extra="forbid"`）。

```json
{
  "report_id": "rpt_001",
  "user_id": "user_a_001",
  "video_id": "vid_019",
  "strategy_id": "str_001",
  "profile_version_in": 1,
  "generated_at": "2026-04-27T15:00:00Z",

  "data_cards": [
    {
      "card_id": "dc_completion",
      "metric": "completion_rate",
      "value": 0.39,
      "baseline_overall": 0.46,
      "baseline_pillar": 0.38,
      "verdict": "within_noise",
      "is_key_indicator": false
    },
    {
      "card_id": "dc_follow",
      "metric": "follow_rate",
      "value": 0.022,
      "baseline_overall": 0.012,
      "baseline_pillar": 0.014,
      "verdict": "exceed",
      "is_key_indicator": true
    }
  ],

  "strategy_review": [
    {
      "predicted": "前 3 秒 hook 抓住注意力",
      "actual":    "drop_off_curve 在第 3 秒后保持 0.95，hook 有效",
      "verdict":   "hit",
      "evidence":  [{"type": "drop_off", "ref": "[0:3]"}]
    },
    {
      "predicted": "中段保持 pacing 紧凑",
      "actual":    "第 12 秒讲学习方法时出现明显掉量",
      "verdict":   "miss",
      "evidence":  [{"type": "drop_off", "ref": "[10:14]"}, {"type": "comment", "ref": "cmt_0191"}]
    }
  ],

  "insights": [
    {
      "insight_id": "ins_001",
      "claim": "Hook 设计有效，但中段第 12 秒前后讲学习方法的部分让观众流失",
      "evidence": [
        {"type": "drop_off", "ref": "drop_off_curve[2:4]", "snippet": "0.82 → 0.55"},
        {"type": "comment",  "ref": "cmt_0191",            "snippet": "钩子很好但中间讲学习的部分太长了"}
      ],
      "confidence": "medium",
      "linked_card_ids": ["dc_completion"],
      "linked_strategy_fields": ["execution.pacing"]
    },
    {
      "insight_id": "ins_002",
      "claim": "key_focus 锚点（新粉考研标签占比）显著超出 pillar 基线，验证了'考研内容融合'假设的初步可行性",
      "evidence": [
        {"type": "metric",  "ref": "follow_rate=0.022 vs baseline_pillar 0.014"},
        {"type": "comment", "ref": "cmt_0192", "snippet": "终于有同样在考研的博主了，关注"}
      ],
      "confidence": "low",
      "caveat": "单条视频样本，需要 2 至 3 条同向数据才能升级为 confirmed",
      "linked_card_ids": ["dc_follow"],
      "linked_strategy_fields": ["profile_fit.to_explore_validation"]
    }
  ],

  "audience_signals": [
    {
      "signal_id": "sig_001",
      "signal": "考研同好群体强烈认同'真实考研身份'差异化资产",
      "category": "new_audience_segment",
      "evidence_comments": ["cmt_0192", "cmt_0193"],
      "implication": "未来内容可继续强化'考研中'身份标签，但需控制学习方法讲解占比"
    }
  ],

  "suggestions": [
    {
      "suggestion_id": "sug_001",
      "type": "iterate",
      "content": "保持考研 + 食堂的融合方向，下条视频把学习方法部分压缩到 5 秒内，用 b-roll 替代口播",
      "linked_insight_ids": ["ins_001", "ins_002"],
      "estimated_effort": "low"
    },
    {
      "suggestion_id": "sug_002",
      "type": "test_new",
      "content": "可以测试纯考研日常无食堂场景的视频，看融合是否必要",
      "linked_insight_ids": ["ins_002"],
      "estimated_effort": "medium"
    }
  ],

  "profile_delta": {
    "hypotheses_updated": [
      {
        "hypothesis_id": "h001",
        "delta": "evidence_for +1",
        "new_status": "likely_validated",
        "evidence_summary": "vid_019 follow_rate 0.022 显著高于 pillar 基线 0.014，新粉考研标签占比上升"
      }
    ],
    "to_explore_resolved": [],
    "new_observations": [
      {
        "category": "persona_trait",
        "claim_text": "用户在'真实身份呈现'方面对受众有强吸引力",
        "proposed_state": "personalized",
        "evidence": [{"source_type": "comment", "ref": "cmt_0192"}, {"source_type": "metric", "ref": "follow_rate"}]
      }
    ]
  }
}
```

字段说明：

* `data_cards[].verdict` 取值 `hit | miss | exceed | within_noise | partial`（`Verdict` 枚举），主要参照 `baseline_pillar` 判定，不再依赖 strategy 阶段的 `predicted_range`（已不存在）
* `data_cards[]` 不含 `predicted_range` / `delta_vs_predicted` 字段。Strategy 与 Retro 之间的契约改为：strategy 给一句 `execution.key_focus` 锚点，retro 把对应指标卡 `is_key_indicator=true` 并在 PRESENT 中放大讨论
* `insights[].confidence` 是三档枚举 `"high" | "medium" | "low"`（`ConfidenceLevel`），不是 0–1 浮点。单条视频样本的 insight 必填 `caveat` 说明不确定性
* `audience_signals[].category` 是可选字段，未明确归类时可省略
* `suggestions[].type` 取值 `iterate | test_new | pivot | hold`（早期方案的 `preserve` 已重命名为 `hold`）
* `profile_delta` 是 InsightsReport 的可选顶层字段；在 UPDATE_PROFILE 阶段填充并立即触发 profile_v{n+1} 落盘

注意三层结构的相互链接：每个 insight 通过 `linked_card_ids` 与 `linked_strategy_fields` 显式连接到上层数据；每个 suggestion 通过 `linked_insight_ids` 连接到 insight。这是 dashboard 支持"点击任意元素向下追问"的结构基础。

## 5. Prompts

### 5.1 System Prompt（贯穿全部 LLM 调用）

```
你是一个为早期视频类 KOC 提供发布后复盘的 AI 分析师。
你的目标是把一条已发布的视频转化为一次结构化学习，
让用户理解发生了什么、为什么、以及下一步可以怎么做，
同时把学习沉淀回画像。

你必须遵守以下原则：

1. 对不确定性诚实。一条视频不是结论。明确区分
   "这个数据点支持某假设" 与 "这个假设已被验证"。
   单条样本永远只能让 hypothesis 增加证据，不能直接 confirmed。

2. 证据可追溯。每条 insight 都必须挂靠到具体证据：
   指标 / drop_off 时点 / 评论 ID。绝不输出无证据的判断。

3. 给选项不下处方。所有 suggestion 以"你可以考虑 A / B / C"
   呈现，估计 effort 等级，但不替用户做决定。

4. 契约式归因。严格对照 strategy_snapshot 中各项策略意图（hook / pacing /
   cta / execution.key_focus），并以 baseline_pillar 作为判断 verdict 的参考系。
   策略命中与未命中都如实给出，不做粉饰。

5. 简洁、专业、不油腻。中文回复。
```

### 5.2 COMPARE Prompt

```
任务：构造策略意图与实际表现的多维对比表。

[STRATEGY_SNAPSHOT]
{{strategy_snapshot_json}}

[ACTUAL_METRICS]
{{video_metrics_json}}

[BASELINE]
{{account_baseline_json}}

请严格输出 JSON：

{
  "data_cards": [
    {
      "card_id": "...",
      "metric": "...",
      "value": 数值,
      "baseline_overall": 数值 | null,
      "baseline_pillar": 数值 | null,
      "verdict": "hit | miss | exceed | within_noise | partial",
      "is_key_indicator": true | false
    }
  ],
  "strategy_review": [
    {
      "predicted": "...",
      "actual":    "...",
      "verdict":   "hit | miss | exceed | within_noise | partial",
      "evidence":  [{"type": "...", "ref": "..."}]
    }
  ]
}

判定规则（参照 baseline_pillar）：
* verdict = hit：实际值显著优于同 pillar 基线（提升 ≥ 15%）
* verdict = exceed：实际值远超基线（≥ 30%），与 strategy 的 key_focus 锚点对齐时尤其值得放大
* verdict = miss：实际值显著低于基线（≤ -15%）
* verdict = within_noise：实际值落在基线 ±15% 内，视为正常波动
* verdict = partial：部分指标命中、部分未达
* strategy 中 execution.key_focus 锚点对应的 card 必须 is_key_indicator=true
* strategy_review 至少覆盖 strategy 的 hook / pacing / cta / key_focus 四类意图
```

### 5.3 ATTRIBUTE Prompt

```
任务：对 COMPARE 中所有 verdict ≠ hit 的项做归因分析。

[COMPARISON_GRID]
{{comparison_grid_json}}

[DROP_OFF_CURVE]
{{drop_off_curve}}

[ALL_COMMENTS]
{{comments_json}}

[STRATEGY_DETAILS]
{{strategy_snapshot_json}}

请严格输出 JSON：

{
  "attributions": [
    {
      "metric_or_field": "completion_rate",
      "deviation_summary": "比预测低 0.06，比 pillar 基线略高",
      "primary_cause": "...",
      "evidence": [
        {"type": "drop_off", "ref": "[10:14]", "snippet": "..."},
        {"type": "comment",  "ref": "...",     "snippet": "..."}
      ],
      "confidence": 0.0 至 1.0,
      "alternative_hypotheses": ["..."]
    }
  ]
}

要求：
* 每条归因必须给出至少 1 条 evidence
* 当多个原因同时可能时，主因 + 替代假设都要列出
* 不要做超过证据强度的判断；证据弱时 confidence 必须低
* drop_off_curve 中的明显拐点必须解释
```

### 5.4 EXTRACT_SIGNALS Prompt

```
任务：从评论中挖掘对画像和策略有意义的受众信号。

[ALL_COMMENTS]
{{comments_json}}

[USER_PROFILE_SLICE]
{{relevant_profile_slice}}

[STRATEGY_SNAPSHOT]
{{strategy_snapshot_json}}

请严格输出 JSON：

{
  "audience_signals": [
    {
      "signal_id": "...",
      "signal": "一句话总结",
      "category": "unmet_request | new_audience_segment | strategy_feedback_positive | strategy_feedback_negative",
      "evidence_comments": ["cmt_xxx", ...],
      "implication": "对未来内容或画像的含义"
    }
  ]
}

要求：
* 优先挖掘 likes 数高的评论
* 至少识别 1 条 unmet_request（未被满足的内容请求）
* 至少识别 1 条 strategy_feedback（对策略某条的正向或负向反馈）
* 评论数量少时宁缺毋滥，不要硬凑信号
```

### 5.5 SYNTHESIZE Prompt

```
任务：把 COMPARE / ATTRIBUTE / EXTRACT_SIGNALS 的输出
组装为完整的 InsightsReport。

[DATA_CARDS]
{{data_cards_json}}

[STRATEGY_REVIEW]
{{strategy_review_json}}

[ATTRIBUTIONS]
{{attributions_json}}

[AUDIENCE_SIGNALS]
{{signals_json}}

请严格输出 JSON（InsightsReport 完整 schema，但暂不填 profile_delta，
该字段由后续 UPDATE_PROFILE 阶段填）：

{
  "data_cards": [...],
  "strategy_review": [...],
  "insights": [
    {
      "insight_id": "...",
      "claim": "一句话判断",
      "evidence": [...],
      "confidence": "high | medium | low",
      "caveat": "...（必要时，例如样本量小）",
      "linked_card_ids": [...],
      "linked_strategy_fields": [...]
    }
  ],
  "audience_signals": [...],
  "suggestions": [
    {
      "suggestion_id": "...",
      "type": "iterate | test_new | pivot | hold",
      "content": "...",
      "linked_insight_ids": [...],
      "estimated_effort": "low | medium | high"
    }
  ]
}

要求：
* 每条 insight 至少链接 1 个 data_card 或 strategy_field
* 每条 suggestion 至少链接 1 条 insight
* insight 数量控制在 3 至 5 条，避免信息过载
* suggestion 数量控制在 2 至 4 条，必须覆盖至少一个 iterate 与一个 test_new
* 单条视频样本时，confidence 不得为 high；若为 medium / low 必填 caveat 说明不确定性
```

### 5.6 PRESENT Prompt

```
任务：把 InsightsReport 翻译成对用户友好的自然语言总览。

[INSIGHTS_REPORT]
{{insights_report_json}}

要求：
* 分四段呈现：
  第一段："成功的部分..."（hit 的预测 + exceed 的指标）
  第二段："没达预期的部分..."（miss 的指标 + 主要归因）
  第三段："观众告诉我们..."（audience_signals）
  第四段："你可以考虑的下一步..."（suggestions）
* 每段 2 至 4 句话，引用具体数字或证据
* 强调 key_indicator 的表现
* 单条视频时，结尾提醒"这是单条视频的初步信号，需要再 2 至 3 条
  同向数据才能形成稳定结论"
* 总长度 280 至 380 字
* 结尾对话钩子："想先深入聊哪一块？"
```

### 5.7 DRILL Prompt（循环执行）

```
任务：根据用户对某个 dashboard 元素的追问，给出深入回答。

[INSIGHTS_REPORT]
{{insights_report_json}}

[CLICKED_ELEMENT]
{{element_id_and_type}}

[USER_QUESTION]
{{user_text}}

[RECENT_DRILL_HISTORY]
{{drill_history}}

要求：
* 沿被点击元素的 evidence 链路向下展开
  （card → 链接到 insight；insight → 展开 evidence；
   suggestion → 展开 linked_insights 与 effort 拆解）
* 必要时引用 drop_off_curve 具体时点、具体评论原文
* 用户问"为什么"时给基于 evidence 的解释
* 用户问"如果当时 X 会怎样"时基于已有数据做有限推演，
  并明示"这是推演不是事实"
* 单次回答 100 至 180 字
* 若被追问 insight 的 confidence 为 medium 或 low，必须说明不确定性
```

### 5.8 UPDATE_PROFILE Prompt

```
任务：基于本次复盘结果，生成对 profile 的更新指令。

[INSIGHTS_REPORT]
{{insights_report_json}}

[CURRENT_PROFILE]
{{profile_json}}

[STRATEGY_SNAPSHOT]
{{strategy_snapshot_json}}

请严格输出 JSON：

{
  "hypotheses_updated": [
    {
      "hypothesis_id": "h001",
      "delta": "evidence_for +1 | evidence_against +1",
      "new_status": "pending | pending_more_data | likely_validated | likely_refuted",
      "evidence_summary": "..."
    }
  ],
  "to_explore_resolved": [
    {
      "question_id": "q001",
      "resolution": "...",
      "new_state": "personalized | confirmed | still_open"
    }
  ],
  "new_observations": [
    {
      "category": "persona_trait | life_context | aspiration",
      "claim_text": "...",
      "proposed_state": "personalized | to_explore",
      "evidence": [...]
    }
  ]
}

判定规则：
* 单条视频样本时，hypothesis 最多升级到 likely_validated，
  不能直接 confirmed
* to_explore 项只有在用户对话中明确表态 + 数据支持时才 resolved
* 新观察的 confidence 必须基于 evidence 强度
* 不在 evidence 支持范围内的更新一律不输出
```

## 6. Demo 中实现什么 / Mock 什么

### 6.1 Demo 实现的部分

* 完整的 INGEST → COMPARE → ATTRIBUTE → EXTRACT_SIGNALS → SYNTHESIZE → PRESENT → DRILL → UPDATE_PROFILE → COMMIT 流转
* 至少 1 至 2 轮 DRILL 交互（演示用户对 data_card 与 insight 的追问）
* 最终 InsightsReport JSON 与 profile_delta JSON 的产出
* 与 strategy agent 的衔接（消费 strategy_snapshot.json）
* 与 onboarding 的闭环：profile_delta 显示哪个 to_explore / hypothesis 得到验证

### 6.2 Demo Mock 的部分

| Mock 文件 | 内容 | 来源 |
|---|---|---|
| `profile_v1.json` | 完整 KOC 画像 | onboarding agent 输出 |
| `strategy_snapshot.json` | 发布前策略快照 | strategy agent 输出 |
| `new_video_for_retro.json` | 视频实际指标 + drop_off_curve + 评论 | 预制 |
| `account_baseline.json` | 历史指标基线（按 pillar 分组） | 与 onboarding 共享 |

**预跑固化建议**：

* COMPARE / ATTRIBUTE / EXTRACT_SIGNALS / SYNTHESIZE 四个结构化输出阶段全部预跑并缓存，演示时直接加载，避免现场 LLM 输出方差
* PRESENT、DRILL、UPDATE_PROFILE 实时生成，体现对话感与"AI 在思考"的临场效果
* 准备至少 2 个不同 DRILL 路径（一个针对 data_card，一个针对 insight），demo 时根据现场反应选择

### 6.3 Demo 不涉及的部分

* 真实平台数据接入与抓取
* 跨视频的 batch-review 模式
* 多版本 profile 的合并与冲突解决
* 自动 trigger 的时间窗口控制

### 6.4 演示故事线建议

承接 strategy agent demo 中"考研期间一日三餐"这条视频的策略快照（vid_019）。Demo 中预生成了三条候选视频报告（vid_016 / vid_019 / vid_020），主线选 vid_019，另外两条用作评委追问的备用切换。

第一步，呈现 strategy_snapshot 的核心意图：hook 设计、pacing 安排、execution.key_focus 锚点为"新增粉丝中考研兴趣标签占比"。

第二步，加载 new_video_for_retro 的实际数据：completion 落在 pillar 基线附近（within_noise）、follow_rate 0.022 显著高于 baseline_pillar 0.014（exceed 且是 key_indicator）、drop_off_curve 在第 12 秒前后出现明显下降。

第三步，COMPARE 输出对比表，data_cards 中 dc_follow 标 exceed 且 is_key_indicator=true（与 strategy.key_focus 锚点呼应），dc_completion 标 within_noise，strategy_review 中"中段保持 pacing 紧凑"标 miss。

第四步，ATTRIBUTE 把 pacing miss 归因到中段口播过长，evidence 同时来自 drop_off_curve 形状和评论 cmt_0191。

第五步，EXTRACT_SIGNALS 挖出"考研同好对真实身份强烈认同"的 audience_signal，evidence 是高赞评论 cmt_0192 与 cmt_0193。

第六步，SYNTHESIZE 产出三层结构：两条核心 insight（hook 有效但中段失守、confidence=medium；key_focus 锚点验证融合假设、confidence=low + caveat="单条视频样本"），两条 suggestion（iterate：压缩学习段；test_new：纯考研无食堂版本）。

第七步，PRESENT 用四段式呈现，并明确指出"这是单条视频信号，需要再 2 至 3 条同向数据才能形成稳定结论"。

第八步，用户点击 dc_completion 数据卡，问"为什么 pacing 会被判 miss"，或在 chat dock 输入"第 12 秒为什么掉"。

第九步，DRILL 沿 evidence 链给出回答：drop_off_curve 显示具体下落 + 评论 cmt_0191 印证。

第十步，用户点 retro view 中的"写回画像 →"按钮，触发 UPDATE_PROFILE：profile_delta 把 hypothesis "考研内容能与既有素材融合" 的 evidence_for +1、状态升级到 likely_validated；新增一条 personalized observation "用户在真实身份呈现上有强吸引力"；profile_v{n+1}.json 立刻落盘，前端 chat dock 收到 `profile_updated` 事件后自动拉取并展示新版画像。

第十一步，FINALIZE 写入 InsightsReport，结束。

这条故事线把 onboarding 的 to_explore 项 → strategy 的 to_explore_validation + key_focus → retro 的 hypothesis evidence + key_indicator 验证 形成完整闭环，是整套 demo 最有传播力的一条因果链。它直观回答了"AI 凭什么越用越懂你"这个产品核心问题。
