"""StrategyService：Strategy Agent 对外门面。

职责
====

1. 编排八状态 FSM：``submit_idea`` 一次性走 RECEIVE_IDEA → … → PRESENT，
   PRESENT 用 async generator 流式返回；FINALIZE 由 ``finalize_snapshot`` 触发。
2. 缓存兜底：``USE_CACHED_ANALYSIS=true`` 时 SCORE + STRATEGIZE 直接读
   ``cache/strategy_score_strategize.json``，跳过两次 pro-thinking 调用。
3. JSON retry：SCORE / STRATEGIZE / GENERATE_IDEAS 解析失败 retry 1 次；
   仍失败时降级到 cache（演示稳定性最高优先级）。
4. Source tag 强约束：PRESENT / REFINE 文本若没有 SOURCES 行 → retry 1 次
   附加 system 约束；仍无则 fallback 注入 ``["画像驱动"]``，绝不抛异常。
5. 落库：FINALIZE 把 strategy_draft 组装成 :class:`StrategySnapshot` 通过
   pydantic 校验后写 ``runtime_data/strategy_snapshot_{id}.json``；版本化命名
   为 ``strategy_snapshot_{id}_v{n}.json`` 以支持 approve 落多次。
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from ...schemas import (
    DifferentiationPoint,
    Execution,
    HeatAnalysis,
    HookDesign,
    IdeaSummary,
    PersonaLeveragePoint,
    PillarAlignment,
    ProfileFit,
    SourceTag,
    StrategyInput,
    StrategySnapshot,
    ToExploreValidation,
)
from .._llm.client import LLMClient
from . import handlers as H
from .memory import ConversationTurn, StrategyShortTermMemory, StrategyWorkingMemory
from .state_machine import StrategyState, assert_can_transition

_LOGGER = structlog.get_logger(__name__)

VALID_SOURCE_TAGS: set[str] = {"画像驱动", "趋势驱动", "数据驱动", "历史复盘", "用户偏好驱动"}
FALLBACK_SOURCE_TAG: str = "画像驱动"

_VALID_ALIGNMENT_LEVELS: set[str] = {"high", "medium", "low"}


def _coerce_alignment(raw: object) -> str:
    """把 alignment 值规整到 high/medium/low；老格式数值或非法值兜底。

    Parameters
    ----------
    raw : object
        prompt 输出的 alignment（新格式字符串，老缓存可能仍是 0-1 浮点）。

    Returns
    -------
    str
        ``"high"`` | ``"medium"`` | ``"low"``。

    Notes
    -----
    迁移期兜底：浮点 ≥0.7 → high，0.4-0.7 → medium，<0.4 → low。
    非字符串非数字 → ``"medium"`` 中性兜底。
    """
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in _VALID_ALIGNMENT_LEVELS:
            return normalized
    if isinstance(raw, (int, float)):
        if raw >= 0.7:
            return "high"
        if raw >= 0.4:
            return "medium"
        return "low"
    return "medium"


@dataclass(frozen=True, slots=True)
class StrategyServiceConfig:
    """Service 运行配置。

    Attributes
    ----------
    use_cached_analysis : bool
        True 时 SCORE + STRATEGIZE 走 cache。
    cache_path : Path
        预跑结果文件路径。
    runtime_dir : Path
        snapshot 持久化目录。
    """

    use_cached_analysis: bool
    cache_path: Path
    runtime_dir: Path


@dataclass
class PresentResult:
    """``submit_idea`` 收尾时给 caller 的结构。"""

    snapshot_id: str
    """新建的 strategy snapshot id（用于后续 refine / finalize）。"""
    final_text: str
    """PRESENT 拼接后的完整文本。"""
    sources: list[str]
    """从 PRESENT 文本里解析出的 source tags（保证 ≥ 1）。"""
    strategy_draft: dict[str, Any]
    """合并后的 draft（heat + fit + idea_summary + differentiation + execution）。"""


@dataclass
class RefineResult:
    """``refine`` 的返回结构。"""

    snapshot_id: str
    feedback_type: str
    """``"challenge"`` / ``"adjust"`` / ``"approve"``。"""
    final_text: str
    sources: list[str]
    persisted_version: int | None
    """若 approve 触发新版本落库，返回新版本号；否则 None。"""


# ---------------------------------------------------------------------------
# StrategyService
# ---------------------------------------------------------------------------


class StrategyService:
    """Strategy Agent 对外接口。

    每个 session 创建一个新实例（demo 单 persona 时也可复用，因为内部不暂存跨
    session 状态——working memory 用 session_id 索引；snapshot 写盘后即与实例解耦）。
    """

    def __init__(
        self,
        *,
        client: LLMClient,
        config: StrategyServiceConfig,
        mock_bundle: Any,
    ) -> None:
        """构造 service。

        Parameters
        ----------
        client : LLMClient
            LLM 客户端（DeepSeek / Mock）。
        config : StrategyServiceConfig
            运行配置。
        mock_bundle : MockBundle
            ``backend.mock_loader.MockBundle`` 实例，提供 trends / videos。
            （demo 单 persona，profile_v1 也从这里 derive 一份 stub。）
        """
        self._client = client
        self._cfg = config
        self._mock = mock_bundle
        self._sessions: dict[str, StrategyWorkingMemory] = {}
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._snapshot_versions: dict[str, int] = {}
        self._cfg.runtime_dir.mkdir(parents=True, exist_ok=True)
        # 预跑缓存对应的 demo idea 关键词（用于 idea 匹配检测）
        self._cache_demo_idea: str = self._load_cache_demo_idea()

    # ------------------------------------------------------------------
    # 公开入口：submit / refine / finalize
    # ------------------------------------------------------------------

    async def submit_idea(
        self,
        *,
        idea_text: str,
        profile: dict[str, Any] | None = None,
        use_cache: bool | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """idea-driven 主流程。返回 async generator，逐事件 yield。

        事件结构（dict）::

            {"event": "state",   "state": "ANALYZE_IDEA"}
            {"event": "state",   "state": "SCORE"}
            {"event": "state",   "state": "STRATEGIZE"}
            {"event": "state",   "state": "PRESENT"}
            {"event": "delta",   "text": "..."}
            ...
            {"event": "done",    "snapshot_id": "...", "result": {...}}

        Parameters
        ----------
        idea_text : str
            用户提交的 idea 原文。
        profile : dict, optional
            profile_v1（onboarding 输出）。缺失时用 ``_stub_profile`` 兜底。
        use_cache : bool, optional
            是否走预跑缓存（覆盖 ``cfg.use_cached_analysis``）。``None`` 时回退默认。
            前端 toggle ``mode=cache|live`` 通过路由透传。
        """
        effective_cache = (
            self._cfg.use_cached_analysis if use_cache is None else use_cache
        )
        snapshot_id = "str_" + uuid.uuid4().hex[:10]
        working = StrategyWorkingMemory(session_id=snapshot_id)
        working.full_profile = profile or self._stub_profile()
        working.full_trends = [t.model_dump(mode="json") for t in self._mock.external_trends.trends]
        self._sessions[snapshot_id] = working

        # 1) RECEIVE_IDEA → ANALYZE_IDEA
        state = StrategyState.RECEIVE_IDEA
        yield {"event": "state", "state": state.value, "snapshot_id": snapshot_id}

        next_state = StrategyState.ANALYZE_IDEA
        assert_can_transition(state, next_state)
        state = next_state
        short = self._build_short_term(working, current_idea=idea_text, current_state=state)
        yield {"event": "state", "state": state.value}
        analysis = await H.handle_analyze_idea(short=short, client=self._client)
        working.append_turn(ConversationTurn(role="agent", text=analysis, sources=[]))

        # 2) SCORE
        next_state = StrategyState.SCORE
        assert_can_transition(state, next_state)
        state = next_state
        short.current_state = state
        yield {"event": "state", "state": state.value}
        use_cache_for_idea = effective_cache and self._idea_matches_cache(idea_text)
        if use_cache_for_idea:
            score_out = await self._run_score_with_cache(short, use_cache=True)
        else:
            # Live LLM：inline 流式，实时把思考 token yield 到 SSE 流，保留 1 次 retry
            score_out = None
            for _attempt in range(2):
                _score_parts: list[str] = []
                async for _chunk_type, _chunk in H.stream_score_typed(short=short, client=self._client):
                    if _chunk_type == "thinking":
                        yield {"event": "thinking.delta", "text": _chunk}
                    else:
                        _score_parts.append(_chunk)
                try:
                    score_out = json.loads("".join(_score_parts))
                    break
                except (json.JSONDecodeError, ValueError):
                    _LOGGER.warning("strategy.score.live_json_fail", attempt=_attempt + 1)
            if score_out is None:
                _LOGGER.warning("strategy.score.live_json_fail.fallback_cache")
                score_out = self._read_cache_section("score_output") or {}
        working.strategy_draft.update(score_out)

        # 3) STRATEGIZE
        next_state = StrategyState.STRATEGIZE
        assert_can_transition(state, next_state)
        state = next_state
        short.current_state = state
        short.strategy_draft = working.strategy_draft
        yield {"event": "state", "state": state.value}
        top_videos = self._select_top_videos_for_idea(idea_text)
        if use_cache_for_idea:
            strategize_out = await self._run_strategize_with_cache(
                short, top_videos=top_videos, use_cache=True
            )
        else:
            # Live LLM：inline 流式，实时把思考 token yield 到 SSE 流，保留 1 次 retry
            strategize_out = None
            for _attempt in range(2):
                _strat_parts: list[str] = []
                async for _chunk_type, _chunk in H.stream_strategize_typed(
                    short=short, client=self._client, top_videos=top_videos
                ):
                    if _chunk_type == "thinking":
                        yield {"event": "thinking.delta", "text": _chunk}
                    else:
                        _strat_parts.append(_chunk)
                try:
                    strategize_out = json.loads("".join(_strat_parts))
                    break
                except (json.JSONDecodeError, ValueError):
                    _LOGGER.warning("strategy.strategize.live_json_fail", attempt=_attempt + 1)
            if strategize_out is None:
                _LOGGER.warning("strategy.strategize.live_json_fail.fallback_cache")
                strategize_out = self._read_cache_section("strategize_output") or {}
        working.strategy_draft.update(strategize_out)

        # 4) PRESENT（流式，含思考过程）
        next_state = StrategyState.PRESENT
        assert_can_transition(state, next_state)
        state = next_state
        short.current_state = state
        short.strategy_draft = working.strategy_draft
        yield {"event": "state", "state": state.value}

        # 用 stream_typed 实时 yield 思考 token，content 收集后统一做 source 校验
        content_parts: list[str] = []
        async for chunk_type, chunk in H.stream_present_typed(strategy_draft=working.strategy_draft, client=self._client):
            if chunk_type == "thinking":
                yield {"event": "thinking.delta", "text": chunk}
            else:
                content_parts.append(chunk)

        raw_content = "".join(content_parts)
        sources = self._parse_sources(raw_content)
        if not sources:
            _LOGGER.warning("strategy.present.no_source_tag.retry")
            retry_raw = await self._collect_stream(
                H.stream_present(
                    strategy_draft=working.strategy_draft,
                    client=self._client,
                    extra_constraint="必须在文末追加 SOURCES: 行，至少包含 1 个 source tag。",
                )
            )
            retry_sources = self._parse_sources(retry_raw)
            if retry_sources:
                raw_content, sources = retry_raw, retry_sources
            else:
                _LOGGER.warning("strategy.present.no_source_tag.fallback")
                sources = [FALLBACK_SOURCE_TAG]

        full_text = self._strip_sources_line(raw_content)
        yield {"event": "delta", "text": full_text}

        working.append_turn(ConversationTurn(role="agent", text=full_text, sources=sources))

        # 缓存到 service 实例，供 refine / finalize 使用
        self._snapshots[snapshot_id] = dict(working.strategy_draft)
        self._snapshots[snapshot_id]["__user_idea"] = idea_text
        self._snapshots[snapshot_id]["__user_id"] = working.full_profile.get("meta", {}).get(
            "user_id", "user_a_001"
        )
        self._snapshots[snapshot_id]["__profile_version"] = working.full_profile.get("meta", {}).get(
            "version", 1
        )
        self._snapshot_versions[snapshot_id] = 0

        # 立即落库（v1），确保 GET /snapshot/{id} 在 done 事件后不会 404
        await self._finalize_and_persist(snapshot_id)

        result = PresentResult(
            snapshot_id=snapshot_id,
            final_text=full_text,
            sources=sources,
            strategy_draft=dict(working.strategy_draft),
        )
        yield {
            "event": "done",
            "snapshot_id": snapshot_id,
            "result": {
                "final_text": result.final_text,
                "sources": result.sources,
                "strategy_draft": result.strategy_draft,
            },
        }

    async def refine(
        self,
        *,
        snapshot_id: str,
        user_text: str,
    ) -> RefineResult:
        """REFINE 阶段。

        步骤
        ----
        1. flash 分类 user_text → challenge / adjust / approve
        2. flash-thinking 流式生成回复 + source tag 校验
        3. approve → 落新版本 snapshot；challenge / adjust 仅追加对话
        """
        if snapshot_id not in self._snapshots:
            raise KeyError(f"snapshot_id 不存在：{snapshot_id}")
        draft = self._snapshots[snapshot_id]

        # 1) 分类
        feedback_type = await H.classify_refine_feedback(
            user_text=user_text,
            client=self._client,
        )

        # 2) 生成回复
        full_text, sources = await self._stream_refine_with_source_guard(
            strategy_draft={k: v for k, v in draft.items() if not k.startswith("__")},
            feedback_type=feedback_type,
            user_text=user_text,
        )

        # 3) approve 时落新版本
        persisted_version: int | None = None
        if feedback_type == "approve":
            persisted_version = await self._finalize_and_persist(snapshot_id)

        return RefineResult(
            snapshot_id=snapshot_id,
            feedback_type=feedback_type,
            final_text=full_text,
            sources=sources,
            persisted_version=persisted_version,
        )

    async def finalize(self, *, snapshot_id: str) -> int:
        """显式 FINALIZE：跳过 REFINE 的 approve 路径直接落库（API 备用）。"""
        if snapshot_id not in self._snapshots:
            raise KeyError(snapshot_id)
        return await self._finalize_and_persist(snapshot_id)

    def get_snapshot_payload(self, *, snapshot_id: str, version: int | None = None) -> dict[str, Any]:
        """读取已落库的 snapshot JSON。

        Parameters
        ----------
        snapshot_id : str
            snapshot id。
        version : int, optional
            指定版本；缺省读最新。
        """
        if version is None:
            version = self._snapshot_versions.get(snapshot_id, 1)
        path = self._snapshot_path(snapshot_id, version)
        if not path.exists():
            raise FileNotFoundError(path)
        return json.loads(path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # 内部：cache 兜底 + retry
    # ------------------------------------------------------------------

    async def _run_score_with_cache(
        self,
        short: StrategyShortTermMemory,
        *,
        use_cache: bool | None = None,
    ) -> dict[str, Any]:
        """SCORE 阶段：cache 优先（仅限 demo idea） → 在线调用 → JSON retry → cache 兜底。"""
        effective_cache = (
            self._cfg.use_cached_analysis if use_cache is None else use_cache
        )
        # 仅当 idea 与预跑缓存匹配时才走 cache；用户改了 idea 则走 live LLM
        if effective_cache and self._idea_matches_cache(short.current_idea):
            cached = self._read_cache_section("score_output")
            if cached is not None:
                _LOGGER.info("strategy.score.cache_hit", snapshot=short.current_state.value)
                return cached
        return await self._call_with_retry(
            primary=lambda: H.handle_score(short=short, client=self._client),
            fallback_section="score_output",
            stage="score",
        )

    async def _run_strategize_with_cache(
        self,
        short: StrategyShortTermMemory,
        *,
        top_videos: list[dict[str, Any]],
        use_cache: bool | None = None,
    ) -> dict[str, Any]:
        """STRATEGIZE 阶段：cache 优先（仅限 demo idea） → 在线 → retry → cache 兜底。"""
        effective_cache = (
            self._cfg.use_cached_analysis if use_cache is None else use_cache
        )
        # 仅当 idea 与预跑缓存匹配时才走 cache；用户改了 idea 则走 live LLM
        if effective_cache and self._idea_matches_cache(short.current_idea):
            cached = self._read_cache_section("strategize_output")
            if cached is not None:
                _LOGGER.info("strategy.strategize.cache_hit")
                return cached
        return await self._call_with_retry(
            primary=lambda: H.handle_strategize(short=short, client=self._client, top_videos=top_videos),
            fallback_section="strategize_output",
            stage="strategize",
        )

    async def _call_with_retry(
        self,
        *,
        primary: Any,
        fallback_section: str,
        stage: str,
    ) -> dict[str, Any]:
        """JSON 调用 + retry 1 次 + cache 兜底。"""
        try:
            return await primary()
        except (json.JSONDecodeError, ValueError) as exc:
            _LOGGER.warning("strategy.json_parse_fail.first", stage=stage, err=str(exc))
        # retry 1 次
        try:
            return await primary()
        except (json.JSONDecodeError, ValueError) as exc:
            _LOGGER.warning("strategy.json_parse_fail.retry", stage=stage, err=str(exc))
        # cache 兜底
        cached = self._read_cache_section(fallback_section)
        if cached is None:
            raise RuntimeError(f"{stage} 解析失败且无 cache 兜底")
        _LOGGER.warning("strategy.fallback_to_cache", stage=stage)
        return cached

    def _read_cache_section(self, section: str) -> dict[str, Any] | None:
        """从 cache/strategy_score_strategize.json 读指定 section。"""
        if not self._cfg.cache_path.exists():
            return None
        try:
            data = json.loads(self._cfg.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        out = data.get(section)
        if isinstance(out, dict):
            return out
        return None

    def _load_cache_demo_idea(self) -> str:
        """从 cache 文件读取 demo_idea / idea_key 关键词，供 idea 匹配检测使用。

        Returns
        -------
        str
            缓存文件里 demo_idea 字段（优先）或 idea_key；文件缺失时返回空字符串。
        """
        if not self._cfg.cache_path.exists():
            return ""
        try:
            data = json.loads(self._cfg.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ""
        return data.get("demo_idea", "") or data.get("idea_key", "")

    def _idea_matches_cache(self, idea_text: str) -> bool:
        """判断 idea_text 是否与预跑缓存的 demo idea 匹配。

        老版本 cache 无 demo_idea 字段时返回 True（保持原行为）。

        Parameters
        ----------
        idea_text : str
            用户提交的 idea 原文。

        Returns
        -------
        bool
            True → 命中缓存；False → 绕过缓存走 live LLM。
        """
        if not self._cache_demo_idea:
            return True  # 老版 cache 无字段，保持原行为
        return self._cache_demo_idea in idea_text

    # ------------------------------------------------------------------
    # 内部：source tag 强约束
    # ------------------------------------------------------------------

    async def _stream_present_with_source_guard(
        self,
        *,
        strategy_draft: dict[str, Any],
    ) -> tuple[str, list[str]]:
        """PRESENT 流式 + source 校验 + retry + fallback。

        Returns
        -------
        (text, sources)
            text 为完整拼接文本（含 SOURCES 行）；sources 为解析出的 tag 列表（≥ 1）。
        """
        # 第一次
        text = await self._collect_stream(
            H.stream_present(strategy_draft=strategy_draft, client=self._client)
        )
        sources = self._parse_sources(text)
        if sources:
            return self._strip_sources_line(text), sources

        # retry 1 次，附加约束
        _LOGGER.warning("strategy.present.no_source_tag.retry")
        text = await self._collect_stream(
            H.stream_present(
                strategy_draft=strategy_draft,
                client=self._client,
                extra_constraint="必须在文末追加 SOURCES: 行，至少包含 1 个 source tag。",
            )
        )
        sources = self._parse_sources(text)
        if sources:
            return self._strip_sources_line(text), sources

        # fallback：注入默认 tag，不抛错
        _LOGGER.warning("strategy.present.no_source_tag.fallback")
        return text, [FALLBACK_SOURCE_TAG]

    async def _stream_refine_with_source_guard(
        self,
        *,
        strategy_draft: dict[str, Any],
        feedback_type: str,
        user_text: str,
    ) -> tuple[str, list[str]]:
        """REFINE 流式 + source 校验 + retry + fallback。"""
        text = await self._collect_stream(
            H.stream_refine_reply(
                strategy_draft=strategy_draft,
                feedback_type=feedback_type,
                user_text=user_text,
                client=self._client,
            )
        )
        sources = self._parse_sources(text)
        if sources:
            return self._strip_sources_line(text), sources

        text = await self._collect_stream(
            H.stream_refine_reply(
                strategy_draft=strategy_draft,
                feedback_type=feedback_type,
                user_text=user_text,
                client=self._client,
                extra_constraint="必须在文末追加 SOURCES: 行，至少 1 个 tag。",
            )
        )
        sources = self._parse_sources(text)
        if sources:
            return self._strip_sources_line(text), sources

        return text, [FALLBACK_SOURCE_TAG]

    @staticmethod
    async def _collect_stream(stream: AsyncIterator[str]) -> str:
        """把 async generator 拼成完整字符串。"""
        chunks: list[str] = []
        async for c in stream:
            chunks.append(c)
        return "".join(chunks)

    _SOURCES_RE = re.compile(r"^\s*SOURCES\s*:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)

    @classmethod
    def _parse_sources(cls, text: str) -> list[str]:
        """从 ``SOURCES: 画像驱动, 趋势驱动`` 行解析 tag 列表。"""
        match = cls._SOURCES_RE.search(text)
        if not match:
            return []
        raw_line = match.group(1)
        # 支持 "[a, b]" 或 "a, b"
        raw_line = raw_line.strip().strip("[]")
        candidates = [p.strip() for p in re.split(r"[,，、]", raw_line) if p.strip()]
        return [c for c in candidates if c in VALID_SOURCE_TAGS]

    @classmethod
    def _strip_sources_line(cls, text: str) -> str:
        """从 PRESENT 文本里去掉 SOURCES 行（这一行用于机器解析，不是给用户看的）。"""
        return cls._SOURCES_RE.sub("", text).rstrip()

    # ------------------------------------------------------------------
    # 内部：FINALIZE / 落库
    # ------------------------------------------------------------------

    async def _finalize_and_persist(self, snapshot_id: str) -> int:
        """组装 StrategySnapshot → pydantic 校验 → 写盘。"""
        draft = self._snapshots[snapshot_id]
        snapshot = self._assemble_snapshot(snapshot_id=snapshot_id, draft=draft)
        version = self._snapshot_versions.get(snapshot_id, 0) + 1
        self._snapshot_versions[snapshot_id] = version
        path = self._snapshot_path(snapshot_id, version)
        path.write_text(
            json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _LOGGER.info(
            "strategy.snapshot.persisted",
            snapshot_id=snapshot_id,
            version=version,
            path=str(path),
        )
        return version

    def _snapshot_path(self, snapshot_id: str, version: int) -> Path:
        return self._cfg.runtime_dir / f"strategy_snapshot_{snapshot_id}_v{version}.json"

    def _assemble_snapshot(self, *, snapshot_id: str, draft: dict[str, Any]) -> StrategySnapshot:
        """从 draft dict 构造 StrategySnapshot pydantic 模型。

        失败会抛 ValidationError，由 caller 决定是否回滚（demo 期不回滚——schema 失败即 bug）。
        """
        idea_summary = draft.get("idea_summary", {}) or {}
        heat = draft.get("heat_analysis", {}) or {}
        fit = draft.get("profile_fit", {}) or {}
        differentiation_raw = draft.get("differentiation", []) or []
        execution_raw = draft.get("execution", {}) or {}

        snapshot = StrategySnapshot(
            strategy_id=snapshot_id,
            user_id=draft.get("__user_id", "user_a_001"),
            profile_version=int(draft.get("__profile_version", 1)),
            generated_at=datetime.now(UTC),
            input=StrategyInput(
                mode="idea_driven",
                user_idea=draft.get("__user_idea", ""),
                iterations=self._snapshot_versions.get(snapshot_id, 0),
            ),
            idea=IdeaSummary(
                topic=idea_summary.get("topic", draft.get("__user_idea", "")),
                predicted_pillar=idea_summary.get("predicted_pillar", ""),
                rationale=idea_summary.get("rationale", ""),
            ),
            heat_analysis=HeatAnalysis(
                trend_score=float(heat.get("trend_score", 0.0)),
                trend_direction=heat.get("trend_direction", "stable"),
                supply_demand_ratio=float(heat.get("supply_demand_ratio", 1.0)),
                matched_trends=list(heat.get("matched_trends", [])),
                comment=heat.get("comment", ""),
            ),
            profile_fit=ProfileFit(
                pillar_alignment=[
                    PillarAlignment(
                        pillar=p.get("pillar", ""),
                        alignment=_coerce_alignment(p.get("alignment")),
                        evidence=p.get("evidence", ""),
                    )
                    for p in fit.get("pillar_alignment", [])
                ],
                persona_leverage=[
                    PersonaLeveragePoint(
                        trait=p.get("trait"),
                        life_context=p.get("life_context"),
                        how_to_use=p.get("how_to_use", ""),
                    )
                    for p in fit.get("persona_leverage", [])
                ],
                to_explore_validation=[
                    ToExploreValidation(
                        hypothesis_id=p.get("hypothesis_id", "h000"),
                        what_this_tests=p.get("what_this_tests", ""),
                    )
                    for p in fit.get("to_explore_validation", [])
                ],
                fit_score=float(fit.get("fit_score", 0.0)),
            ),
            differentiation=[
                DifferentiationPoint(
                    point=d.get("point", ""),
                    source=self._coerce_source(d.get("source", FALLBACK_SOURCE_TAG)),
                )
                for d in differentiation_raw
            ],
            execution=Execution(
                hook=HookDesign(
                    design=execution_raw.get("hook", {}).get("design", ""),
                    rationale=execution_raw.get("hook", {}).get("rationale", ""),
                ),
                pacing=execution_raw.get("pacing", ""),
                cta=execution_raw.get("cta", ""),
                tags=list(execution_raw.get("tags", [])),
                key_focus=execution_raw.get("key_focus", "完播率"),
            ),
        )
        return snapshot

    @staticmethod
    def _coerce_source(raw: str) -> SourceTag:
        """把 LLM 输出的 source 字符串规整到 SourceTag Literal。

        非法值降级为 ``FALLBACK_SOURCE_TAG`` 而不是抛错——demo 稳定性优先。
        """
        if raw in VALID_SOURCE_TAGS:
            return raw  # type: ignore[return-value]
        return FALLBACK_SOURCE_TAG  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # 内部：辅助
    # ------------------------------------------------------------------

    def _build_short_term(
        self,
        working: StrategyWorkingMemory,
        *,
        current_idea: str,
        current_state: StrategyState,
    ) -> StrategyShortTermMemory:
        """从 working memory + idea 构建一份 in-context slice。"""
        return StrategyShortTermMemory(
            current_state=current_state,
            current_idea=current_idea,
            profile_slice=self._profile_slice(working.full_profile, current_idea),
            matched_trends=self._match_trends(working.full_trends, current_idea),
            strategy_draft=working.strategy_draft,
            recent_turns=working.recent_turns(4),
        )

    @staticmethod
    def _profile_slice(profile: dict[str, Any], idea_text: str) -> dict[str, Any]:
        """简化版 slice：直接返完整 profile（demo 单 persona，token 充裕）。

        之后可改为按 idea 关键词检索 to_explore / pillars。
        """
        return profile

    @staticmethod
    def _match_trends(trends: list[dict[str, Any]], idea_text: str) -> list[dict[str, Any]]:
        """简单关键词命中（含 topic 或 matched_keywords 任一字符串与 idea 有交集）。"""
        idea_chars = set(idea_text)
        matched: list[dict[str, Any]] = []
        for t in trends:
            text = (t.get("topic", "") or "") + " ".join(t.get("matched_keywords", []) or [])
            if idea_chars & set(text):
                matched.append(t)
        # 命中为空时回退到全部 trends（让 LLM 自己判断），保证 demo 不空
        return matched or trends

    def _select_top_videos_for_idea(self, idea_text: str) -> list[dict[str, Any]]:
        """从 mock 历史视频里选出与 idea 相关的 top 3，用于 STRATEGIZE 的 hook 对标。"""
        idea_chars = set(idea_text)
        scored: list[tuple[float, dict[str, Any]]] = []
        for v in self._mock.historical_videos.videos:
            payload = v.model_dump(mode="json")
            title = payload.get("title", "")
            transcript = payload.get("transcript_summary", "")
            overlap = len(idea_chars & set(title + transcript))
            completion = payload.get("metrics", {}).get("completion_rate", 0)
            scored.append((overlap + completion, payload))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [v for _, v in scored[:3]]

    def _stub_profile(self) -> dict[str, Any]:
        """没有 onboarding profile 输入时的 demo 兜底 profile。

        使用 mock_data 中的账号 + 围绕"考研一日三餐"的 to_explore 假设。
        """
        account = self._mock.account.model_dump(mode="json")
        return {
            "meta": {
                "user_id": account.get("user_id", "user_a_001"),
                "version": 1,
                "created_at": "2026-04-26T00:00:00Z",
                "session_id": "stub_session",
            },
            "confirmed": {
                "audience_baseline": {},
                "content_pillars": [
                    {"name": "食堂探店", "evidence_video_ids": ["vid_001", "vid_007"]},
                    {"name": "考研日常", "evidence_video_ids": ["vid_004", "vid_010", "vid_016"]},
                ],
                "content_style": {},
            },
            "personalized": {
                "persona_traits": [
                    {"trait": "活力 + 真实感", "evidence": []},
                ],
                "life_context": [
                    {"context": "在读大三、正在备考研", "valid_until": None, "evidence": []},
                ],
                "unique_assets": [
                    {"asset": "本人正在考研的真实身份", "evidence": []},
                ],
            },
            "to_explore": {
                "open_questions": [
                    {
                        "question": "是否把考研作为长期主轴",
                        "options": ["是", "否", "考研结束前混合双轴"],
                        "priority": 1,
                        "user_concerns": ["考研结束后内容寿命"],
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h001",
                        "hypothesis": "考研内容能否与既有食堂、校园生活素材自然融合",
                        "status": "pending",
                        "evidence_for": [],
                        "evidence_against": [],
                    }
                ],
                "aspirations": ["把账号专业化为校园 + 考研类小型商单"],
            },
            "audit_log": [],
        }
