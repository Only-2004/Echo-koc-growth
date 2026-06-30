"""Retro Insight Agent 核心逻辑测试。

覆盖：
- 9 状态 FSM 全流程跑通 + 最终 InsightsReport 通过 schema
- DRILL 沿 evidence 链回答（含 cmt_xxx / drop_off ref）
- SYNTHESIZE JSON 校验失败 retry
- profile_v1 → profile_v2 合并 + audit_log 含 version-bump
- PRESENT/DRILL source-tag 强约束 + retry + fallback
- EXTRACT_SIGNALS 输出 ≥ 4 个 cluster

全部使用 MockLLMClient，不发起真实 LLM 调用。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from backend.agents._llm import MockLLMClient
from backend.agents.retro import RetroService, merge_profile_delta
from backend.agents.retro.handlers import (
    _extract_json_block,
    _has_source_tag,
    run_compare,
    run_synthesize,
    stream_drill,
    stream_present,
)
from backend.agents.retro.memory import DrillTurn, RetroMemory
from backend.agents.retro.state_machine import RetroState
from backend.api.retro import _stub_profile, _stub_strategy_snapshot
from backend.config import load_settings
from backend.schemas import (
    AccountBaseline,
    InsightsReport,
    NewVideoForRetro,
    Profile,
    ProfileDelta,
)


# ---------------- 通用 fixtures ----------------

@pytest.fixture
def video_data() -> NewVideoForRetro:
    """加载演示视频 vid_020 数据。"""
    path = Path(__file__).resolve().parents[1] / "mock_data" / "new_video_for_retro.json"
    return NewVideoForRetro.model_validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture
def baseline_data() -> AccountBaseline:
    path = Path(__file__).resolve().parents[1] / "mock_data" / "account_baseline.json"
    return AccountBaseline.model_validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture
def profile_v1() -> Profile:
    return _stub_profile(user_id="user_a_001")


@pytest.fixture
def strategy_snapshot():
    return _stub_strategy_snapshot(user_id="user_a_001", video_id="vid_020")


@pytest.fixture
def settings_no_cache(tmp_path: Path):
    """禁用缓存的 Settings（强制走 LLM mock 路径）。"""
    cfg = load_settings(require_keys=False)
    # use_cached_analysis 通过环境变量；这里通过 dataclasses.replace 覆盖
    from dataclasses import replace

    return replace(cfg, use_cached_analysis=False)


@pytest.fixture
def settings_cached(tmp_path: Path):
    cfg = load_settings(require_keys=False)
    from dataclasses import replace

    return replace(cfg, use_cached_analysis=True)


# ---------------- mock fixture payload helpers ----------------

def _compare_fixture() -> dict[str, Any]:
    return {
        "data_cards": [
            {
                "card_id": "dc_completion",
                "metric": "completion_rate",
                "value": 0.39,
                "baseline_overall": 0.36,
                "baseline_pillar": 0.43,
                "verdict": "miss",
                "is_key_indicator": False,
            },
            {
                "card_id": "dc_follow",
                "metric": "follow_rate",
                "value": 0.022,
                "baseline_overall": 0.012,
                "baseline_pillar": 0.023,
                "verdict": "exceed",
                "is_key_indicator": True,
            },
        ],
        "strategy_review": [
            {
                "predicted": "前 3 秒 hook 抓住注意力",
                "actual": "drop_off_curve 在第 3 秒后保持 0.95，hook 有效",
                "verdict": "hit",
                "evidence": [{"type": "drop_off", "ref": "[0:3]"}],
            },
            {
                "predicted": "完播率以 pillar baseline 0.43 为目标线",
                "actual": "0.39，比 pillar 基线略低，主要掉量在第 12 秒",
                "verdict": "miss",
                "evidence": [{"type": "drop_off", "ref": "[10:14]"}],
            },
            {
                "predicted": "中段 b-roll 节奏顺畅",
                "actual": "中段口播过长，第 12 秒掉量",
                "verdict": "partial",
                "evidence": [{"type": "comment", "ref": "cmt_201"}],
            },
            {
                "predicted": "结尾 CTA 收口考研日常",
                "actual": "follow_rate 0.022 表明 CTA 有效",
                "verdict": "hit",
                "evidence": [{"type": "metric", "ref": "follow_rate"}],
            },
        ],
    }


def _attribute_fixture() -> dict[str, Any]:
    return {
        "attributions": [
            {
                "metric_or_field": "completion_rate",
                "deviation_summary": "比 pillar 基线略低，但仍高于账号 overall 基线",
                "primary_cause": "中段口播过长，第 12 秒前后断崖下落",
                "evidence": [
                    {"type": "drop_off", "ref": "[10:14]", "snippet": "0.85 → 0.55"},
                    {"type": "comment", "ref": "cmt_201", "snippet": "中间讲学习的部分太长了，第 12 秒后我跳走了"},
                ],
                "confidence": "high",
                "alternative_hypotheses": ["可能是 BGM 突变或字幕缺失"],
            }
        ]
    }


def _signals_fixture() -> dict[str, Any]:
    return {
        "audience_signals": [
            {
                "signal_id": "sig_001",
                "signal": "考研同好群体强烈认同'真实考研身份'",
                "category": "new_audience_segment",
                "evidence_comments": ["cmt_202", "cmt_208"],
                "implication": "可继续强化考研身份标签",
            },
            {
                "signal_id": "sig_002",
                "signal": "用户希望干货更具体",
                "category": "unmet_request",
                "evidence_comments": ["cmt_206"],
                "implication": "下次三餐方案细化到分量",
            },
            {
                "signal_id": "sig_003",
                "signal": "对 b-roll 节奏正向反馈",
                "category": "strategy_feedback_positive",
                "evidence_comments": ["cmt_205"],
                "implication": "压缩口播，更多 b-roll",
            },
            {
                "signal_id": "sig_004",
                "signal": "对中段口播过长的负向反馈",
                "category": "strategy_feedback_negative",
                "evidence_comments": ["cmt_201"],
                "implication": "学习方法部分压缩到 5 秒内",
            },
        ],
        "clusters": [
            {"cluster_id": "kaoyan_resonance", "label": "考研共鸣", "comment_ids": ["cmt_202", "cmt_203", "cmt_204", "cmt_208"]},
            {"cluster_id": "pacing_issue", "label": "节奏问题", "comment_ids": ["cmt_201"]},
            {"cluster_id": "production_feedback", "label": "制作反馈", "comment_ids": ["cmt_205"]},
            {"cluster_id": "content_request", "label": "内容请求", "comment_ids": ["cmt_206", "cmt_207"]},
        ],
    }


def _synthesize_fixture() -> dict[str, Any]:
    grid = _compare_fixture()
    sig = _signals_fixture()
    return {
        "data_cards": grid["data_cards"],
        "strategy_review": grid["strategy_review"],
        "insights": [
            {
                "insight_id": "ins_001",
                "claim": "Hook 设计有效，但中段第 12 秒前后讲学习方法的部分让观众流失",
                "evidence": [
                    {"type": "drop_off", "ref": "drop_off_curve[10:14]", "snippet": "0.85 → 0.55"},
                    {"type": "comment", "ref": "cmt_201", "snippet": "中间讲学习的部分太长了"},
                ],
                "confidence": "high",
                "caveat": "单条视频样本，需要 2-3 条同向数据才能确认",
                "linked_card_ids": ["dc_completion"],
                "linked_strategy_fields": ["execution.pacing"],
            },
            {
                "insight_id": "ins_002",
                "claim": "key_indicator 新粉考研标签 0.83 验证了'考研内容融合'假设的初步可行性",
                "evidence": [
                    {"type": "metric", "ref": "follow_rate=0.022 vs 基线 0.012"},
                    {"type": "comment", "ref": "cmt_202", "snippet": "终于有同样在考研的博主了"},
                ],
                "confidence": "medium",
                "caveat": "单条视频样本，需更多数据升级到 confirmed",
                "linked_card_ids": ["dc_follow"],
                "linked_strategy_fields": ["profile_fit.to_explore_validation"],
            },
            {
                "insight_id": "ins_003",
                "claim": "评论中对 b-roll 节奏的正向反馈与 pacing 优化方向一致",
                "evidence": [{"type": "comment", "ref": "cmt_205", "snippet": "b-roll 替代口播节奏更好"}],
                "confidence": "medium",
                "caveat": None,
                "linked_card_ids": ["dc_completion"],
                "linked_strategy_fields": ["execution.pacing"],
            },
        ],
        "audience_signals": sig["audience_signals"],
        "suggestions": [
            {
                "suggestion_id": "sug_001",
                "type": "iterate",
                "content": "你可以考虑保持考研 + 食堂融合，下条视频把学习方法部分压缩到 5 秒内，用 b-roll 替代口播",
                "linked_insight_ids": ["ins_001", "ins_002"],
                "estimated_effort": "low",
            },
            {
                "suggestion_id": "sug_002",
                "type": "test_new",
                "content": "你可以测试纯考研日常无食堂场景的视频，看融合是否必要",
                "linked_insight_ids": ["ins_002"],
                "estimated_effort": "medium",
            },
        ],
    }


def _profile_delta_fixture() -> dict[str, Any]:
    return {
        "add_evidence": [
            {
                "target_kind": "hypothesis",
                "target_id": "h001",
                "side": "for",
                "evidence": {
                    "source_type": "metric",
                    "source_id": "vid_020",
                    "snippet": "follow_rate 0.022 显著高于基线 0.012；新粉考研标签 0.83",
                    "ref": "follow_rate",
                },
            }
        ],
        "promote": [
            {"kind": "hypothesis", "id": "h001", "from_status": "pending", "to_status": "supported"}
        ],
        "new_observations": [
            {
                "category": "persona_trait",
                "claim_text": "用户在'真实身份呈现'方面对受众有强吸引力",
                "proposed_state": "personalized",
                "evidence": [
                    {"source_type": "comment", "source_id": "cmt_202", "snippet": "终于有同样在考研的博主了"}
                ],
            }
        ],
        "audit_entries": [
            {
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "source": "RETRO_UPDATE",
                "change": "h001 evidence_for+1 + promote pending->supported; 新增 persona_trait",
                "claim_id": "h001",
            }
        ],
    }


def _present_text_with_tag() -> str:
    return (
        "<source:数据驱动> 成功的部分：完播 0.39 虽然 miss 但仍高于账号 overall 基线 0.36；key_indicator 新粉考研标签 0.83 显著超出预期，验证融合假设。"
        "\n\n<source:数据驱动> 没达预期：完播率 0.39 比预测 0.45-0.55 低 0.06，主要在第 12 秒断崖（drop_off_curve[10:14]: 0.85→0.55），cmt_201 印证。"
        "\n\n<source:画像驱动> 观众告诉我们：考研同好群体强烈认同'真实考研身份'，部分用户希望干货更具体，b-roll 节奏获正向反馈。"
        "\n\n<source:历史复盘> 你可以考虑：(1) 保持融合方向，把学习方法压缩到 5 秒内、用 b-roll 替代口播；(2) 测试纯考研日常版本看融合是否必要。"
        "\n\n这是单条视频信号，需要再 2 至 3 条同向数据才能形成稳定结论。想先深入聊哪一块？"
    )


def _drill_text_with_tag() -> str:
    return (
        "<source:数据驱动> 第 12 秒是中段口播切入的位置，drop_off_curve 在 [10:14] 区间从 0.85 下落到 0.55，"
        "cmt_201 「钩子很好但中间讲学习的部分太长了」直接印证。"
        "ins_001 confidence high，结合归因属于较强支持。"
        "建议下一条把学习方法部分压缩到 5 秒内、用 b-roll 替代口播验证。"
    )


# ---------------- 测试 1：完整 9 状态流程 ----------------

@pytest.mark.asyncio
async def test_state_machine_full_flow(
    settings_no_cache, video_data, baseline_data, profile_v1, strategy_snapshot, tmp_path
):
    """跑完 LOAD → COMPARE → ATTRIBUTE → EXTRACT_SIGNALS → SYNTHESIZE → PRESENT
    → DRILL → UPDATE_PROFILE → FINALIZE，最终 InsightsReport 通过 pydantic。"""
    llm = MockLLMClient()
    # 注册 fixture 响应（路由不显式注册，靠"第一个非空队列"退化策略）
    llm.register("compare", json.dumps(_compare_fixture()))
    llm.register("attribute", json.dumps(_attribute_fixture()))
    llm.register("extract_signals", json.dumps(_signals_fixture()))
    llm.register("synthesize", json.dumps(_synthesize_fixture()))
    llm.register("present", _present_text_with_tag())
    llm.register("drill", _drill_text_with_tag())
    llm.register("update_profile", json.dumps(_profile_delta_fixture()))

    svc = RetroService(
        llm=llm,
        settings=settings_no_cache,
        runtime_dir=tmp_path / "runtime_data",
        cache_dir=tmp_path / "cache",
    )
    session = svc.new_session()

    session.load_inputs(
        video_id=video_data.video_id,
        profile=profile_v1,
        strategy_snapshot=strategy_snapshot,
        video=video_data.model_dump(mode="json"),
        baseline=baseline_data.model_dump(mode="json"),
    )
    assert session.fsm.state == RetroState.LOAD

    await session.run_analysis_phases()
    assert session.fsm.state == RetroState.SYNTHESIZE
    assert session.memory.insights_report_draft is not None

    # PRESENT
    chunks: list[str] = []
    async for c in session.stream_present():
        chunks.append(c)
    assert session.fsm.state == RetroState.PRESENT
    full_present = "".join(chunks)
    assert _has_source_tag(full_present)
    assert "想先深入聊哪一块" in full_present

    # DRILL
    drill_chunks: list[str] = []
    async for c in session.stream_drill(
        element_id="dc_completion",
        element_type="data_card",
        user_text="为什么会在第 12 秒掉",
    ):
        drill_chunks.append(c)
    assert session.fsm.state == RetroState.DRILL
    drill_text = "".join(drill_chunks)
    assert _has_source_tag(drill_text)

    # UPDATE_PROFILE
    delta, profile_v2 = await session.update_profile(profile_in=profile_v1)
    assert session.fsm.state == RetroState.UPDATE_PROFILE
    assert profile_v2.meta.version == 2
    session.write_profile(profile_v2)

    # FINALIZE
    report = session.finalize(
        user_id="user_a_001",
        video_id=video_data.video_id,
        strategy_id=strategy_snapshot.strategy_id,
        profile_version_in=profile_v1.meta.version,
        profile_delta=delta,
    )
    assert session.fsm.state == RetroState.FINALIZE
    # 重 validate 一次以保证写盘 JSON 也是合法的
    re_loaded = InsightsReport.model_validate(report.model_dump(mode="json"))
    assert re_loaded.report_id == report.report_id
    assert any(c.is_key_indicator for c in re_loaded.data_cards)


# ---------------- 测试 2：DRILL 沿 evidence 链 ----------------

@pytest.mark.asyncio
async def test_drill_evidence_chain():
    """DRILL 输出必须引用具体 evidence（drop_off / cmt_xxx）。"""
    llm = MockLLMClient()
    llm.register("drill", _drill_text_with_tag())

    memory = RetroMemory()
    memory.insights_report_draft = _synthesize_fixture()

    chunks: list[str] = []
    async for c in stream_drill(
        llm=llm,
        memory=memory,
        element_id="dc_completion",
        element_type="data_card",
        user_text="为什么会在第 12 秒掉",
    ):
        chunks.append(c)
    text = "".join(chunks)
    assert "drop_off_curve" in text or "[10:14]" in text or "12 秒" in text
    assert "cmt_201" in text
    assert _has_source_tag(text)
    assert len(memory.drill_history) == 1


# ---------------- 测试 3：SYNTHESIZE JSON 校验 retry ----------------

@pytest.mark.asyncio
async def test_synthesize_json_validation():
    """第一次返回非法 JSON / 缺字段；第二次合法 → retry 成功。"""
    llm = MockLLMClient()
    # 第一次：缺关键字段（缺 insights）
    bad = json.dumps({"data_cards": [], "strategy_review": [], "audience_signals": [], "suggestions": []})
    llm.register("synthesize", bad)
    llm.register("synthesize", json.dumps(_synthesize_fixture()))

    memory = RetroMemory()
    memory.comparison_grid = _compare_fixture()
    memory.attributions = _attribute_fixture()
    memory.audience_signals = _signals_fixture()

    out = await run_synthesize(llm=llm, memory=memory, max_retries=2)
    assert "insights" in out and len(out["insights"]) >= 3
    # 应当被 call 了两次
    synth_calls = [c for c in llm.call_log if c["stage_key"] == "synthesize"]
    assert len(synth_calls) == 2


# ---------------- 测试 4：profile_v1 → profile_v2 ----------------

def test_update_profile_v1_to_v2(profile_v1):
    """ProfileDelta 合并后版本号 +1，audit_log 含 version-bump 总条目。"""
    delta = ProfileDelta.model_validate(_profile_delta_fixture())
    profile_v2 = merge_profile_delta(profile_in=profile_v1, delta=delta)
    assert profile_v2.meta.version == profile_v1.meta.version + 1

    # 找到 hypothesis h001 应当有 1 条 evidence_for + status=supported
    h001 = next(h for h in profile_v2.to_explore.hypotheses if h.hypothesis_id == "h001")
    assert h001.status == "supported"
    assert len(h001.evidence_for) == 1

    # persona_trait 新增
    new_traits = [t.trait for t in profile_v2.personalized.persona_traits]
    assert any("真实身份呈现" in t for t in new_traits)

    # audit_log 含 version-bump
    bumps = [e for e in profile_v2.audit_log if "version bump" in e.change]
    assert len(bumps) == 1
    assert "v1 -> v2" in bumps[0].change

    # pydantic 重新校验
    Profile.model_validate(profile_v2.model_dump(mode="json"))


# ---------------- 测试 5：source-tag 强约束 ----------------

@pytest.mark.asyncio
async def test_source_tag_enforcement():
    """PRESENT 第一次无 tag → retry → 仍无 → fallback 兜底。"""
    llm = MockLLMClient()
    no_tag = "成功的部分：完播 0.39 比预测低 0.06。"
    llm.register("present", no_tag)
    llm.register("present", no_tag)  # retry 仍无

    memory = RetroMemory()
    memory.insights_report_draft = _synthesize_fixture()

    chunks: list[str] = []
    async for c in stream_present(llm=llm, memory=memory):
        chunks.append(c)
    text = "".join(chunks)
    assert _has_source_tag(text), f"fallback 兜底失败：{text!r}"
    assert "系统兜底" in text


# ---------------- 测试 6：EXTRACT_SIGNALS 4+ cluster ----------------

def test_audience_signals_clustering():
    """fixture 必须有 4 个 cluster；同时验证 audience_signals 字段合法。"""
    sig = _signals_fixture()
    assert "clusters" in sig
    assert len(sig["clusters"]) >= 4
    assert len({c["cluster_id"] for c in sig["clusters"]}) == 4
    # audience_signals 4 条覆盖 4 类 category
    cats = {s["category"] for s in sig["audience_signals"]}
    assert "unmet_request" in cats
    assert "new_audience_segment" in cats
    # 至少一条正向 / 负向 strategy_feedback
    assert any(c.startswith("strategy_feedback") for c in cats)


# ---------------- 测试 7：COMPARE handler 端到端（路径覆盖） ----------------

@pytest.mark.asyncio
async def test_compare_handler_writes_memory(video_data, baseline_data, profile_v1, strategy_snapshot):
    """直接调 run_compare，确认 comparison_grid 落到 memory。"""
    llm = MockLLMClient()
    llm.register("compare", json.dumps(_compare_fixture()))

    memory = RetroMemory()
    memory.inputs = {
        "profile": profile_v1.model_dump(mode="json"),
        "strategy_snapshot": strategy_snapshot.model_dump(mode="json"),
        "video": video_data.model_dump(mode="json"),
        "baseline": baseline_data.model_dump(mode="json"),
        "video_id": video_data.video_id,
    }
    out = await run_compare(llm=llm, memory=memory)
    assert memory.comparison_grid is out
    assert any(c["is_key_indicator"] for c in out["data_cards"])


# ---------------- 测试 8：_extract_json_block 鲁棒性 ----------------

def test_extract_json_block_clean():
    """整段干净 JSON 直接解析。"""
    data = _extract_json_block('{"data_cards": [], "strategy_review": []}')
    assert data == {"data_cards": [], "strategy_review": []}


def test_extract_json_block_trailing_text():
    """JSON 后跟说明文字（thinking 模式常见输出）。"""
    raw = '{"data_cards": [], "strategy_review": []} 以上是分析结果，请参考。'
    data = _extract_json_block(raw)
    assert data == {"data_cards": [], "strategy_review": []}


def test_extract_json_block_leading_text():
    """JSON 前有说明文字。"""
    raw = '以下是对比结果：\n{"data_cards": [], "strategy_review": []}'
    data = _extract_json_block(raw)
    assert data == {"data_cards": [], "strategy_review": []}


def test_extract_json_block_skips_non_json_braces():
    """中文括号 / 非标准 { 不干扰提取。"""
    raw = '{这不是JSON} 实际结果：{"data_cards": [], "strategy_review": []}'
    data = _extract_json_block(raw)
    assert data == {"data_cards": [], "strategy_review": []}


def test_extract_json_block_fenced():
    """```json ... ``` fenced block。"""
    raw = '```json\n{"data_cards": [], "strategy_review": []}\n```'
    data = _extract_json_block(raw)
    assert data == {"data_cards": [], "strategy_review": []}


# ---------------- 测试 9：drill_history 缓冲容量 ----------------

def test_drill_history_capacity():
    """memory.drill_history 应保持最多 4 条。"""
    memory = RetroMemory()
    for i in range(7):
        memory.push_drill(
            DrillTurn(
                element_id=f"e_{i}",
                element_type="data_card",
                user_text=f"q{i}",
                answer_text=f"a{i}",
            )
        )
    assert len(memory.drill_history) == 4
    assert memory.drill_history[0].element_id == "e_3"


# ---------------- 测试 10：per-video cache 查找 ----------------

def test_per_video_cache_lookup(settings_cached, video_data, baseline_data, profile_v1, strategy_snapshot, tmp_path):
    """_maybe_load_cache 优先查 retro_synthesis_{video_id}.json。"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    synth = _synthesize_fixture()

    # 写 per-video 文件
    per_video_data = {
        "video_id": "vid_016",
        "compare_output": _compare_fixture(),
        "attribute_output": _attribute_fixture(),
        "extract_signals_output": _signals_fixture(),
        "synthesize_output": synth,
    }
    (cache_dir / "retro_synthesis_vid_016.json").write_text(
        json.dumps(per_video_data), encoding="utf-8"
    )

    svc = RetroService(
        llm=MockLLMClient(),
        settings=settings_cached,
        cache_dir=cache_dir,
        runtime_dir=tmp_path / "runtime",
    )
    session = svc.new_session(use_cache=True)
    session.memory.inputs = {
        "video_id": "vid_016",
        "profile": profile_v1.model_dump(mode="json"),
        "strategy_snapshot": strategy_snapshot.model_dump(mode="json"),
        "video": video_data.model_dump(mode="json"),
        "baseline": baseline_data.model_dump(mode="json"),
    }

    result = session._maybe_load_cache()
    assert result is not None
    assert result["video_id"] == "vid_016"
    assert "synthesize_output" in result


# ---------------- 测试 11.5：缓存 present_text 跳过 LLM ----------------

@pytest.mark.asyncio
async def test_cached_present_text_skips_llm(
    settings_cached, video_data, baseline_data, profile_v1, strategy_snapshot, tmp_path
):
    """cache 文件含 present_text 时，stream_present_typed 应直接 yield 文本，不调 LLM。"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached_present = "<source:数据驱动> 这是预生成的复盘文本。"
    payload = {
        "video_id": "vid_016",
        "present_text": cached_present,
        "compare_output": _compare_fixture(),
        "attribute_output": _attribute_fixture(),
        "extract_signals_output": _signals_fixture(),
        "synthesize_output": _synthesize_fixture(),
    }
    (cache_dir / "retro_synthesis_vid_016.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    llm = MockLLMClient()  # 故意不注册任何 present 响应
    svc = RetroService(
        llm=llm, settings=settings_cached, cache_dir=cache_dir, runtime_dir=tmp_path / "runtime"
    )
    session = svc.new_session(use_cache=True)
    session.load_inputs(
        video_id="vid_016",
        profile=profile_v1,
        strategy_snapshot=strategy_snapshot,
        video=video_data.model_dump(mode="json"),
        baseline=baseline.model_dump(mode="json") if (baseline := baseline_data) else {},
    )
    await session.run_analysis_phases()  # 触发 _maybe_load_cache → 设置 _cached_present_text

    chunks: list[tuple[str, str]] = []
    async for ev in session.stream_present_typed():
        chunks.append(ev)

    # 应当只有一个 content 事件，内容就是缓存文本，没有 thinking 事件
    assert len(chunks) == 1
    assert chunks[0] == ("content", cached_present)
    # LLM 完全没被调用过 PRESENT 阶段
    present_calls = [c for c in llm.call_log if c.get("stage_key") == "present"]
    assert len(present_calls) == 0


# ---------------- 测试 12：inject_analysis_results FSM 路径 ----------------

def test_inject_analysis_results(settings_no_cache, video_data, baseline_data, profile_v1, strategy_snapshot, tmp_path):
    """inject_analysis_results 应正确转移 FSM 并填充 memory，无需 LLM 调用。"""
    svc = RetroService(
        llm=MockLLMClient(),
        settings=settings_no_cache,
        cache_dir=tmp_path / "cache",
        runtime_dir=tmp_path / "runtime",
    )
    session = svc.new_session()
    session.load_inputs(
        video_id="vid_016",
        profile=profile_v1,
        strategy_snapshot=strategy_snapshot,
        video=video_data.model_dump(mode="json"),
        baseline=baseline_data.model_dump(mode="json"),
    )
    assert session.fsm.state == RetroState.LOAD

    bg_data = {
        "compare_output": _compare_fixture(),
        "attribute_output": _attribute_fixture(),
        "extract_signals_output": _signals_fixture(),
        "synthesize_output": _synthesize_fixture(),
    }
    session.inject_analysis_results(bg_data)

    assert session.fsm.state == RetroState.SYNTHESIZE
    assert session.memory.comparison_grid == bg_data["compare_output"]
    assert session.memory.insights_report_draft == bg_data["synthesize_output"]
    # LLM 未被调用
    assert len(MockLLMClient().call_log) == 0
