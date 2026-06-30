"""Onboarding agent 后端核心逻辑测试。

全部基于 :class:`MockLLMClient`，不依赖真实 API key。

覆盖：

- ``test_state_machine_full_flow``：六状态全流程，最终 profile_v1.json schema 通过
- ``test_validate_action_classification``：4 类用户回复都能被正确识别
- ``test_finalize_retry``：FINALIZE 第一次返回非法 JSON，retry 后成功
- ``test_source_tag_enforcement``：缺 tag 触发 retry，最终有 tag（含 fallback）
- ``test_finalize_writes_profile_v1``：写到 runtime_data/profile_v1.json
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from backend.agents._llm import LLMClient, MockLLMClient, fixture_key
from backend.agents._llm.client import ModelTier
from backend.agents.onboarding import OnboardingService, OnboardingState
from backend.agents.onboarding.handlers import (
    apply_validate_actions,
    extract_sources,
    run_finalize,
    run_validate,
    seed_memory_from_analyze,
)
from backend.agents.onboarding.memory import OnboardingMemory
from backend.config import Settings
from backend.mock_loader import load_mock_bundle
from backend.schemas import Profile

# ---------------------------------------------------------------- fixtures


def _read_prompt(name: str) -> str:
    """读 prompts/onboarding/{name}.txt 计算 system prompt 摘要用。"""
    path = Path(__file__).resolve().parents[1] / "prompts" / "onboarding" / name
    return path.read_text(encoding="utf-8")


SYSTEM_PROMPT = _read_prompt("system.txt")


def _settings(tmp_path: Path, *, use_cache: bool = True) -> Settings:
    """构造 demo Settings，把 cache / runtime 指向 tmp_path。"""
    return Settings(
        deepseek_api_key="",
        deepseek_api_base="https://api.deepseek.com/v1",
        model_flash="m-flash",
        model_pro="m-pro",
        max_tokens_flash=2048,
        max_tokens_flash_thinking=8192,
        max_tokens_pro_thinking=16384,
        use_cached_analysis=use_cache,
        use_fallback_all=False,
        llm_max_retries=2,
        llm_retry_min_wait=0.01,
        llm_retry_max_wait=0.02,
        llm_timeout_first_token=8.0,
        llm_timeout_total=30.0,
        admin_token="",
        log_level="warning",
        port=8000,
        cors_origin="http://localhost:5173",
        enable_mock_debug=False,
    )


def _write_analyze_cache(cache_dir: Path) -> dict[str, Any]:
    """生成一个最小可用的 cache/onb_analyze.json，覆盖食堂 / 考研故事线。"""
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": "2026-04-28T00:00:00Z",
        "model": "pro-thinking",
        "candidate_claims": [
            {
                "claim_id": "c001",
                "claim_text": "食堂探店为稳定内容主轴",
                "category": "content_pillar",
                "proposed_state": "confirmed",
                "evidence": [
                    {"source_type": "video", "source_id": "vid_001", "snippet": "9 块 9 套餐"},
                    {"source_type": "video", "source_id": "vid_007", "snippet": "咖啡 ranking"},
                ],
            },
            {
                "claim_id": "c002",
                "claim_text": "活力 + 真实感的人设特质",
                "category": "persona_trait",
                "proposed_state": "personalized",
                "evidence": [
                    {"source_type": "comment", "source_id": "cmt_0042", "snippet": "破防了"},
                ],
            },
            {
                "claim_id": "c003",
                "claim_text": "考研内容是否要作为长期主轴",
                "category": "open_question",
                "proposed_state": "to_explore",
                "evidence": [
                    {"source_type": "video", "source_id": "vid_004", "snippet": "完播 0.48"},
                ],
            },
        ],
        "draft_profile_seed": {
            "confirmed": {"audience_baseline": {}, "content_pillars": [], "content_style": {}},
            "personalized": {"persona_traits": [], "life_context": [], "unique_assets": []},
            "to_explore": {"open_questions": [], "hypotheses": [], "aspirations": []},
        },
    }
    (cache_dir / "onb_analyze.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


# ------------------- fixture builders（生成 MockLLMClient 桩响应）


def _present_text() -> str:
    """模拟 PRESENT 阶段流式输出，含合法 source tag。"""
    return (
        "嗨小A 👋\n这不是问卷。我已经分析过你的 8 条视频：\n"
        "· 食堂探店是稳定主轴（4 条，平均完播 34%）\n"
        "· 考研那几条完播 43% 显著好于其他\n"
        "· 受众里有 31% 考研意向群体\n"
        "这些感受准确吗？哪部分需要修正？\n"
        "[数据驱动 画像驱动]"
    )


def _explore_text() -> str:
    """EXPLORE 阶段流式输出。"""
    return (
        "你说「怕做不下去了断更」是关键。这个顾虑可以拆成两层：\n"
        "1. 内容耐力：考研期间精力是否够拍\n"
        "2. 受众绑定：考完是否会失去当前粉丝\n"
        "你觉得哪一层更让你犹豫？\n"
        "[画像驱动]"
    )


def _summarize_text() -> str:
    """SUMMARIZE 阶段流式输出。"""
    return (
        "关于你已经清晰的部分：食堂探店是主轴，4 条视频平均完播 34%。\n\n"
        "你身上让我印象深刻的特质：活力 + 真实感，评论区多次提到 \"破防\"。\n\n"
        "你还在思考的方向：考研内容是否做长期主轴。我们先标成待探索。\n\n"
        "这是我目前的理解，还有需要补充或修正的吗？\n"
        "[画像驱动 数据驱动]"
    )


def _validate_json(action: str = "confirm", fatigue: str = "none") -> str:
    """VALIDATE 阶段 JSON 输出。"""
    payload = {
        "actions": [
            {"claim_id": "c001", "action": action, "new_text": None, "reason": "用户明确表态"}
        ],
        "new_observations": [],
        "user_signals": {"fatigue_level": fatigue, "engagement_topics": ["食堂"]},
    }
    return json.dumps(payload, ensure_ascii=False)


def _finalize_json(*, user_id: str, session_id: str) -> str:
    """FINALIZE 阶段 JSON 输出（schema-valid）。"""
    payload = {
        "meta": {
            "user_id": user_id,
            "version": 1,
            "created_at": "2026-04-28T10:00:00Z",
            "session_id": session_id,
        },
        "confirmed": {
            "audience_baseline": {"primary": "在校女大学生 + 考研意向"},
            "content_pillars": [
                {
                    "name": "食堂探店",
                    "evidence_video_ids": ["vid_001", "vid_007"],
                    "validated_at": None,
                }
            ],
            "content_style": {},
        },
        "personalized": {
            "persona_traits": [
                {"trait": "活力 + 真实感", "evidence": []}
            ],
            "life_context": [
                {"context": "在读大三 · 考研中", "valid_until": None, "evidence": []}
            ],
            "unique_assets": [
                {"asset": "正在考研的食堂博主（融合身份）", "evidence": []}
            ],
        },
        "to_explore": {
            "open_questions": [
                {
                    "question": "考研内容是否要作为长期主轴",
                    "options": ["作为主轴", "短期话题", "还没想好"],
                    "priority": 1,
                    "user_concerns": ["内容耐力", "考后受众断层"],
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h001",
                    "hypothesis": "考研内容作为主轴可持续到考完为止",
                    "status": "pending",
                    "evidence_for": [],
                    "evidence_against": [],
                }
            ],
            "aspirations": [],
        },
        "audit_log": [
            {
                "ts": "2026-04-28T10:00:00Z",
                "source": "ANALYZE",
                "change": "added 食堂探店 pillar",
                "claim_id": "c001",
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------- helpers


def _build_fixtures(
    *,
    user_replies: list[str],
    validate_outputs: list[str],
    user_id: str = "user_a_001",
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """构造覆盖 PRESENT / VALIDATE / EXPLORE / SUMMARIZE / FINALIZE 的 fixtures。"""
    fixtures: dict[str, str] = {}
    sequences: dict[str, list[str]] = {}

    # PRESENT：tier=flash-thinking, 第一次 user_msg 是 02_present.txt 渲染后
    # 但 last_user message 内容很长，这里我们在测试中通过 sequences 兜底：
    # 任何 flash-thinking 的调用都按 sequence 顺序返回。

    # 由于 fixture_key 依赖 last_user 前 40 字，我们采用更鲁棒的方案：
    # 把 sequences 挂在 *特殊 key 'flash-thinking_any'*，但实际 MockLLMClient
    # 不支持 wildcard。所以测试时直接构造一个 patch 版 MockLLMClient（见 test 内）。
    return fixtures, sequences


class _SequenceMockLLM(LLMClient):
    """按调用次数顺序返回 fixture 的 MockLLM；不依赖 prompt hash。

    便于跨多个不同 prompt 的连续调用（PRESENT → VALIDATE → EXPLORE → ...）
    构造确定性测试。
    """

    def __init__(
        self,
        *,
        complete_seq: list[str] | None = None,
        stream_seq: list[str] | None = None,
        chunk_size: int = 8,
    ) -> None:
        self._complete = list(complete_seq or [])
        self._stream = list(stream_seq or [])
        self.chunk_size = chunk_size
        self.complete_calls: list[tuple[ModelTier, str]] = []
        self.stream_calls: list[tuple[ModelTier, str]] = []

    async def complete(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        self.complete_calls.append((model, messages[-1]["content"][:40] if messages else ""))
        if not self._complete:
            raise KeyError("SequenceMockLLM: complete sequence exhausted")
        return self._complete.pop(0)

    async def stream(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        self.stream_calls.append((model, messages[-1]["content"][:40] if messages else ""))
        if not self._stream:
            raise KeyError("SequenceMockLLM: stream sequence exhausted")
        text = self._stream.pop(0)
        for i in range(0, len(text), self.chunk_size):
            yield text[i : i + self.chunk_size]

    async def stream_typed(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[tuple[str, str]]:
        self.stream_calls.append((model, messages[-1]["content"][:40] if messages else ""))
        if not self._stream:
            raise KeyError("SequenceMockLLM: stream_typed sequence exhausted")
        text = self._stream.pop(0)
        for i in range(0, len(text), self.chunk_size):
            yield ("content", text[i : i + self.chunk_size])


# ---------------------------------------------------------------- tests


@pytest.mark.asyncio
async def test_state_machine_full_flow(tmp_path: Path) -> None:
    """完整六状态走通：start → turn(PRESENT) → turn(user "对的") → finalize。

    用 cache/onb_analyze.json 跳过 ANALYZE LLM 调用。
    """
    bundle = load_mock_bundle()
    cache_dir = tmp_path / "cache"
    runtime_dir = tmp_path / "runtime_data"
    _write_analyze_cache(cache_dir)
    settings = _settings(tmp_path, use_cache=True)

    llm = _SequenceMockLLM(
        complete_seq=[
            _validate_json(action="confirm", fatigue="strong"),  # VALIDATE 用户秒确认 + 强收口
            _finalize_json(user_id="user_a_001", session_id="placeholder"),  # FINALIZE
        ],
        stream_seq=[
            _present_text(),  # PRESENT
            _summarize_text(),  # SUMMARIZE（VALIDATE → SUMMARIZE）
        ],
    )

    svc = OnboardingService(
        llm=llm,
        bundle=bundle,
        settings=settings,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
    )

    # 1) start
    started = await svc.start()
    assert started["state"] == OnboardingState.PRESENT.value
    session_id = started["session_id"]
    assert len(started["candidate_claims"]) >= 3

    # 2) PRESENT 流（user_text=None）
    events_present = []
    async for ev in svc.turn_stream(session_id=session_id, user_text=None):
        events_present.append(ev)
    types = [e["type"] for e in events_present]
    assert "message.complete" in types
    msg_complete = next(e for e in events_present if e["type"] == "message.complete")
    assert any(t in {"画像驱动", "数据驱动", "趋势驱动"} for t in msg_complete["sources"])

    # 3) 用户明确收口 → VALIDATE → SUMMARIZE → finish.ready
    events_turn = []
    async for ev in svc.turn_stream(session_id=session_id, user_text="对的，可以了"):
        events_turn.append(ev)
    turn_types = [e["type"] for e in events_turn]
    assert "profile.tick" in turn_types
    assert "message.complete" in turn_types
    assert "finish.ready" in turn_types

    # 4) finalize → profile_v1.json 写盘 + schema 通过
    profile = await svc.finalize(session_id)
    assert profile.meta.user_id == "user_a_001"
    assert profile.meta.version == 1
    assert (runtime_dir / "profile_v1.json").is_file()


@pytest.mark.asyncio
async def test_validate_action_classification() -> None:
    """run_validate + apply_validate_actions 应识别 confirm / modify / reject / move_to_explore。"""
    bundle = load_mock_bundle()
    memory = OnboardingMemory(session_id="t1", user_id="user_a_001")
    seed_memory_from_analyze(
        memory,
        {
            "candidate_claims": [
                {
                    "claim_id": "c001",
                    "claim_text": "食堂探店",
                    "category": "content_pillar",
                    "proposed_state": "confirmed",
                    "evidence": [],
                },
                {
                    "claim_id": "c002",
                    "claim_text": "活力人设",
                    "category": "persona_trait",
                    "proposed_state": "personalized",
                    "evidence": [],
                },
                {
                    "claim_id": "c003",
                    "claim_text": "考研主轴？",
                    "category": "open_question",
                    "proposed_state": "to_explore",
                    "evidence": [],
                },
            ],
            "draft_profile_seed": {},
        },
    )

    payloads = [
        {
            "actions": [{"claim_id": "c001", "action": "confirm", "new_text": None, "reason": "对"}],
            "new_observations": [],
            "user_signals": {"fatigue_level": "none", "engagement_topics": []},
        },
        {
            "actions": [
                {"claim_id": "c002", "action": "modify", "new_text": "真实 + 学生气", "reason": "对但..."}
            ],
            "new_observations": [],
            "user_signals": {"fatigue_level": "none", "engagement_topics": []},
        },
        {
            "actions": [{"claim_id": "c003", "action": "reject", "new_text": None, "reason": "不对"}],
            "new_observations": [],
            "user_signals": {"fatigue_level": "none", "engagement_topics": []},
        },
        {
            "actions": [
                {"claim_id": "c001", "action": "move_to_explore", "new_text": None, "reason": "犹豫"}
            ],
            "new_observations": [],
            "user_signals": {"fatigue_level": "mild", "engagement_topics": []},
        },
    ]

    llm = _SequenceMockLLM(complete_seq=[json.dumps(p, ensure_ascii=False) for p in payloads])

    # confirm
    out1 = await run_validate(llm=llm, memory=memory, user_reply="对")
    apply_validate_actions(memory, out1)
    assert next(c for c in memory.candidate_claims if c.claim_id == "c001").touched is True

    # modify
    out2 = await run_validate(llm=llm, memory=memory, user_reply="对但 trait 是真实 + 学生气")
    apply_validate_actions(memory, out2)
    assert next(c for c in memory.candidate_claims if c.claim_id == "c002").claim_text == "真实 + 学生气"

    # reject
    out3 = await run_validate(llm=llm, memory=memory, user_reply="不对")
    apply_validate_actions(memory, out3)
    assert next(c for c in memory.candidate_claims if c.claim_id == "c003").proposed_state == "rejected"

    # move_to_explore
    out4 = await run_validate(llm=llm, memory=memory, user_reply="还没想好")
    apply_validate_actions(memory, out4)
    assert memory.fatigue_level == "mild"
    # 触发把 c001 移入 to_explore
    assert next(
        c for c in memory.candidate_claims if c.claim_id == "c001"
    ).proposed_state == "to_explore"


@pytest.mark.asyncio
async def test_finalize_retry() -> None:
    """FINALIZE 第一次输出非法 JSON，retry 1 次后通过 pydantic 校验。"""
    memory = OnboardingMemory(session_id="onb_test", user_id="user_a_001")
    memory.draft_profile = {
        "confirmed": {"audience_baseline": {}, "content_pillars": [], "content_style": {}},
        "personalized": {"persona_traits": [], "life_context": [], "unique_assets": []},
        "to_explore": {"open_questions": [], "hypotheses": [], "aspirations": []},
    }

    bad_first = "{not valid json"
    good_second = _finalize_json(user_id="user_a_001", session_id="onb_test")
    llm = _SequenceMockLLM(complete_seq=[bad_first, good_second])

    profile = await run_finalize(llm=llm, memory=memory, max_retry=1)
    assert isinstance(profile, Profile)
    assert profile.meta.user_id == "user_a_001"
    assert profile.meta.session_id == "onb_test"
    assert len(llm.complete_calls) == 2  # 第一次失败 + 第二次成功


@pytest.mark.asyncio
async def test_source_tag_enforcement(tmp_path: Path) -> None:
    """缺 source tag 触发 retry；retry 仍缺时 fallback 注入 [数据驱动]。"""
    bundle = load_mock_bundle()
    cache_dir = tmp_path / "cache"
    runtime_dir = tmp_path / "runtime_data"
    _write_analyze_cache(cache_dir)
    settings = _settings(tmp_path, use_cache=True)

    bad_text = "这是一段没有 source tag 的回复。\n用户请回应。"  # 没有末行 [tag]
    # 两次 stream 都没 tag → 触发 fallback
    llm = _SequenceMockLLM(
        complete_seq=[],
        stream_seq=[bad_text, bad_text],
    )
    svc = OnboardingService(
        llm=llm,
        bundle=bundle,
        settings=settings,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
    )
    started = await svc.start()
    sid = started["session_id"]

    events = [ev async for ev in svc.turn_stream(session_id=sid, user_text=None)]
    msg_complete = next(e for e in events if e["type"] == "message.complete")
    # 至少 1 个 source（fallback 也算）
    assert len(msg_complete["sources"]) >= 1
    assert msg_complete["sources"][0] in {"画像驱动", "趋势驱动", "数据驱动"}


@pytest.mark.asyncio
async def test_finalize_writes_profile_v1(tmp_path: Path) -> None:
    """端到端 finalize：profile_v1.json 写盘且能被 pydantic 重新加载。"""
    bundle = load_mock_bundle()
    cache_dir = tmp_path / "cache"
    runtime_dir = tmp_path / "runtime_data"
    _write_analyze_cache(cache_dir)
    settings = _settings(tmp_path, use_cache=True)

    llm = _SequenceMockLLM(
        complete_seq=[
            _validate_json(action="confirm", fatigue="strong"),
            _finalize_json(user_id="user_a_001", session_id="placeholder"),
        ],
        stream_seq=[_present_text(), _summarize_text()],
    )
    svc = OnboardingService(
        llm=llm,
        bundle=bundle,
        settings=settings,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
    )

    started = await svc.start()
    sid = started["session_id"]
    async for _ev in svc.turn_stream(session_id=sid, user_text=None):
        pass
    async for _ev in svc.turn_stream(session_id=sid, user_text="对的，可以了"):
        pass
    profile = await svc.finalize(sid)

    out_path = runtime_dir / "profile_v1.json"
    assert out_path.is_file()
    reloaded = Profile.model_validate(json.loads(out_path.read_text(encoding="utf-8")))
    assert reloaded.meta.user_id == profile.meta.user_id
    assert reloaded.meta.version == 1
    # 三态结构非空
    assert reloaded.confirmed.content_pillars
    assert reloaded.to_explore.open_questions


# ---------------------------------------------------------------- helpers tests


def test_extract_sources_basic() -> None:
    """extract_sources 应识别末行 [tag] 并去除。"""
    text = "你好。\n[画像驱动 数据驱动]"
    clean, sources = extract_sources(text)
    assert clean == "你好。"
    assert sources == ["画像驱动", "数据驱动"]


def test_extract_sources_missing() -> None:
    """无末行 tag 时 sources 为空。"""
    clean, sources = extract_sources("普通文本，没有任何标签")
    assert sources == []
    assert clean == "普通文本，没有任何标签"


def test_extract_sources_with_invalid_tag() -> None:
    """不合法 tag（例如 [Hello]）应被 ignore。"""
    clean, sources = extract_sources("回复内容\n[随便写的]")
    assert sources == []


def test_fixture_key_stable() -> None:
    """fixture_key 同输入应返回同输出。"""
    a = fixture_key("flash", "system text", "user msg")
    b = fixture_key("flash", "system text", "user msg")
    assert a == b
    c = fixture_key("flash-thinking", "system text", "user msg")
    assert a != c


# 让 pytest-asyncio 在 auto mode 下识别本文件
asyncio  # type: ignore[pointless-statement]  # noqa: B018
