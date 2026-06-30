"""启动时把 mock_data/*.json 加载到内存并通过 schema 校验。

主要消费方：
- Onboarding agent：account_snapshot / historical_videos / comments / audience_snapshot / baseline
- Strategy agent：external_trends + 全部 onboarding 输入
- Retro agent：new_video_for_retro
- 演示备份：onboarding_conversation_template
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schemas import (
    AccountBaseline,
    AccountSnapshot,
    AudienceSnapshot,
    CommentsFile,
    ExternalTrendsFile,
    HistoricalVideosFile,
    NewVideoForRetro,
    OnboardingConversationTemplate,
)


@dataclass(frozen=True, slots=True)
class MockBundle:
    """运行时 mock 数据包。"""

    account: AccountSnapshot
    historical_videos: HistoricalVideosFile
    comments: CommentsFile
    audience: AudienceSnapshot
    baseline: AccountBaseline
    external_trends: ExternalTrendsFile
    new_video_for_retro: NewVideoForRetro
    onboarding_template: OnboardingConversationTemplate


def _read(path: Path) -> dict[str, object]:
    """读 JSON 并返回 dict（不做 schema 校验，由 caller 完成）。"""
    return json.loads(path.read_text(encoding="utf-8"))


def load_mock_bundle(mock_dir: Path | None = None) -> MockBundle:
    """从指定目录加载并校验 mock 数据。

    Parameters
    ----------
    mock_dir : Path, optional
        默认 `backend/mock_data/`。

    Returns
    -------
    MockBundle
        全部 mock 数据通过 schema 后的冻结对象。
    """
    base = mock_dir or Path(__file__).parent / "mock_data"

    return MockBundle(
        account=AccountSnapshot.model_validate(_read(base / "account_snapshot.json")),
        historical_videos=HistoricalVideosFile.model_validate(_read(base / "historical_videos.json")),
        comments=CommentsFile.model_validate(_read(base / "comments.json")),
        audience=AudienceSnapshot.model_validate(_read(base / "audience_snapshot.json")),
        baseline=AccountBaseline.model_validate(_read(base / "account_baseline.json")),
        external_trends=ExternalTrendsFile.model_validate(_read(base / "external_trends.json")),
        new_video_for_retro=NewVideoForRetro.model_validate(_read(base / "new_video_for_retro.json")),
        onboarding_template=OnboardingConversationTemplate.model_validate(
            _read(base / "onboarding_conversation_template.json")
        ),
    )
