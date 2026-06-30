"""Onboarding agent 对外门面（service）。

调用关系：

    FastAPI router (api/onboarding.py)
        └─ OnboardingService.start() / turn_stream() / finalize()
                └─ handlers.run_*  →  LLMClient

每个 session 由 ``session_id`` 在内存 dict 中索引，单 persona demo 不做并发分片。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from ...config import Settings
from ...mock_loader import MockBundle
from ...schemas import Profile
from .._llm import LLMClient
from . import handlers
from .handlers import (
    apply_validate_actions,
    extract_sources,
    run_analyze,
    run_explore,
    run_finalize,
    run_present,
    run_summarize,
    run_validate,
    seed_memory_from_analyze,
)
from .memory import OnboardingMemory
from .state_machine import OnboardingState, can_transition, next_state_after_validate

_logger = structlog.get_logger(__name__)

_FALLBACK_SOURCE = "数据驱动"


class SessionNotFoundError(LookupError):
    """请求的 session_id 未在 service 内存中注册。"""


class OnboardingService:
    """Onboarding agent 对外门面。

    Parameters
    ----------
    llm : LLMClient
        LLM 客户端实例（生产用 :class:`DeepSeekClient`，测试用 ``MockLLMClient``）。
    bundle : MockBundle
        加载好的 mock 数据包。
    settings : Settings
        运行时配置。
    cache_dir : Path | None
        缓存目录。默认 project_root / "cache"。
    runtime_dir : Path | None
        profile_v{n}.json 落盘目录。默认 project_root / "runtime_data"。
    """

    def __init__(
        self,
        *,
        llm: LLMClient,
        bundle: MockBundle,
        settings: Settings,
        cache_dir: Path | None = None,
        runtime_dir: Path | None = None,
    ) -> None:
        """构造函数。"""
        self._llm = llm
        self._bundle = bundle
        self._settings = settings
        # 默认目录基于 backend/.. 的 project root
        backend_dir = Path(__file__).resolve().parents[2]
        project_root = backend_dir.parent
        self._cache_dir = cache_dir or (project_root / "cache")
        self._runtime_dir = runtime_dir or (project_root / "runtime_data")
        self._sessions: dict[str, OnboardingMemory] = {}

    # ------------------------------------------------------------------ start

    async def start(self, *, use_cache: bool | None = None) -> dict[str, Any]:
        """触发 ANALYZE 并初始化 session。

        Parameters
        ----------
        use_cache : bool, optional
            是否走预跑缓存。``None`` 时回退到 ``settings.use_cached_analysis``；
            前端 toggle ``mode=cache|live`` 通过路由层透传到这里。

        Returns
        -------
        dict[str, Any]
            ``{"session_id": ..., "candidate_claims": [...], "state": "PRESENT"}``。
        """
        effective_cache = (
            self._settings.use_cached_analysis if use_cache is None else use_cache
        )
        session_id = f"onb_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        memory = OnboardingMemory(
            session_id=session_id,
            user_id=self._bundle.account.user_id,
        )
        memory.transition(OnboardingState.ANALYZE)

        analyze_output = await self._load_or_run_analyze(use_cache=effective_cache)
        seed_memory_from_analyze(memory, analyze_output)

        memory.transition(OnboardingState.PRESENT)
        self._sessions[session_id] = memory
        _logger.info(
            "onboarding.start",
            session_id=session_id,
            claims=len(memory.candidate_claims),
            from_cache=effective_cache,
        )
        return {
            "session_id": session_id,
            "state": memory.state.value,
            "candidate_claims": [
                {
                    "claim_id": c.claim_id,
                    "claim_text": c.claim_text,
                    "category": c.category,
                    "proposed_state": c.proposed_state,
                }
                for c in memory.candidate_claims
            ],
        }

    async def _load_or_run_analyze(self, *, use_cache: bool | None = None) -> dict[str, Any]:
        """根据 ``use_cache``（或回退到 settings）决定走缓存还是实时调用。"""
        effective_cache = (
            self._settings.use_cached_analysis if use_cache is None else use_cache
        )
        cache_path = self._cache_dir / "onb_analyze.json"
        if effective_cache and cache_path.is_file():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            _logger.info("analyze.cache_hit", path=str(cache_path))
            return data
        _logger.info("analyze.live_call", reason="cache_miss_or_disabled")
        return await run_analyze(llm=self._llm, bundle=self._bundle)

    # ------------------------------------------------------------------- turn

    async def turn_stream(
        self,
        *,
        session_id: str,
        user_text: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """处理一轮对话，SSE 风格 yield 事件 dict。

        Parameters
        ----------
        session_id : str
            会话 id。
        user_text : str | None
            用户文本。第一轮（state == PRESENT）允许 None，触发开场白。

        Yields
        ------
        dict[str, Any]
            形如 ``{"type": "message.delta", "text": "..."}`` 的事件。
        """
        memory = self._get_memory(session_id)
        prev_state = memory.state

        # 1) 第一轮 PRESENT：直接流出开场白，不经过 VALIDATE
        if memory.state == OnboardingState.PRESENT and not memory.short_term:
            async for ev in self._stream_state(memory, OnboardingState.PRESENT, run_present):
                yield ev
            # 留在 VALIDATE 状态等下一次用户输入
            self._safe_transition(memory, OnboardingState.VALIDATE)
            yield {"type": "state.transition", "from": prev_state.value, "to": memory.state.value}
            return

        # 2) 之后的轮次：必有 user_text
        if not user_text:
            yield {"type": "error", "message": "缺少 user_text"}
            return

        memory.append_turn(role="user", text=user_text, state=memory.state)

        # 用户主动收口
        if any(kw in user_text for kw in ("够了", "可以了", "先这样", "结束", "完成")):
            memory.user_requested_finish = True

        # VALIDATE
        validate_output = await run_validate(llm=self._llm, memory=memory, user_reply=user_text)
        patch = apply_validate_actions(memory, validate_output)
        yield {"type": "profile.tick", "patch": patch}

        # 决策下一步
        next_state = next_state_after_validate(
            has_unexplored_high_priority=memory.has_unexplored_high_priority(),
            fatigue_strong=memory.fatigue_level == "strong",
            user_requested_finish=memory.user_requested_finish,
        )

        if next_state == OnboardingState.EXPLORE:
            self._safe_transition(memory, OnboardingState.EXPLORE)
            yield {"type": "state.transition", "from": prev_state.value, "to": memory.state.value}
            async for ev in self._stream_state(memory, OnboardingState.EXPLORE, run_explore):
                yield ev
            self._safe_transition(memory, OnboardingState.VALIDATE)
            yield {"type": "state.transition", "from": "EXPLORE", "to": memory.state.value}
        else:
            self._safe_transition(memory, OnboardingState.SUMMARIZE)
            yield {"type": "state.transition", "from": prev_state.value, "to": memory.state.value}
            async for ev in self._stream_state(memory, OnboardingState.SUMMARIZE, run_summarize):
                yield ev
            memory.summarized = True
            yield {"type": "finish.ready", "session_id": memory.session_id}

    async def _stream_state(
        self,
        memory: OnboardingMemory,
        state: OnboardingState,
        runner: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """通用流式包装器：从 runner 拿 typed chunk → yield thinking.delta / message.delta →
        末尾抽 source tag → message.complete + source enforcement。
        """
        buffer_chunks: list[str] = []
        async for chunk_type, chunk in runner(llm=self._llm, memory=memory):
            if chunk_type == "thinking":
                yield {"type": "thinking.delta", "text": chunk}
            else:
                buffer_chunks.append(chunk)
                yield {"type": "message.delta", "text": chunk}

        full = "".join(buffer_chunks)
        clean, sources = extract_sources(full)

        if not sources:
            # retry 一次：重新跑同一个 runner
            _logger.warning("source_tag.missing.retry", state=state.value)
            buffer_chunks = []
            async for chunk_type, chunk in runner(llm=self._llm, memory=memory):
                if chunk_type == "content":
                    buffer_chunks.append(chunk)
                # retry 时不 emit delta（保持 SSE 简洁），caller 已收到一份
            retry_full = "".join(buffer_chunks)
            clean, sources = extract_sources(retry_full)
            if sources:
                full = retry_full

        if not sources:
            _logger.warning("source_tag.fallback_injected", state=state.value)
            sources = [_FALLBACK_SOURCE]

        memory.append_turn(role="ai", text=clean, sources=sources, state=state)
        yield {
            "type": "message.complete",
            "text": clean,
            "sources": sources,
            "state": state.value,
        }

    # --------------------------------------------------------------- finalize

    async def finalize(self, session_id: str) -> Profile:
        """触发 FINALIZE 并写盘 profile_v1.json。

        Parameters
        ----------
        session_id : str
            会话 id。

        Returns
        -------
        Profile
            通过 schema 校验的最终画像。
        """
        memory = self._get_memory(session_id)
        if memory.state in {OnboardingState.FINALIZE, OnboardingState.DONE}:
            # 幂等：直接重读已落盘文件
            existing = self._read_profile_v1()
            if existing is not None:
                return existing

        self._safe_transition(memory, OnboardingState.FINALIZE)
        profile = await run_finalize(llm=self._llm, memory=memory)

        # 写盘
        self._runtime_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._runtime_dir / "profile_v1.json"
        out_path.write_text(
            json.dumps(profile.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _logger.info("finalize.written", path=str(out_path))

        self._safe_transition(memory, OnboardingState.DONE)
        return profile

    async def finalize_stream(self, session_id: str) -> AsyncIterator[dict[str, Any]]:
        """SSE 流式版 finalize：边 thinking 边输出，最终 yield profile.ready。

        Parameters
        ----------
        session_id : str
            会话 id。

        Yields
        ------
        dict[str, Any]
            ``{"type": "thinking.delta", "text": "..."}`` 推理过程。
            ``{"type": "profile.ready", "profile": {...}}`` 生成完成。
            ``{"type": "error", "message": "..."}`` 失败。
        """
        memory = self._get_memory(session_id)
        if memory.state in {OnboardingState.FINALIZE, OnboardingState.DONE}:
            existing = self._read_profile_v1()
            if existing is not None:
                yield {"type": "profile.ready", "profile": existing.model_dump(mode="json")}
                return

        self._safe_transition(memory, OnboardingState.FINALIZE)

        from .handlers import run_finalize_stream  # 避免循环 import 放到函数内

        async for chunk_type, chunk in run_finalize_stream(llm=self._llm, memory=memory):
            if chunk_type == "thinking":
                yield {"type": "thinking.delta", "text": chunk}
            elif chunk_type == "profile_json":
                profile = Profile.model_validate_json(chunk)
                # 写盘
                self._runtime_dir.mkdir(parents=True, exist_ok=True)
                out_path = self._runtime_dir / "profile_v1.json"
                out_path.write_text(chunk, encoding="utf-8")
                _logger.info("finalize_stream.written", path=str(out_path))
                self._safe_transition(memory, OnboardingState.DONE)
                yield {"type": "profile.ready", "profile": profile.model_dump(mode="json")}
            else:
                yield {"type": "error", "message": chunk}

    def _read_profile_v1(self) -> Profile | None:
        """读已落盘 profile_v1.json；不存在返回 None。"""
        path = self._runtime_dir / "profile_v1.json"
        if not path.is_file():
            return None
        try:
            return Profile.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # pragma: no cover - 防御性
            return None

    # --------------------------------------------------------------- helpers

    def _get_memory(self, session_id: str) -> OnboardingMemory:
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id)
        return self._sessions[session_id]

    def _safe_transition(self, memory: OnboardingMemory, dst: OnboardingState) -> None:
        """带 assert 的转移；非法转移记录 warning 但不抛错（demo 容忍）。"""
        if not can_transition(memory.state, dst):
            _logger.warning(
                "fsm.illegal_transition",
                src=memory.state.value,
                dst=dst.value,
            )
        memory.transition(dst)

    # --------------------------------------------------------------- testing API

    def get_memory_snapshot(self, session_id: str) -> OnboardingMemory:
        """暴露给测试：取 memory 引用以做断言。"""
        return self._get_memory(session_id)


# 公共导出
__all__ = ["OnboardingService", "SessionNotFoundError"]


# 让静态分析器知道我们用了 asyncio（service 内 _stream_state 内部隐含异步迭代）
_ = asyncio  # noqa: F841
_ = handlers  # 保持 import 引用
