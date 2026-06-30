"""把 ProfileDelta 合并到 Profile_v_in，产出 Profile_v_(in+1)。

合并规则（与 ``onboarding_agent_demo_spec.md`` + retro spec §5.8 对齐）：

1. ``add_evidence``：追加 evidence 到指定 hypothesis 的 evidence_for / evidence_against
2. ``promote``：状态升级（hypothesis status，或 to_explore → personalized 收敛）
3. ``new_observations``：新增 persona_trait / life_context / unique_asset / open_question
4. ``audit_entries``：直接 extend；自动追加一条 version-bump 总条目

约束（spec §5.8 判定规则）：
- 单条视频样本时 hypothesis 最多 promote 到 ``supported``，不能直接 ``graduated``
- 不在 evidence 支持范围内的更新一律不合并（由调用方过滤；merger 只做结构合并）
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from backend.schemas import (
    AuditLogEntry,
    Evidence,
    Hypothesis,
    LifeContext,
    OpenQuestion,
    PersonaTrait,
    Profile,
    ProfileDelta,
    UniqueAsset,
)

_log = structlog.get_logger("retro.profile_merger")

_HYPOTHESIS_TERMINAL = {"graduated"}  # 终态，不允许从单条复盘直接到达


def merge_profile_delta(
    *,
    profile_in: Profile,
    delta: ProfileDelta,
    new_version: int | None = None,
    timestamp: datetime | None = None,
) -> Profile:
    """合并 delta，返回新版本 Profile。

    Parameters
    ----------
    profile_in : Profile
        当前画像（v_in）。
    delta : ProfileDelta
        retro UPDATE_PROFILE 阶段产出的 delta。
    new_version : int, optional
        指定新版本号；不指定时为 ``profile_in.meta.version + 1``。
    timestamp : datetime, optional
        合并时间戳；不指定时取 utc now。

    Returns
    -------
    Profile
        合并后的新画像（已通过 pydantic 校验）。
    """
    ts = timestamp or datetime.now(tz=timezone.utc)
    target_version = new_version if new_version is not None else profile_in.meta.version + 1

    # 用 dict 形式做易变操作；最后再统一过 pydantic 校验
    p_dict: dict[str, Any] = profile_in.model_dump(mode="json")
    p_dict["meta"]["version"] = target_version
    p_dict["meta"]["created_at"] = ts.isoformat()

    # 1) add_evidence
    _apply_add_evidence(p_dict, delta.add_evidence)
    # 2) promote
    _apply_promote(p_dict, delta.promote)
    # 3) new_observations
    _apply_new_observations(p_dict, delta.new_observations)

    # 4) audit_entries（保留原有 + delta 的 + 自动 version-bump）
    audit = list(p_dict.get("audit_log", []))
    for entry in delta.audit_entries:
        audit.append(entry.model_dump(mode="json"))
    audit.append(
        AuditLogEntry(
            ts=ts,
            source="RETRO_UPDATE",
            change=f"version bump v{profile_in.meta.version} -> v{target_version}",
            claim_id=None,
        ).model_dump(mode="json")
    )
    p_dict["audit_log"] = audit

    merged = Profile.model_validate(p_dict)
    _log.info(
        "retro.profile_merger.ok",
        from_version=profile_in.meta.version,
        to_version=target_version,
        add_evidence=len(delta.add_evidence),
        promote=len(delta.promote),
        new_obs=len(delta.new_observations),
    )
    return merged


def _apply_add_evidence(p_dict: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """把 evidence 追加到对应 hypothesis 的 for/against 列表。"""
    if not items:
        return
    hypotheses: list[dict[str, Any]] = (
        p_dict.setdefault("to_explore", {}).setdefault("hypotheses", [])
    )
    for item in items:
        target_kind = item.get("target_kind")
        target_id = item.get("target_id")
        side = item.get("side", "for")
        ev_payload = item.get("evidence", {})
        if target_kind != "hypothesis":
            # 当前只实现 hypothesis；其他类型未来扩展
            continue
        hypo = next((h for h in hypotheses if h.get("hypothesis_id") == target_id), None)
        if hypo is None:
            continue
        # 校验 evidence
        ev = Evidence.model_validate(ev_payload).model_dump(mode="json")
        key = "evidence_for" if side == "for" else "evidence_against"
        hypo.setdefault(key, []).append(ev)


def _apply_promote(p_dict: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """处理状态升级。

    支持两种 kind：
    - ``hypothesis``：改 status；禁止单条视频直接到 graduated
    - ``open_question``：从 to_explore.open_questions 移除（视为收敛），
      不自动派生新 trait（让 ``new_observations`` 做这件事）
    """
    if not items:
        return
    hypotheses: list[dict[str, Any]] = (
        p_dict.setdefault("to_explore", {}).setdefault("hypotheses", [])
    )
    open_questions: list[dict[str, Any]] = (
        p_dict["to_explore"].setdefault("open_questions", [])
    )
    for item in items:
        kind = item.get("kind")
        target_id = item.get("id")
        to_status = item.get("to_status") or item.get("to_state")
        if kind == "hypothesis":
            hypo = next(
                (h for h in hypotheses if h.get("hypothesis_id") == target_id),
                None,
            )
            if hypo is None or to_status is None:
                continue
            if to_status in _HYPOTHESIS_TERMINAL:
                _log.warning(
                    "retro.profile_merger.promote_blocked",
                    reason="单条视频复盘禁止直接到 graduated",
                    hypothesis_id=target_id,
                )
                hypo["status"] = "supported"
            else:
                hypo["status"] = to_status
            # 用 schema 验证（防止 status 字面量错误）
            Hypothesis.model_validate(hypo)
        elif kind == "open_question":
            for i, q in enumerate(list(open_questions)):
                if q.get("question_id") == target_id or q.get("question") == target_id:
                    open_questions.pop(i)
                    break


def _apply_new_observations(
    p_dict: dict[str, Any],
    items: list[dict[str, Any]],
) -> None:
    """根据 category 把新观察插到 personalized 或 to_explore。"""
    if not items:
        return
    personalized = p_dict.setdefault(
        "personalized", {"persona_traits": [], "life_context": [], "unique_assets": []}
    )
    personalized.setdefault("persona_traits", [])
    personalized.setdefault("life_context", [])
    personalized.setdefault("unique_assets", [])

    to_explore = p_dict.setdefault(
        "to_explore", {"open_questions": [], "hypotheses": [], "aspirations": []}
    )
    to_explore.setdefault("open_questions", [])
    to_explore.setdefault("aspirations", [])

    for obs in items:
        category = obs.get("category")
        claim = obs.get("claim_text", "")
        proposed_state = obs.get("proposed_state", "personalized")
        evidence_payload = obs.get("evidence", [])
        evidence_objs = [Evidence.model_validate(e).model_dump(mode="json") for e in evidence_payload]
        if proposed_state == "to_explore":
            # 进入 open_questions（粗略转化）
            to_explore["open_questions"].append(
                OpenQuestion(question=claim, options=[], priority=3).model_dump(mode="json")
            )
            continue

        if category == "persona_trait":
            personalized["persona_traits"].append(
                PersonaTrait(
                    trait=claim,
                    evidence=evidence_objs,
                ).model_dump(mode="json")
            )
        elif category == "life_context":
            personalized["life_context"].append(
                LifeContext(context=claim, evidence=evidence_objs).model_dump(mode="json")
            )
        elif category == "unique_asset":
            personalized["unique_assets"].append(
                UniqueAsset(asset=claim, evidence=evidence_objs).model_dump(mode="json")
            )
        elif category == "aspiration":
            to_explore["aspirations"].append(claim)
        else:
            _log.warning("retro.profile_merger.unknown_category", category=category)
