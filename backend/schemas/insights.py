"""InsightsReport schema（Retro agent 输出）。

对应 retro_insight_agent_demo_spec.md §4。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .profile import ProfileDelta


Verdict = Literal["hit", "miss", "exceed", "within_noise", "partial"]
ConfidenceLevel = Literal["high", "medium", "low"]


class DataCard(BaseModel):
    """retro view 中的指标卡（基于 baseline_pillar 判定 verdict）。"""

    model_config = ConfigDict(extra="forbid")

    card_id: str
    metric: str
    value: float
    baseline_overall: float | None = None
    baseline_pillar: float | None = None
    verdict: Verdict
    is_key_indicator: bool = False


class StrategyReviewItem(BaseModel):
    """逐条 strategy 字段的策略意图 vs 实际表现对照。"""

    model_config = ConfigDict(extra="forbid")

    predicted: str
    actual: str
    verdict: Verdict
    evidence: list[dict[str, str]] = Field(default_factory=list)


class InsightEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["drop_off", "comment", "metric", "audience", "transcript"]
    ref: str
    snippet: str | None = None


class Insight(BaseModel):
    """retro 卡片中央的一条洞察。"""

    model_config = ConfigDict(extra="forbid")

    insight_id: str
    claim: str
    evidence: list[InsightEvidence]
    confidence: ConfidenceLevel
    caveat: str | None = None
    linked_card_ids: list[str] = Field(default_factory=list)
    linked_strategy_fields: list[str] = Field(default_factory=list)


AudienceSignalCategory = Literal[
    "unmet_request",
    "new_audience_segment",
    "strategy_feedback_positive",
    "strategy_feedback_negative",
]


class AudienceSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    signal_id: str
    signal: str
    category: AudienceSignalCategory | None = None
    evidence_comments: list[str]
    implication: str


class Suggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suggestion_id: str
    type: Literal["iterate", "test_new", "pivot", "hold"]
    content: str
    linked_insight_ids: list[str] = Field(default_factory=list)
    estimated_effort: Literal["low", "medium", "high"]


class InsightsReport(BaseModel):
    """Retro agent 的最终产物。"""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    user_id: str
    video_id: str
    strategy_id: str
    profile_version_in: int = Field(ge=1)
    generated_at: datetime
    data_cards: list[DataCard]
    strategy_review: list[StrategyReviewItem]
    insights: list[Insight]
    audience_signals: list[AudienceSignal]
    suggestions: list[Suggestion]
    profile_delta: ProfileDelta | None = None
