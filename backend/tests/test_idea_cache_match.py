"""验证 _load_cache_demo_idea / _idea_matches_cache 逻辑。

确保：
- 默认 demo idea 命中 cache
- 用户改了 idea 不命中 cache（走 live LLM）
- 老版本 cache 无 demo_idea 字段时保持原行为（始终命中）
"""
import json
import tempfile
from pathlib import Path

import pytest

from backend.agents.strategy.service import StrategyService, StrategyServiceConfig


def _make_service(cache_data: dict) -> StrategyService:
    """构造一个只注入了 cache 相关状态的最小 StrategyService。"""
    td = tempfile.mkdtemp()
    cache_path = Path(td) / "strategy_score_strategize.json"
    cache_path.write_text(json.dumps(cache_data), encoding="utf-8")
    cfg = StrategyServiceConfig(
        use_cached_analysis=True,
        cache_path=cache_path,
        runtime_dir=Path(td) / "runtime_data",
    )
    svc = StrategyService.__new__(StrategyService)
    svc._client = None  # type: ignore[assignment]
    svc._cfg = cfg
    svc._mock = object()  # type: ignore[assignment]
    svc._sessions = {}
    svc._snapshots = {}
    svc._snapshot_versions = {}
    cfg.runtime_dir.mkdir(parents=True, exist_ok=True)
    svc._cache_demo_idea = svc._load_cache_demo_idea()
    return svc


def test_default_idea_matches() -> None:
    """默认 demo idea 包含 demo_idea 关键词 → 应命中 cache。"""
    svc = _make_service({"demo_idea": "考研期间一日三餐怎么吃才能不困"})
    default = "下一期想拍：「考研期间一日三餐怎么吃才能不困」— 用半纪录片半干货的口吻。"
    assert svc._idea_matches_cache(default)


def test_different_idea_no_match() -> None:
    """用户提交不同 idea → 不应命中 cache，应走 live LLM。"""
    svc = _make_service({"demo_idea": "考研期间一日三餐怎么吃才能不困"})
    assert not svc._idea_matches_cache("我想拍一期关于学习方法的视频")
    assert not svc._idea_matches_cache("如何在宿舍做一顿低成本早餐")


def test_no_demo_idea_field_always_matches() -> None:
    """老版本 cache 无 demo_idea / idea_key 字段 → 保持原行为（始终命中）。"""
    svc = _make_service({"score_output": {}})
    assert svc._idea_matches_cache("任何 idea 都应命中，保持向后兼容")


def test_idea_key_fallback() -> None:
    """只有 idea_key 字段时也能正常匹配。"""
    svc = _make_service({"idea_key": "考研一日三餐"})
    assert svc._idea_matches_cache("考研一日三餐怎么吃才能不困")
    assert not svc._idea_matches_cache("如何拍出高质量 vlog")


def test_missing_cache_file_always_matches() -> None:
    """cache 文件不存在时 _cache_demo_idea 为空 → 保持原行为（始终命中）。"""
    td = tempfile.mkdtemp()
    cfg = StrategyServiceConfig(
        use_cached_analysis=True,
        cache_path=Path(td) / "nonexistent.json",
        runtime_dir=Path(td) / "runtime_data",
    )
    svc = StrategyService.__new__(StrategyService)
    svc._client = None  # type: ignore[assignment]
    svc._cfg = cfg
    svc._mock = object()  # type: ignore[assignment]
    svc._sessions = {}
    svc._snapshots = {}
    svc._snapshot_versions = {}
    Path(td, "runtime_data").mkdir(parents=True, exist_ok=True)
    svc._cache_demo_idea = svc._load_cache_demo_idea()
    assert svc._idea_matches_cache("任意内容")
