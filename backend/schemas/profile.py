"""KOC Profile schema（Onboarding agent 的输出 + Retro agent 的输入）。

对应 onboarding_agent_demo_spec.md §4。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PillarState = Literal["confirmed", "personalized", "to_explore"]


class Evidence(BaseModel):
    """支撑某条 claim 的证据。"""

    model_config = ConfigDict(extra="forbid")

    source_type: Literal["video", "comment", "user_reply", "metric", "audience"]
    source_id: str | None = None
    snippet: str | None = None
    ref: str | None = None


class ContentPillar(BaseModel):
    """已确定的内容主轴（confirmed）。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    evidence_video_ids: list[str] = Field(default_factory=list)
    validated_at: datetime | None = None


class PersonaTrait(BaseModel):
    """个性化特质（personalized）。"""

    model_config = ConfigDict(extra="forbid")

    trait: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float | None = None


class LifeContext(BaseModel):
    """用户当下的生活上下文（personalized · 有效期）。"""

    model_config = ConfigDict(extra="forbid")

    context: str
    valid_until: datetime | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class UniqueAsset(BaseModel):
    """用户独有的可调用资产。"""

    model_config = ConfigDict(extra="forbid")

    asset: str
    evidence: list[Evidence] = Field(default_factory=list)


class OpenQuestion(BaseModel):
    """待探索的开放问题。"""

    model_config = ConfigDict(extra="forbid")

    question: str
    options: list[str] = Field(default_factory=list)
    priority: int = Field(ge=1)
    user_concerns: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    """待验证的假设（retro 阶段会回写 evidence_for / evidence_against）。"""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    hypothesis: str
    status: Literal["pending", "supported", "refuted", "graduated"]
    evidence_for: list[Evidence] = Field(default_factory=list)
    evidence_against: list[Evidence] = Field(default_factory=list)


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ts: datetime
    source: Literal["ANALYZE", "VALIDATE", "EXPLORE", "RETRO_UPDATE", "USER"]
    change: str
    claim_id: str | None = None


class ProfileMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    version: int = Field(ge=1)
    created_at: datetime
    session_id: str


class ConfirmedPillars(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience_baseline: dict[str, str | float | int] = Field(default_factory=dict)
    content_pillars: list[ContentPillar] = Field(default_factory=list)
    content_style: dict[str, str | float | int] = Field(default_factory=dict)


class PersonalizedAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")
    persona_traits: list[PersonaTrait] = Field(default_factory=list)
    life_context: list[LifeContext] = Field(default_factory=list)
    unique_assets: list[UniqueAsset] = Field(default_factory=list)


class ToExploreSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    aspirations: list[str] = Field(default_factory=list)


class Profile(BaseModel):
    """KOC 三态画像。Onboarding 输出 v1，Retro 阶段回写 delta 形成 v2、v3..."""

    model_config = ConfigDict(extra="forbid")

    meta: ProfileMeta
    confirmed: ConfirmedPillars
    personalized: PersonalizedAssets
    to_explore: ToExploreSection
    audit_log: list[AuditLogEntry] = Field(default_factory=list)


class ProfileDelta(BaseModel):
    """Retro 阶段产出的画像 delta，用于合并生成下一版 profile。"""

    model_config = ConfigDict(extra="forbid")

    add_evidence: list[dict[str, object]] = Field(default_factory=list)
    promote: list[dict[str, str]] = Field(default_factory=list)
    new_observations: list[dict[str, object]] = Field(default_factory=list)
    audit_entries: list[AuditLogEntry] = Field(default_factory=list)
