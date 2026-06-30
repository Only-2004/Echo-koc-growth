"""Strategy snapshot schema（Strategy agent 输出 → Retro 输入）。

对应 content_strategy_agent_demo_spec.md §4。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SourceTag = Literal["画像驱动", "趋势驱动", "数据驱动", "历史复盘", "用户偏好驱动"]


class StrategyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["idea_driven", "discovery_driven", "system_triggered"]
    user_idea: str
    iterations: int = Field(ge=0)


class IdeaSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str
    predicted_pillar: str
    rationale: str


class HeatAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trend_score: float = Field(ge=0, le=1)
    trend_direction: Literal["rising", "stable", "falling"]
    supply_demand_ratio: float = Field(ge=0)
    matched_trends: list[str]
    comment: str


AlignmentLevel = Literal["high", "medium", "low"]


class PillarAlignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pillar: str
    alignment: AlignmentLevel
    evidence: str


class PersonaLeveragePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trait: str | None = None
    life_context: str | None = None
    how_to_use: str


class ToExploreValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hypothesis_id: str
    what_this_tests: str


class ProfileFit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pillar_alignment: list[PillarAlignment]
    persona_leverage: list[PersonaLeveragePoint]
    to_explore_validation: list[ToExploreValidation]
    fit_score: float = Field(ge=0, le=1)


class DifferentiationPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    point: str
    source: SourceTag


class HookDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    design: str
    rationale: str


class Execution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hook: HookDesign
    pacing: str
    cta: str
    tags: list[str]
    key_focus: str


class StrategySnapshot(BaseModel):
    """Strategy agent 的最终产物，retro 的契约输入。"""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    user_id: str
    profile_version: int = Field(ge=1)
    generated_at: datetime
    input: StrategyInput
    idea: IdeaSummary
    heat_analysis: HeatAnalysis
    profile_fit: ProfileFit
    differentiation: list[DifferentiationPoint]
    execution: Execution
