"""Strategy Agent 后端单元测试。

全部用 ``MockLLMClient``，覆盖：

1. 完整 8 状态主流程 → 落库 + pydantic 校验
2. REFINE 三类反馈分类（challenge / adjust / approve），approve 落新版本
3. SCORE JSON parse 失败 retry 后成功
4. PRESENT source tag 缺失 → retry → fallback 注入兜底 tag
5. snapshot 写盘 + GET 取回字段一致
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from backend.agents._llm.client import MockLLMClient, MockResponseSpec
from backend.agents.strategy.service import (
    FALLBACK_SOURCE_TAG,
    StrategyService,
    StrategyServiceConfig,
)
from backend.mock_loader import load_mock_bundle
from backend.schemas.strategy import StrategySnapshot

# ---------------------------------------------------------------------------
# Fixture：标准的 SCORE / STRATEGIZE / PRESENT JSON
# ---------------------------------------------------------------------------


SCORE_JSON: dict[str, Any] = {
    "heat_analysis": {
        "trend_score": 0.82,
        "trend_direction": "rising",
        "supply_demand_ratio": 0.7,
        "matched_trends": ["考研一日三餐"],
        "comment": "处于上升期，供给少于需求",
    },
    "profile_fit": {
        "pillar_alignment": [
            {"pillar": "食堂探店", "alignment": "high", "evidence": "vid_001 / vid_007"},
            {"pillar": "考研日常", "alignment": "high", "evidence": "vid_004 / vid_010"},
        ],
        "persona_leverage": [
            {"trait": "活力 + 真实感", "how_to_use": "前 3 秒展示困到趴桌"},
        ],
        "to_explore_validation": [
            {"hypothesis_id": "h001", "what_this_tests": "考研内容能否融合既有食堂素材"},
        ],
        "fit_score": 0.78,
    },
    "idea_summary": {
        "topic": "考研期间一日三餐怎么吃才能不困",
        "predicted_pillar": "考研日常 + 食堂探店融合",
        "rationale": "踩到上升 trend + 高 fit + 验证 h001",
    },
}

STRATEGIZE_JSON: dict[str, Any] = {
    "differentiation": [
        {"point": "利用'本人正在考研'的真实身份", "source": "画像驱动"},
        {"point": "复用既有食堂场景资源，节省制作成本", "source": "画像驱动"},
        {"point": "结合学习状态做反差", "source": "趋势驱动"},
    ],
    "execution": {
        "hook": {
            "design": "前 3 秒展示困到趴桌的画面 + 字幕'考研第 67 天'",
            "rationale": "对标当前同主题 top 视频开场",
        },
        "pacing": "前 1/3 做问题感铺垫，中段 3 个解决方案，结尾收口考研日常",
        "cta": "评论区分享你考研中最困的时段",
        "tags": ["考研日常", "食堂探店", "考研党"],
        "key_focus": "新增粉丝中考研兴趣标签占比",
    },
}


PRESENT_TEXT_OK: str = (
    "评估：高 fit + 高 heat，强烈推荐。\n\n"
    "差异化：你正在考研的真实身份是绝对独有资产（画像驱动）；既有食堂素材可以零成本复用（画像驱动）。\n\n"
    "执行要点：hook 用困到趴桌的画面 + '考研第 67 天'字幕；"
    "pacing 前 1/3 铺垫，中段 3 个方案，结尾收口；CTA 让观众分享自己最困时段。\n\n"
    "可观察指标：完播率预期 0.45-0.55，粉丝转化预期 0.015-0.025，重点看新增粉丝中考研兴趣标签占比。\n\n"
    "这版策略你觉得哪里需要调整？\n"
    "SOURCES: 画像驱动, 趋势驱动"
)

PRESENT_TEXT_NO_SOURCES: str = (
    "评估：高 fit + 高 heat。\n\n这版策略你觉得哪里需要调整？"
)

REFINE_REPLY_OK: str = (
    "把 hook 调成轻松路线：把'困到趴桌'换成'起床即开摆'的反讽日常；"
    "保留'考研第 67 天'字幕保持身份锚。pacing 不动，"
    "CTA 改成'你考研第几天开摆'。\n\nSOURCES: 画像驱动"
)

REFINE_REPLY_APPROVE: str = (
    "好的，已经记下你的认可。这版策略写入快照，retro 阶段会重点看"
    "'新增粉丝中考研兴趣标签占比'这个 key indicator。\n\nSOURCES: 画像驱动"
)


# ---------------------------------------------------------------------------
# Helper：构造 service
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_bundle() -> Any:
    """加载真实 mock_data。"""
    return load_mock_bundle()


@pytest.fixture
def runtime_dir(tmp_path: Path) -> Path:
    """每个测试用一个独立 runtime_data 目录。"""
    d = tmp_path / "runtime_data"
    d.mkdir()
    return d


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    """cache 文件路径（默认不存在，触发在线调用路径）。"""
    return tmp_path / "cache" / "strategy_score_strategize.json"


def _make_service(
    *,
    client: MockLLMClient,
    runtime_dir: Path,
    cache_path: Path,
    mock_bundle: Any,
    use_cache: bool = False,
) -> StrategyService:
    return StrategyService(
        client=client,
        config=StrategyServiceConfig(
            use_cached_analysis=use_cache,
            cache_path=cache_path,
            runtime_dir=runtime_dir,
        ),
        mock_bundle=mock_bundle,
    )


async def _drain(service: StrategyService, idea_text: str) -> dict[str, Any]:
    """跑 submit_idea 并取出 ``done`` 事件。"""
    result_event: dict[str, Any] | None = None
    async for ev in service.submit_idea(idea_text=idea_text):
        if ev["event"] == "done":
            result_event = ev
    assert result_event is not None
    return result_event


# ---------------------------------------------------------------------------
# 1) 完整 8 状态主流程
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_machine_full_flow(
    mock_bundle: Any,
    runtime_dir: Path,
    cache_path: Path,
) -> None:
    """全部 8 状态走通 → snapshot pydantic 校验通过。"""
    client = MockLLMClient()
    # ANALYZE_IDEA → flash-thinking complete
    client.queue("flash-thinking", marker="", responses=[])  # 占位（不会命中）
    client.queue_default(responses=[
        MockResponseSpec(text="这条 idea 命中考研一日三餐 trend；高 fit。"),
    ])
    # SCORE → pro-thinking JSON
    client.queue("pro-thinking", marker="score", responses=[
        MockResponseSpec(text=json.dumps(SCORE_JSON, ensure_ascii=False)),
    ])
    # STRATEGIZE → pro-thinking JSON
    client.queue("pro-thinking", marker="strategize", responses=[
        MockResponseSpec(text=json.dumps(STRATEGIZE_JSON, ensure_ascii=False)),
    ])
    # PRESENT → flash-thinking stream
    client.queue("flash-thinking", marker="present", responses=[
        MockResponseSpec(text=PRESENT_TEXT_OK, stream_chunk_chars=30),
    ])

    service = _make_service(
        client=client,
        runtime_dir=runtime_dir,
        cache_path=cache_path,
        mock_bundle=mock_bundle,
    )
    done = await _drain(service, idea_text="考研期间一日三餐怎么吃才能不困")

    snapshot_id = done["snapshot_id"]
    assert snapshot_id.startswith("str_")
    assert "画像驱动" in done["result"]["sources"]
    # submit_idea 已自动 finalize（v1）；显式再 finalize 一次 → v2
    version = await service.finalize(snapshot_id=snapshot_id)
    assert version == 2

    # 落盘 + 通过 pydantic 校验
    payload = service.get_snapshot_payload(snapshot_id=snapshot_id)
    snapshot = StrategySnapshot.model_validate(payload)
    assert snapshot.heat_analysis.trend_direction == "rising"
    assert snapshot.profile_fit.fit_score == pytest.approx(0.78)
    assert len(snapshot.differentiation) >= 2
    assert snapshot.execution.key_focus != ""


# ---------------------------------------------------------------------------
# 2) REFINE 三类反馈
# ---------------------------------------------------------------------------


def _seed_full_flow_fixtures(client: MockLLMClient) -> None:
    """通用：把走完一次 submit_idea 所需的 fixture 塞进 client。"""
    client.queue_default(responses=[MockResponseSpec(text="ANALYZE 文本")])
    client.queue("pro-thinking", marker="score", responses=[
        MockResponseSpec(text=json.dumps(SCORE_JSON, ensure_ascii=False)),
    ])
    client.queue("pro-thinking", marker="strategize", responses=[
        MockResponseSpec(text=json.dumps(STRATEGIZE_JSON, ensure_ascii=False)),
    ])
    client.queue("flash-thinking", marker="present", responses=[
        MockResponseSpec(text=PRESENT_TEXT_OK, stream_chunk_chars=20),
    ])


@pytest.mark.asyncio
async def test_refine_classification(
    mock_bundle: Any,
    runtime_dir: Path,
    cache_path: Path,
) -> None:
    """challenge / adjust / approve 三种反馈各自走通；approve 落新版本，其他不覆盖。"""
    client = MockLLMClient()
    _seed_full_flow_fixtures(client)
    # 三轮 refine，每轮：分类（flash） + 回复（flash-thinking stream）
    client.queue("flash", marker="refine_classify", responses=[
        MockResponseSpec(text=json.dumps({"feedback_type": "challenge"})),
        MockResponseSpec(text=json.dumps({"feedback_type": "adjust"})),
        MockResponseSpec(text=json.dumps({"feedback_type": "approve"})),
    ])
    client.queue("flash-thinking", marker="refine_reply", responses=[
        MockResponseSpec(text="基于画像，hook 这样设计是因为... \nSOURCES: 画像驱动"),
        MockResponseSpec(text=REFINE_REPLY_OK, stream_chunk_chars=30),
        MockResponseSpec(text=REFINE_REPLY_APPROVE, stream_chunk_chars=30),
    ])

    service = _make_service(
        client=client, runtime_dir=runtime_dir, cache_path=cache_path, mock_bundle=mock_bundle
    )
    done = await _drain(service, idea_text="考研期间一日三餐怎么吃才能不困")
    snapshot_id = done["snapshot_id"]

    # challenge：不写盘
    r1 = await service.refine(snapshot_id=snapshot_id, user_text="为什么 hook 要这样？")
    assert r1.feedback_type == "challenge"
    assert r1.persisted_version is None
    assert "画像驱动" in r1.sources

    # adjust：不写盘
    r2 = await service.refine(snapshot_id=snapshot_id, user_text="hook 太苦情，改轻松点")
    assert r2.feedback_type == "adjust"
    assert r2.persisted_version is None

    # approve：写盘；submit_idea 已自动 finalize v1，首次 approve → v2
    r3 = await service.refine(snapshot_id=snapshot_id, user_text="行就这样吧")
    assert r3.feedback_type == "approve"
    assert r3.persisted_version == 2

    # 落盘文件确实存在（读最新版本）
    payload = service.get_snapshot_payload(snapshot_id=snapshot_id)
    StrategySnapshot.model_validate(payload)


# ---------------------------------------------------------------------------
# 3) SCORE bad JSON retry 后成功
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_json_validation(
    mock_bundle: Any,
    runtime_dir: Path,
    cache_path: Path,
) -> None:
    """SCORE 第一次返回坏 JSON → retry → 第二次合法 → 主流程继续。"""
    client = MockLLMClient()
    client.queue_default(responses=[MockResponseSpec(text="ANALYZE 文本")])
    client.queue("pro-thinking", marker="score", responses=[
        MockResponseSpec(text="this is not json"),  # 第一次：parse fail
        MockResponseSpec(text=json.dumps(SCORE_JSON, ensure_ascii=False)),  # 第二次：合法
    ])
    client.queue("pro-thinking", marker="strategize", responses=[
        MockResponseSpec(text=json.dumps(STRATEGIZE_JSON, ensure_ascii=False)),
    ])
    client.queue("flash-thinking", marker="present", responses=[
        MockResponseSpec(text=PRESENT_TEXT_OK, stream_chunk_chars=30),
    ])

    service = _make_service(
        client=client, runtime_dir=runtime_dir, cache_path=cache_path, mock_bundle=mock_bundle
    )
    done = await _drain(service, idea_text="考研期间一日三餐怎么吃才能不困")
    assert done["result"]["strategy_draft"]["heat_analysis"]["trend_score"] == pytest.approx(0.82)


# ---------------------------------------------------------------------------
# 4) PRESENT source tag 缺失 → retry → fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_source_tag_enforcement(
    mock_bundle: Any,
    runtime_dir: Path,
    cache_path: Path,
) -> None:
    """PRESENT 第一次无 SOURCES → retry 仍无 → fallback 注入。"""
    client = MockLLMClient()
    client.queue_default(responses=[MockResponseSpec(text="ANALYZE 文本")])
    client.queue("pro-thinking", marker="score", responses=[
        MockResponseSpec(text=json.dumps(SCORE_JSON, ensure_ascii=False)),
    ])
    client.queue("pro-thinking", marker="strategize", responses=[
        MockResponseSpec(text=json.dumps(STRATEGIZE_JSON, ensure_ascii=False)),
    ])
    # PRESENT 第一次 + retry 都没 SOURCES
    client.queue("flash-thinking", marker="present", responses=[
        MockResponseSpec(text=PRESENT_TEXT_NO_SOURCES, stream_chunk_chars=30),
        MockResponseSpec(text=PRESENT_TEXT_NO_SOURCES, stream_chunk_chars=30),
    ])

    service = _make_service(
        client=client, runtime_dir=runtime_dir, cache_path=cache_path, mock_bundle=mock_bundle
    )
    done = await _drain(service, idea_text="考研期间一日三餐怎么吃才能不困")
    assert done["result"]["sources"] == [FALLBACK_SOURCE_TAG]
    # 不抛错，主流程继续
    assert done["result"]["strategy_draft"]["execution"]["cta"] != ""


# ---------------------------------------------------------------------------
# 5) snapshot 落盘 + GET 取回
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_persistence(
    mock_bundle: Any,
    runtime_dir: Path,
    cache_path: Path,
) -> None:
    """FINALIZE 写 ``runtime_data/strategy_snapshot_*.json``，可被 GET 读到。"""
    client = MockLLMClient()
    _seed_full_flow_fixtures(client)
    client.queue("flash", marker="refine_classify", responses=[
        MockResponseSpec(text=json.dumps({"feedback_type": "approve"})),
    ])
    client.queue("flash-thinking", marker="refine_reply", responses=[
        MockResponseSpec(text=REFINE_REPLY_APPROVE, stream_chunk_chars=30),
    ])

    service = _make_service(
        client=client, runtime_dir=runtime_dir, cache_path=cache_path, mock_bundle=mock_bundle
    )
    done = await _drain(service, idea_text="考研期间一日三餐怎么吃才能不困")
    snapshot_id = done["snapshot_id"]

    # submit_idea 已自动 finalize v1；approve refine → v2
    r = await service.refine(snapshot_id=snapshot_id, user_text="行")
    assert r.persisted_version == 2
    files = sorted(runtime_dir.glob("strategy_snapshot_*.json"))
    assert any(snapshot_id in p.name for p in files)
    payload = service.get_snapshot_payload(snapshot_id=snapshot_id)
    assert payload["strategy_id"] == snapshot_id
    assert payload["input"]["user_idea"] == "考研期间一日三餐怎么吃才能不困"
    # pydantic 严格校验通过
    StrategySnapshot.model_validate(payload)
