"""Onboarding agent 各状态的 handler。

每个 handler 是一个 async 函数 / coroutine：

- ``run_analyze`` → 同步式（pro-thinking · 结构化输出）
- ``run_present`` / ``run_explore`` / ``run_summarize`` → 流式（flash-thinking）
- ``run_validate`` → 同步式（flash · JSON 分类）
- ``run_finalize`` → 同步式（pro-thinking · pydantic 严格校验 + retry 1 次）

所有 handler 都不直接管理状态机转移；由 :class:`OnboardingService` 在调用后
根据返回值决定下一个状态。
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from pydantic import ValidationError

from ...mock_loader import MockBundle
from ...schemas import Profile
from .._llm import LLMClient
from .memory import CandidateClaim, OnboardingMemory

_logger = structlog.get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts" / "onboarding"

# Source tag 强约束（PRD 红线，与 strategy schema SourceTag 对齐）
_VALID_SOURCE_TAGS = {"画像驱动", "趋势驱动", "数据驱动", "历史复盘", "用户偏好驱动"}
# 匹配末行 [tag1 tag2] 形式
_SOURCE_TAG_PATTERN = re.compile(r"\[([^\[\]]+)\]\s*$")


def _load_prompt(name: str) -> str:
    """加载 prompts/onboarding/{name}.txt。"""
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _system_prompt() -> str:
    """加载贯穿所有 LLM 调用的 system prompt。"""
    return _load_prompt("system.txt")


def extract_sources(text: str) -> tuple[str, list[str]]:
    """从文本末尾抽取 [tag] 标签，返回 (clean_text, tags)。

    Parameters
    ----------
    text : str
        原始 LLM 输出。

    Returns
    -------
    tuple[str, list[str]]
        - 第一项：去除末行 tag 后的纯净文本（trailing whitespace 已 strip）
        - 第二项：识别到的合法 source tag 列表（按出现顺序，去重）

    Notes
    -----
    若末行不是 tag，则返回原文 + 空列表，caller 可决定是否 retry。
    """
    stripped = text.rstrip()
    seen: list[str] = []

    # LLM 可能输出多个并列 [tag]：``...正文\n[数据驱动]\n[画像驱动]``。
    # 循环消耗末尾每一对 ``[xxx]``，直到末尾不再是合法 tag 集合。
    while True:
        match = _SOURCE_TAG_PATTERN.search(stripped)
        if not match:
            break
        raw = match.group(1)
        candidates = [t.strip() for t in re.split(r"[\s,，、]+", raw) if t.strip()]
        # 当前 [] 内必须**全部**是合法 tag，才算 source tag 行；否则可能是
        # 正文中的真实方括号（例如引用），不能误剥。
        if not candidates or not all(c in _VALID_SOURCE_TAGS for c in candidates):
            break
        for tag in candidates:
            if tag not in seen:
                seen.append(tag)
        stripped = stripped[: match.start()].rstrip()

    return stripped, seen


# --------------------------------------------------------------------- ANALYZE


def _serialize_for_analyze(bundle: MockBundle, *, max_videos: int = 12, max_comments_per_video: int = 5) -> dict[str, Any]:
    """裁剪 mock_bundle 到 ANALYZE 需要的最少字段，避免 prompt 超长。

    Parameters
    ----------
    bundle : MockBundle
        已校验的 mock 数据包。
    max_videos : int, optional
        最多保留 N 条历史视频。
    max_comments_per_video : int, optional
        每条视频最多保留 N 条评论。
    """
    videos = []
    for v in bundle.historical_videos.videos[:max_videos]:
        videos.append(
            {
                "video_id": v.video_id,
                "title": v.title,
                "transcript_summary": v.transcript_summary,
                "topic_tags": v.topic_tags,
                "primary_pillar": v.primary_pillar,
                "duration_sec": v.duration_sec,
                "metrics": v.metrics.model_dump(),
            }
        )

    top_comments: dict[str, list[dict[str, Any]]] = {}
    for vid, comments in bundle.comments.comments_by_video.items():
        sorted_cs = sorted(comments, key=lambda c: c.likes, reverse=True)
        top_comments[vid] = [
            {"comment_id": c.comment_id, "text": c.text, "likes": c.likes}
            for c in sorted_cs[:max_comments_per_video]
        ]

    return {
        "account_snapshot_json": json.dumps(bundle.account.model_dump(mode="json"), ensure_ascii=False),
        "historical_videos_json": json.dumps({"videos": videos}, ensure_ascii=False),
        "top_comments_json": json.dumps(top_comments, ensure_ascii=False),
        "audience_snapshot_json": json.dumps(bundle.audience.model_dump(mode="json"), ensure_ascii=False),
        "baseline_metrics_json": json.dumps(bundle.baseline.model_dump(mode="json"), ensure_ascii=False),
    }


async def run_analyze(
    *,
    llm: LLMClient,
    bundle: MockBundle,
) -> dict[str, Any]:
    """ANALYZE state（离线）。

    Parameters
    ----------
    llm : LLMClient
        LLM 客户端。
    bundle : MockBundle
        全部账号数据。

    Returns
    -------
    dict[str, Any]
        ``{"candidate_claims": [...], "draft_profile_seed": {...}}``。
    """
    prompt_template = _load_prompt("01_analyze.txt")
    payload = _serialize_for_analyze(bundle)
    user_msg = prompt_template.format(**payload)

    raw = await llm.complete(
        model="pro-thinking",
        system=_system_prompt(),
        messages=[{"role": "user", "content": user_msg}],
        json_mode=True,
        temperature=0.3,
        max_tokens=4096,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # strip optional ```json ... ``` markdown fence
        cleaned = cleaned.removeprefix("```json").removeprefix("```").rstrip("```").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        _logger.error("analyze.parse_failed", error=str(exc), raw_preview=raw[:200])
        raise RuntimeError(f"ANALYZE 输出非合法 JSON：{exc}") from exc

    return data


def seed_memory_from_analyze(memory: OnboardingMemory, analyze_output: dict[str, Any]) -> None:
    """把 ANALYZE 输出填入 memory（candidate_claims + draft_profile 初值）。

    Parameters
    ----------
    memory : OnboardingMemory
        待填充的 memory。
    analyze_output : dict[str, Any]
        ``run_analyze`` 或缓存的返回值。
    """
    claims_data = analyze_output.get("candidate_claims", [])
    memory.candidate_claims = [
        CandidateClaim(
            claim_id=c["claim_id"],
            claim_text=c["claim_text"],
            category=c["category"],
            proposed_state=c["proposed_state"],
            evidence=list(c.get("evidence", [])),
        )
        for c in claims_data
    ]

    seed = analyze_output.get("draft_profile_seed") or {}
    # 确保三态结构存在
    memory.draft_profile = {
        "confirmed": dict(seed.get("confirmed", {})) or {
            "audience_baseline": {},
            "content_pillars": [],
            "content_style": {},
        },
        "personalized": dict(seed.get("personalized", {})) or {
            "persona_traits": [],
            "life_context": [],
            "unique_assets": [],
        },
        "to_explore": dict(seed.get("to_explore", {})) or {
            "open_questions": [],
            "hypotheses": [],
            "aspirations": [],
        },
    }

    # 把 confirmed/personalized claims 顺手填进 draft（最小可演示版本）
    for claim in memory.candidate_claims:
        if claim.proposed_state == "confirmed" and claim.category == "content_pillar":
            memory.draft_profile["confirmed"].setdefault("content_pillars", []).append(
                {
                    "name": claim.claim_text,
                    "evidence_video_ids": [
                        e.get("source_id") for e in claim.evidence if e.get("source_type") == "video"
                    ],
                    "validated_at": None,
                }
            )
        elif claim.proposed_state == "personalized" and claim.category == "persona_trait":
            memory.draft_profile["personalized"].setdefault("persona_traits", []).append(
                {
                    "trait": claim.claim_text,
                    "evidence": claim.evidence,
                }
            )
        elif claim.proposed_state == "to_explore" or claim.category == "open_question":
            memory.draft_profile["to_explore"].setdefault("open_questions", []).append(
                {
                    "question": claim.claim_text,
                    "options": [],
                    "priority": 1,
                    "user_concerns": [],
                    "_touched": False,
                }
            )


# --------------------------------------------------------------------- PRESENT


def _format_filtered_claims(memory: OnboardingMemory) -> tuple[str, str]:
    """从 candidate_claims 选 3-4 条证据扎实的 + 1 条 open_question。"""
    high = [
        c for c in memory.candidate_claims
        if c.proposed_state in {"confirmed", "personalized"}
    ]
    # 按证据条数倒序：证据越多越靠前；并发情况下保持原序
    high_sorted = sorted(high, key=lambda c: len(c.evidence), reverse=True)[:4]
    open_q = next(
        (c for c in memory.candidate_claims if c.category == "open_question" or c.proposed_state == "to_explore"),
        None,
    )

    high_payload = [
        {
            "claim_id": c.claim_id,
            "claim_text": c.claim_text,
            "category": c.category,
            "state": c.proposed_state,
            "evidence": c.evidence[:2],
        }
        for c in high_sorted
    ]
    open_payload = (
        {
            "claim_id": open_q.claim_id,
            "claim_text": open_q.claim_text,
            "evidence": open_q.evidence[:2],
        }
        if open_q
        else {"claim_text": "暂无明显 to_explore 项"}
    )
    return (
        json.dumps(high_payload, ensure_ascii=False),
        json.dumps(open_payload, ensure_ascii=False),
    )


async def run_present(
    *,
    llm: LLMClient,
    memory: OnboardingMemory,
) -> AsyncIterator[tuple[str, str]]:
    """PRESENT state（流式）。

    Yields
    ------
    tuple[str, str]
        ``("thinking", chunk)`` 或 ``("content", chunk)``。
    """
    high_json, open_json = _format_filtered_claims(memory)
    template = _load_prompt("02_present.txt")
    user_msg = template.format(filtered_claims_json=high_json, primary_open_question=open_json)

    async for chunk_type, chunk in llm.stream_typed(
        model="flash-thinking",
        system=_system_prompt(),
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.6,
        max_tokens=600,
    ):
        yield (chunk_type, chunk)


# --------------------------------------------------------------------- VALIDATE


async def run_validate(
    *,
    llm: LLMClient,
    memory: OnboardingMemory,
    user_reply: str,
) -> dict[str, Any]:
    """VALIDATE state（同步分类）。

    Parameters
    ----------
    llm : LLMClient
        LLM 客户端。
    memory : OnboardingMemory
        当前 session memory。
    user_reply : str
        用户最新一条回复。

    Returns
    -------
    dict[str, Any]
        ``{"actions": [...], "new_observations": [...], "user_signals": {...}}``。
    """
    last_present_claims = [
        {
            "claim_id": c.claim_id,
            "claim_text": c.claim_text,
            "category": c.category,
        }
        for c in memory.candidate_claims
        if c.proposed_state in {"confirmed", "personalized"} and not c.touched
    ][:6]

    template = _load_prompt("03_validate.txt")
    user_msg = template.format(
        claims_in_last_present_json=json.dumps(last_present_claims, ensure_ascii=False),
        user_reply_text=user_reply,
    )

    raw = await llm.complete(
        model="flash",
        system=_system_prompt(),
        messages=[{"role": "user", "content": user_msg}],
        json_mode=True,
        temperature=0.0,
        max_tokens=1024,
    )

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        _logger.warning("validate.parse_failed", error=str(exc), raw_preview=raw[:200])
        # 安全 fallback：识别为 skip + mild fatigue，让流程继续
        return {
            "actions": [],
            "new_observations": [],
            "user_signals": {"fatigue_level": "mild", "engagement_topics": []},
        }


def apply_validate_actions(memory: OnboardingMemory, validate_output: dict[str, Any]) -> dict[str, Any]:
    """把 VALIDATE 输出落到 draft_profile + claims.touched。

    Returns
    -------
    dict[str, Any]
        本次新增到 draft 的 patch（用于 SSE ``profile.tick`` 事件）。
    """
    patch: dict[str, Any] = {"actions": [], "new_observations": []}

    for action in validate_output.get("actions", []):
        if not isinstance(action, dict):
            continue
        cid = action.get("claim_id")
        a = action.get("action")
        for claim in memory.candidate_claims:
            if claim.claim_id == cid:
                claim.touched = True
                if a == "modify" and action.get("new_text"):
                    claim.claim_text = action["new_text"]
                elif a == "reject":
                    # 标记拒绝（保留以便 audit）
                    claim.proposed_state = "rejected"
                elif a == "move_to_explore":
                    claim.proposed_state = "to_explore"
                    memory.draft_profile.setdefault("to_explore", {}).setdefault(
                        "open_questions", []
                    ).append(
                        {
                            "question": claim.claim_text,
                            "options": [],
                            "priority": 1,
                            "user_concerns": [],
                            "_touched": False,
                        }
                    )
                break
        patch["actions"].append(action)

    for obs in validate_output.get("new_observations", []):
        if not isinstance(obs, dict):
            continue
        category = obs.get("category", "")
        state = obs.get("proposed_state", "to_explore")
        section_map = {
            "confirmed": "confirmed",
            "personalized": "personalized",
            "to_explore": "to_explore",
        }
        section_name = section_map.get(state, "to_explore")
        section = memory.draft_profile.setdefault(section_name, {})
        if category == "content_pillar":
            section.setdefault("content_pillars", []).append(
                {
                    "name": obs.get("claim_text", ""),
                    "evidence_video_ids": [],
                    "validated_at": None,
                }
            )
        elif category == "persona_trait":
            section.setdefault("persona_traits", []).append(
                {
                    "trait": obs.get("claim_text", ""),
                    "evidence": obs.get("evidence", []),
                }
            )
        elif category == "life_context":
            section.setdefault("life_context", []).append(
                {
                    "context": obs.get("claim_text", ""),
                    "valid_until": None,
                    "evidence": obs.get("evidence", []),
                }
            )
        elif category == "open_question":
            section.setdefault("open_questions", []).append(
                {
                    "question": obs.get("claim_text", ""),
                    "options": [],
                    "priority": 2,
                    "user_concerns": [],
                    "_touched": False,
                }
            )
        patch["new_observations"].append(obs)

    signals = validate_output.get("user_signals") or {}
    fatigue = signals.get("fatigue_level")
    if fatigue in {"none", "mild", "strong"}:
        memory.fatigue_level = fatigue
    return patch


# --------------------------------------------------------------------- EXPLORE


async def run_explore(
    *,
    llm: LLMClient,
    memory: OnboardingMemory,
) -> AsyncIterator[tuple[str, str]]:
    """EXPLORE state（流式）。"""
    questions = (
        memory.draft_profile.get("to_explore", {}).get("open_questions", [])
        if isinstance(memory.draft_profile, dict)
        else []
    )
    ranked = sorted(
        [q for q in questions if isinstance(q, dict) and not q.get("_touched", False)],
        key=lambda q: q.get("priority", 99),
    )
    if ranked:
        ranked[0]["_touched"] = True

    recent = "\n".join(
        f"{t.role}: {t.text[:80]}" for t in memory.recent_turns(k=4)
    )

    template = _load_prompt("04_explore.txt")
    user_msg = template.format(
        to_explore_questions=json.dumps(ranked[:3], ensure_ascii=False),
        recent_turns=recent or "(暂无对话历史)",
    )

    async for chunk_type, chunk in llm.stream_typed(
        model="flash-thinking",
        system=_system_prompt(),
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.6,
        max_tokens=400,
    ):
        yield (chunk_type, chunk)


# --------------------------------------------------------------------- SUMMARIZE


async def run_summarize(
    *,
    llm: LLMClient,
    memory: OnboardingMemory,
) -> AsyncIterator[tuple[str, str]]:
    """SUMMARIZE state（流式）。"""
    template = _load_prompt("05_summarize.txt")
    # 注意：draft_profile 含 _touched 内部字段，去掉再注入
    cleaned = _strip_internal_fields(memory.draft_profile)
    # 把最近若干轮对话拼进 prompt，确保用户在 PRESENT/VALIDATE 期间补的新事实进入总览
    recent = "\n".join(
        f"{t.role}: {t.text[:160]}" for t in memory.recent_turns(k=8)
    )
    user_msg = template.format(
        draft_profile_json=json.dumps(cleaned, ensure_ascii=False),
        recent_conversation=recent or "(暂无补充对话)",
        turn_count=len(memory.short_term),
    )

    async for chunk_type, chunk in llm.stream_typed(
        model="flash-thinking",
        system=_system_prompt(),
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.5,
        max_tokens=900,
    ):
        yield (chunk_type, chunk)


def _strip_internal_fields(obj: Any) -> Any:
    """递归去除 _touched 等内部字段（不进入 prompt）。"""
    if isinstance(obj, dict):
        return {k: _strip_internal_fields(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_strip_internal_fields(i) for i in obj]
    return obj


# --------------------------------------------------------------------- FINALIZE


async def run_finalize(
    *,
    llm: LLMClient,
    memory: OnboardingMemory,
    max_retry: int = 1,
) -> Profile:
    """FINALIZE state（同步 · pro-thinking · pydantic 严格校验 + retry）。

    Parameters
    ----------
    llm : LLMClient
        LLM 客户端。
    memory : OnboardingMemory
        当前 session memory。
    max_retry : int, optional
        校验失败时的额外重试次数（共调用 max_retry+1 次）。

    Returns
    -------
    Profile
        通过 pydantic 严格 (extra="forbid") 校验的 profile_v1 对象。

    Raises
    ------
    RuntimeError
        所有重试均失败。
    """
    template = _load_prompt("06_finalize.txt")
    cleaned = _strip_internal_fields(memory.draft_profile)
    generated_at = datetime.now(timezone.utc).isoformat()

    user_msg = template.format(
        draft_profile_json=json.dumps(cleaned, ensure_ascii=False),
        user_id=memory.user_id,
        session_id=memory.session_id,
        generated_at=generated_at,
    )

    attempts = max_retry + 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        raw = await llm.complete(
            model="pro-thinking",
            system=_system_prompt(),
            messages=[{"role": "user", "content": user_msg}],
            json_mode=True,
            temperature=0.2,
            max_tokens=3072,
        )
        try:
            data = json.loads(raw)
            return Profile.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            _logger.warning(
                "finalize.attempt_failed",
                attempt=attempt + 1,
                error=str(exc)[:200],
            )
            # retry：在 user_msg 前加一句修复提示
            user_msg = (
                "上一次输出未通过 pydantic 严格校验，请仅修正错误后重新输出严格符合 schema 的 JSON。\n\n"
                + user_msg
            )

    raise RuntimeError(f"FINALIZE 失败（已重试 {max_retry} 次）：{last_error}")


async def run_finalize_stream(
    *,
    llm: LLMClient,
    memory: OnboardingMemory,
    max_retry: int = 1,
) -> AsyncIterator[tuple[str, str]]:
    """FINALIZE state（流式 · pro-thinking · 边思考边输出）。

    Yields
    ------
    tuple[str, str]
        ``("thinking", chunk)``：推理过程 token（可能为空，取决于模型档位）。
        ``("profile_json", json_str)``：验证通过后的完整 profile JSON（仅 yield 一次）。
        ``("error", msg)``：所有重试均失败时。
    """
    template = _load_prompt("06_finalize.txt")
    cleaned = _strip_internal_fields(memory.draft_profile)
    generated_at = datetime.now(timezone.utc).isoformat()

    user_msg = template.format(
        draft_profile_json=json.dumps(cleaned, ensure_ascii=False),
        user_id=memory.user_id,
        session_id=memory.session_id,
        generated_at=generated_at,
    )

    attempts = max_retry + 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        content_chunks: list[str] = []
        async for chunk_type, chunk in llm.stream_typed(
            model="pro-thinking",
            system=_system_prompt(),
            messages=[{"role": "user", "content": user_msg}],
            temperature=0.2,
            max_tokens=3072,
        ):
            if chunk_type == "thinking":
                yield ("thinking", chunk)
            else:
                content_chunks.append(chunk)

        raw = "".join(content_chunks).strip()
        # LLM 流式输出时可能带 ```json ... ``` 包裹，需剥除
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw.rstrip())
        try:
            data = json.loads(raw)
            profile = Profile.model_validate(data)
            yield ("profile_json", json.dumps(profile.model_dump(mode="json"), ensure_ascii=False))
            return
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            _logger.warning(
                "finalize_stream.attempt_failed",
                attempt=attempt + 1,
                error=str(exc)[:200],
            )
            user_msg = (
                "上一次输出未通过 pydantic 严格校验，请仅修正错误后重新输出严格符合 schema 的 JSON。\n\n"
                + user_msg
            )

    yield ("error", f"FINALIZE 失败（已重试 {max_retry} 次）：{last_error}")
