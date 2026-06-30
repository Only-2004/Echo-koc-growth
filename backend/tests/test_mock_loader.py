"""mock_data 全部 8 份 JSON 通过 schema 校验的测试。

通过 = M1 关键交付。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.mock_loader import load_mock_bundle


def test_load_mock_bundle_succeeds() -> None:
    """load_mock_bundle 成功返回完整对象，所有 schema 通过。"""
    bundle = load_mock_bundle()

    assert bundle.account.user_id == "user_a_001"
    assert bundle.account.platform == "douyin"
    assert len(bundle.historical_videos.videos) >= 8
    assert "vid_001" in bundle.comments.comments_by_video
    assert any(c.label.startswith("考研") for c in bundle.audience.interest_clusters)
    assert "考研日常" in bundle.baseline.by_pillar
    assert any(t.topic == "考研一日三餐" for t in bundle.external_trends.trends)
    assert bundle.new_video_for_retro.video_id == "vid_020"
    assert bundle.new_video_for_retro.metrics.completion_rate == 0.47
    assert len(bundle.onboarding_template.ticks) >= 7


def test_kaoyan_narrative_consistency() -> None:
    """关键伏笔：onboarding 推断 → strategy 主题 → retro 数据 闭环一致。"""
    bundle = load_mock_bundle()

    kaoyan_videos = [v for v in bundle.historical_videos.videos if v.primary_pillar == "考研日常"]
    other_videos = [v for v in bundle.historical_videos.videos if v.primary_pillar != "考研日常"]
    assert len(kaoyan_videos) >= 3, "至少 3 条考研视频，否则 onboarding 推不出考研为 to_explore"

    avg_kaoyan_completion = sum(v.metrics.completion_rate for v in kaoyan_videos) / len(kaoyan_videos)
    avg_other_completion = sum(v.metrics.completion_rate for v in other_videos) / len(other_videos)
    assert avg_kaoyan_completion > avg_other_completion, "考研内容完播必须显著优于其他，才能成为 to_explore 信号"

    retro_video = bundle.new_video_for_retro
    assert "考研" in retro_video.title, "retro 视频必须是考研融合主题"
    assert retro_video.metrics.completion_rate < 0.50, "retro 完播应不达 strategy 预测上限（miss 或 within_noise）"
    assert retro_video.metrics.follow_rate > 0.020, "retro follow_rate 应超出预测（exceed）"
    assert retro_video.metrics.new_followers_with_kaoyan_tag_ratio > 0.7, \
        "新粉考研标签占比必须 > 0.7（key_indicator 大幅 exceed）"


def test_mock_endpoints_return_data() -> None:
    """ENABLE_MOCK_DEBUG=true 时 /api/mock/* 端点返回正常数据。"""
    app = create_app()
    client = TestClient(app)

    # 启动 startup hook 加载数据
    with client:
        response = client.get("/api/mock/account")
        assert response.status_code == 200
        assert response.json()["user_id"] == "user_a_001"

        response = client.get("/api/mock/videos")
        assert response.status_code == 200
        assert "videos" in response.json()

        response = client.get("/api/mock/retro-video")
        assert response.status_code == 200
        assert response.json()["strategy_id"] == "str_001"
