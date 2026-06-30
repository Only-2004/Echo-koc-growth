"""Mock 数据的 pydantic v2 模型。

覆盖 account_snapshot / historical_videos / comments / audience_snapshot /
account_baseline / external_trends / new_video_for_retro / onboarding_conversation_template
共 8 份 mock 文件的 schema。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------- AccountSnapshot ----------------

class AccountSnapshot(BaseModel):
    """KOC 账号身份快照。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    platform: Literal["douyin", "xiaohongshu", "bilibili"]
    handle: str
    display_name: str
    bio: str
    follower_count: int = Field(ge=0)
    following_count: int = Field(ge=0)
    verified: bool
    self_declared_tags: list[str]
    created_at: datetime
    snapshot_at: datetime
    self_intent: str


# ---------------- HistoricalVideos ----------------

class VideoMetrics(BaseModel):
    """单条视频的关键指标。"""

    model_config = ConfigDict(extra="forbid")

    plays: int = Field(ge=0)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    shares: int = Field(ge=0)
    completion_rate: float = Field(ge=0, le=1)
    follow_rate: float = Field(ge=0, le=1)


class HistoricalVideo(BaseModel):
    """单条历史视频。"""

    model_config = ConfigDict(extra="forbid")

    video_id: str
    published_at: datetime
    title: str
    transcript_summary: str
    topic_tags: list[str]
    duration_sec: int = Field(gt=0)
    metrics: VideoMetrics
    drop_off_curve: list[float]
    primary_pillar: str


class HistoricalVideosFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    videos: list[HistoricalVideo]


# ---------------- Comments ----------------

class Comment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment_id: str
    text: str
    likes: int = Field(ge=0)


class CommentsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comments_by_video: dict[str, list[Comment]]


# ---------------- AudienceSnapshot ----------------

class InterestCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cluster_id: str
    label: str
    weight: float = Field(ge=0, le=1)
    notes: str | None = None


class AudienceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    snapshot_at: datetime
    demographics: dict[str, dict[str, float] | list[str]]
    interest_clusters: list[InterestCluster]
    core_audience_hypothesis: str


# ---------------- AccountBaseline ----------------

class BaselineMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completion_rate: float = Field(ge=0, le=1)
    follow_rate: float = Field(ge=0, le=1)
    average_plays: float = Field(ge=0)
    comment_rate: float | None = Field(default=None, ge=0, le=1)
    share_rate: float | None = Field(default=None, ge=0, le=1)
    video_count: int | None = None
    notes: str | None = None


class AccountBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    computed_at: datetime
    overall: BaselineMetrics
    by_pillar: dict[str, BaselineMetrics]


# ---------------- ExternalTrends ----------------

class TrendItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trend_id: str
    topic: str
    trend_score: float = Field(ge=0, le=1)
    direction: Literal["rising", "stable", "falling"]
    supply_demand_ratio: float = Field(ge=0)
    search_volume_30d: list[int]
    matched_keywords: list[str]
    notes: str | None = None


class ExternalTrendsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fetched_at: datetime
    platform: Literal["douyin", "xiaohongshu", "bilibili"]
    trends: list[TrendItem]


# ---------------- NewVideoForRetro ----------------

class RetroVideoMetrics(BaseModel):
    """retro 阶段消费的视频指标，比 VideoMetrics 多一些 follow 细节。"""

    model_config = ConfigDict(extra="forbid")

    plays: int
    likes: int
    comments: int
    shares: int
    completion_rate: float = Field(ge=0, le=1)
    follow_rate: float = Field(ge=0, le=1)
    new_followers: int = Field(ge=0)
    new_followers_with_kaoyan_tag_ratio: float = Field(ge=0, le=1)


class DropOffPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    t_sec: int = Field(ge=0)
    retention: float = Field(ge=0, le=1)


class RetroComment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment_id: str
    text: str
    likes: int = Field(ge=0)
    cluster: str


class NewVideoForRetro(BaseModel):
    model_config = ConfigDict(extra="forbid")
    video_id: str
    title: str
    published_at: datetime
    strategy_id: str
    duration_sec: int = Field(gt=0)
    transcript_summary: str
    metrics: RetroVideoMetrics
    drop_off_curve_points: list[DropOffPoint]
    comments: list[RetroComment]


# ---------------- OnboardingConversationTemplate ----------------

class OnboardingTick(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step: int
    role: Literal["ai", "user", "system"]
    text: str
    tick_state: str | None = None
    draft_profile_patch: dict[str, object] | None = None


class OnboardingConversationTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    user_id: str
    ticks: list[OnboardingTick]
