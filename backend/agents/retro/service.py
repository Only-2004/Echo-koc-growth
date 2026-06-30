"""RetroService 门面：state_machine + handlers + memory + storage 的拼装。

API 层（``backend/api/retro.py``）只与 RetroService 交互。

存储约定
--------
- 输入 mock：``backend/mock_data/{strategy_snapshot,profile,...}``
- 运行时输出：``runtime_data/insights_report_{report_id}.json``
                  ``runtime_data/profile_v{n}.json``
- 缓存：``cache/retro_synthesis.json``

如果 ``settings.use_cached_analysis`` 为 True 且缓存存在，
COMPARE / ATTRIBUTE / EXTRACT_SIGNALS / SYNTHESIZE 全部走缓存。
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from backend.config import Settings
from backend.schemas import (
    InsightsReport,
    Profile,
    ProfileDelta,
    StrategySnapshot,
)

from .._llm import LLMClient
from . import handlers
from .memory import RetroMemory
from .profile_merger import merge_profile_delta
from .state_machine import RetroState, RetroStateMachine

_log = structlog.get_logger("retro.service")

# 项目根（worktree 内 = ``...backend/`` 的上一级）
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MOCK_DIR = _BACKEND_ROOT / "mock_data"
_CACHE_DIR = _PROJECT_ROOT / "cache"
_RUNTIME_DIR = _PROJECT_ROOT / "runtime_data"


class RetroService:
    """Retro agent 门面。

    每次复盘新建一个 ``RetroSession`` 实例（持有 memory / fsm），不跨 session 共享。
    """

    def __init__(
        self,
        *,
        llm: LLMClient,
        settings: Settings,
        cache_dir: Path | None = None,
        runtime_dir: Path | None = None,
        mock_dir: Path | None = None,
    ) -> None:
        """构造 service。

        Parameters
        ----------
        llm : LLMClient
            模型客户端。
        settings : Settings
            应用配置。
        cache_dir : Path, optional
            缓存目录（默认 ``cache/``）。
        runtime_dir : Path, optional
            运行时输出目录（默认 ``runtime_data/``）。
        mock_dir : Path, optional
            mock 数据目录（默认 ``backend/mock_data/``）。
        """
        self.llm = llm
        self.settings = settings
        self.cache_dir = cache_dir or _CACHE_DIR
        self.runtime_dir = runtime_dir or _RUNTIME_DIR
        self.mock_dir = mock_dir or _MOCK_DIR
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

    # ------------- 公共入口 -------------

    def new_session(self, *, use_cache: bool | None = None) -> RetroSession:
        """创建一次新的复盘会话。

        Parameters
        ----------
        use_cache : bool, optional
            是否走预跑缓存（覆盖 ``settings.use_cached_analysis``）。``None`` 时
            回退默认。前端 toggle ``mode=cache|live`` 通过路由透传。
        """
        return RetroSession(service=self, use_cache=use_cache)


class RetroSession:
    """一次具体的 retro 会话状态。"""

    def __init__(
        self,
        *,
        service: RetroService,
        use_cache: bool | None = None,
    ) -> None:
        self.service = service
        self.fsm = RetroStateMachine()
        self.memory = RetroMemory()
        self.report_id = "rpt_" + uuid.uuid4().hex[:8]
        self.report: InsightsReport | None = None
        self._use_cache_override = use_cache
        # 缓存命中时存储预生成的 PRESENT 文本，stream_present_typed 直接 yield
        # 避免 PRESENT 阶段的 live LLM 调用（演示路径强制无 LLM）
        self._cached_present_text: str | None = None
        self._log = structlog.get_logger("retro.session").bind(report_id=self.report_id)

    # ------------- LOAD -------------

    def load_inputs(
        self,
        *,
        video_id: str,
        profile: Profile,
        strategy_snapshot: StrategySnapshot,
        video: dict[str, Any],
        baseline: dict[str, Any],
    ) -> None:
        """LOAD 阶段：把全部输入装载进 memory。"""
        self.memory.inputs = {
            "video_id": video_id,
            "profile": profile.model_dump(mode="json"),
            "strategy_snapshot": strategy_snapshot.model_dump(mode="json"),
            "video": video,
            "baseline": baseline,
        }
        self._log.info("retro.load.ok", video_id=video_id)

    # ------------- COMPARE → SYNTHESIZE （含缓存） -------------

    async def run_analysis_phases(self) -> dict[str, Any]:
        """跑完 COMPARE → ATTRIBUTE → EXTRACT_SIGNALS → SYNTHESIZE。

        Returns
        -------
        dict[str, Any]
            ``insights_report_draft`` 的 dict（不含 profile_delta）。
        """
        cache = self._maybe_load_cache()
        # COMPARE
        self.fsm.transition(RetroState.COMPARE)
        if cache is not None:
            self.memory.comparison_grid = cache["compare_output"]
        else:
            await handlers.run_compare(llm=self.service.llm, memory=self.memory)
        # ATTRIBUTE
        self.fsm.transition(RetroState.ATTRIBUTE)
        if cache is not None:
            self.memory.attributions = cache["attribute_output"]
        else:
            await handlers.run_attribute(llm=self.service.llm, memory=self.memory)
        # EXTRACT_SIGNALS
        self.fsm.transition(RetroState.EXTRACT_SIGNALS)
        if cache is not None:
            self.memory.audience_signals = cache["extract_signals_output"]
        else:
            await handlers.run_extract_signals(llm=self.service.llm, memory=self.memory)
        # SYNTHESIZE
        self.fsm.transition(RetroState.SYNTHESIZE)
        if cache is not None:
            self.memory.insights_report_draft = cache["synthesize_output"]
        else:
            await handlers.run_synthesize(llm=self.service.llm, memory=self.memory)
        assert self.memory.insights_report_draft is not None
        return self.memory.insights_report_draft

    async def run_analysis_phases_streaming(self) -> AsyncIterator[tuple[str, str]]:
        """run_analysis_phases 的流式版：同时 yield ("stage", name) 和 ("thinking", chunk)。

        cache 命中时跳过 LLM，不产生 thinking 事件（直接发 stage 通知）。
        live 时每个阶段实时 yield 思考过程。

        Yields
        ------
        tuple[str, str]
            ("stage", stage_name) 阶段切换通知。
            ("thinking", chunk) LLM 推理过程片段（仅 live 模式）。
        """
        cache = self._maybe_load_cache()

        self.fsm.transition(RetroState.COMPARE)
        yield "stage", "COMPARE"
        if cache is not None:
            self.memory.comparison_grid = cache["compare_output"]
        else:
            async for ev in handlers.run_compare_streaming(llm=self.service.llm, memory=self.memory):
                yield ev

        self.fsm.transition(RetroState.ATTRIBUTE)
        yield "stage", "ATTRIBUTE"
        if cache is not None:
            self.memory.attributions = cache["attribute_output"]
        else:
            async for ev in handlers.run_attribute_streaming(llm=self.service.llm, memory=self.memory):
                yield ev

        self.fsm.transition(RetroState.EXTRACT_SIGNALS)
        yield "stage", "EXTRACT_SIGNALS"
        if cache is not None:
            self.memory.audience_signals = cache["extract_signals_output"]
        else:
            async for ev in handlers.run_extract_signals_streaming(llm=self.service.llm, memory=self.memory):
                yield ev

        self.fsm.transition(RetroState.SYNTHESIZE)
        yield "stage", "SYNTHESIZE"
        if cache is not None:
            self.memory.insights_report_draft = cache["synthesize_output"]
        else:
            async for ev in handlers.run_synthesize_streaming(llm=self.service.llm, memory=self.memory):
                yield ev

        assert self.memory.insights_report_draft is not None

    def save_cache(self) -> None:
        """把本次在线分析结果写入 per-video cache 文件。

        文件命名：``cache/retro_synthesis_{video_id}.json``。
        由 API 层在 live 模式分析完成后调用，确保下次同一 video 可走缓存。
        """
        if self.memory.insights_report_draft is None:
            return
        video_id = self.memory.inputs.get("video_id")
        data = {
            "video_id": video_id,
            "compare_output": self.memory.comparison_grid,
            "attribute_output": self.memory.attributions,
            "extract_signals_output": self.memory.audience_signals,
            "synthesize_output": self.memory.insights_report_draft,
        }
        path = self._cache_path(video_id)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        self._log.info("retro.cache.saved", path=str(path), video_id=video_id)

    def inject_analysis_results(self, bg_data: dict[str, Any]) -> None:
        """注入后台预分析结果，跳过 LLM 四阶段直接进入 PRESENT。

        Parameters
        ----------
        bg_data : dict
            包含 compare_output / attribute_output /
            extract_signals_output / synthesize_output 四个键。
        """
        self.fsm.transition(RetroState.COMPARE)
        self.memory.comparison_grid = bg_data["compare_output"]
        self.fsm.transition(RetroState.ATTRIBUTE)
        self.memory.attributions = bg_data["attribute_output"]
        self.fsm.transition(RetroState.EXTRACT_SIGNALS)
        self.memory.audience_signals = bg_data["extract_signals_output"]
        self.fsm.transition(RetroState.SYNTHESIZE)
        self.memory.insights_report_draft = bg_data["synthesize_output"]

    def _cache_path(self, video_id: str | None) -> Path:
        """返回该 video 对应的 per-video cache 路径。"""
        if video_id:
            return self.service.cache_dir / f"retro_synthesis_{video_id}.json"
        return self.service.cache_dir / "retro_synthesis.json"

    def _maybe_load_cache(self) -> dict[str, Any] | None:
        """若 use_cache 为 True 且缓存存在，返回缓存内容。

        查找优先级：
        1. ``cache/retro_synthesis_{video_id}.json``（per-video）
        2. ``cache/retro_synthesis.json``（legacy，仅当 video_id 匹配时使用）
        """
        effective_cache = (
            self.service.settings.use_cached_analysis
            if self._use_cache_override is None
            else self._use_cache_override
        )
        if not effective_cache:
            return None
        video_id = self.memory.inputs.get("video_id") if self.memory.inputs else None

        # 候选路径列表（优先 per-video）
        candidates: list[tuple[Path, bool]] = []
        if video_id:
            candidates.append((self._cache_path(video_id), False))
        # legacy fallback：需要 video_id 匹配校验
        candidates.append((self.service.cache_dir / "retro_synthesis.json", True))

        for path, need_id_check in candidates:
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._log.warning("retro.cache.invalid", path=str(path), err=str(exc))
                continue
            if need_id_check and data.get("video_id") != video_id:
                self._log.info(
                    "retro.cache.video_mismatch",
                    cache_video=data.get("video_id"),
                    load_video=video_id,
                )
                continue
            # 捕获 present_text（如有），供 stream_present_typed 使用
            present = data.get("present_text")
            if isinstance(present, str) and present.strip():
                self._cached_present_text = present
            self._log.info("retro.cache.hit", path=str(path))
            return data

        self._log.warning("retro.cache.missing", video_id=video_id)
        return None

    # ------------- PRESENT -------------

    async def stream_present(self) -> AsyncIterator[str]:
        """PRESENT 阶段流式总览（仅 content）。"""
        self.fsm.transition(RetroState.PRESENT)
        async for chunk in handlers.stream_present(
            llm=self.service.llm, memory=self.memory
        ):
            yield chunk

    async def stream_present_typed(self) -> AsyncIterator[tuple[str, str]]:
        """PRESENT 阶段（typed 版，含思考过程）。

        若 ``_cached_present_text`` 已被 ``_maybe_load_cache`` 写入，
        直接 yield 缓存文本，跳过 LLM 调用（演示路径强制无 LLM）。

        Yields
        ------
        tuple[str, str]
            ``("thinking", chunk)`` 实时思考片段；``("content", full_text)`` 最终正文。
        """
        self.fsm.transition(RetroState.PRESENT)
        if self._cached_present_text:
            self.memory.presentation_text = self._cached_present_text
            yield "content", self._cached_present_text
            return
        async for chunk_type, chunk in handlers.stream_present_typed(
            llm=self.service.llm, memory=self.memory
        ):
            yield chunk_type, chunk

    # ------------- DRILL -------------

    async def stream_drill(
        self,
        *,
        element_id: str,
        element_type: str,
        user_text: str,
    ) -> AsyncIterator[str]:
        """DRILL 阶段（可循环）。"""
        if self.fsm.state != RetroState.DRILL:
            self.fsm.transition(RetroState.DRILL)
        async for chunk in handlers.stream_drill(
            llm=self.service.llm,
            memory=self.memory,
            element_id=element_id,
            element_type=element_type,
            user_text=user_text,
        ):
            yield chunk

    # ------------- UPDATE_PROFILE -------------

    async def update_profile(self, *, profile_in: Profile) -> tuple[ProfileDelta, Profile]:
        """UPDATE_PROFILE 阶段：生成 ProfileDelta 并合并到 v_(in+1)。

        Returns
        -------
        (ProfileDelta, Profile)
            delta 与新版 Profile（已通过 schema）。
        """
        self.fsm.transition(RetroState.UPDATE_PROFILE)
        delta_dict = await handlers.run_update_profile(
            llm=self.service.llm, memory=self.memory
        )
        delta = ProfileDelta.model_validate(delta_dict)
        new_profile = merge_profile_delta(profile_in=profile_in, delta=delta)
        return delta, new_profile

    # ------------- FINALIZE -------------

    def finalize(
        self,
        *,
        user_id: str,
        video_id: str,
        strategy_id: str,
        profile_version_in: int,
        profile_delta: ProfileDelta | None = None,
    ) -> InsightsReport:
        """FINALIZE：组装最终 InsightsReport，pydantic 校验后写盘。"""
        if self.memory.insights_report_draft is None:
            raise RuntimeError("FINALIZE 前必须先跑过 SYNTHESIZE")
        draft = dict(self.memory.insights_report_draft)
        report = InsightsReport.model_validate(
            {
                "report_id": self.report_id,
                "user_id": user_id,
                "video_id": video_id,
                "strategy_id": strategy_id,
                "profile_version_in": profile_version_in,
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
                "data_cards": draft["data_cards"],
                "strategy_review": draft["strategy_review"],
                "insights": draft["insights"],
                "audience_signals": draft["audience_signals"],
                "suggestions": draft["suggestions"],
                "profile_delta": profile_delta.model_dump(mode="json") if profile_delta else None,
            }
        )
        self.fsm.transition(RetroState.FINALIZE)
        self.report = report
        self._write_report(report)
        return report

    def _write_report(self, report: InsightsReport) -> None:
        """把 InsightsReport 落盘到 ``runtime_data/insights_report_{id}.json``。"""
        path = self.service.runtime_dir / f"insights_report_{report.report_id}.json"
        path.write_text(
            report.model_dump_json(indent=2, exclude_none=False),
            encoding="utf-8",
        )
        self._log.info("retro.report.written", path=str(path))

    def write_profile(self, profile: Profile) -> Path:
        """把新版 Profile 落盘到 ``runtime_data/profile_v{n}.json``。"""
        path = self.service.runtime_dir / f"profile_v{profile.meta.version}.json"
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        self._log.info(
            "retro.profile.written", path=str(path), version=profile.meta.version
        )
        return path
