"""Orchestrator 主服务：组合 router (Step A) + handlers (Step B)（M7 · Step 4）。

唯一对外入口：:meth:`OrchestratorService.chat_stream`，返回 async generator yield
``ChatEvent`` dict（``delta`` / ``done`` / ``error``），由 API 层转 SSE。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from .._llm import LLMClient
from .context_builder import build_context
from .handlers import stream_chat_with_guard
from .router import RouteDecision, route_decide

_log = structlog.get_logger("orchestrator.service")

Scene = Literal["home", "onboard", "profile", "ideate", "retro"]


class ChatTurn(BaseModel):
    """前端送回的一轮对话。"""

    role: Literal["user", "ai", "system"]
    text: str
    # 兼容前端 sources / suggestions / pending 等字段，service 不读
    sources: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class OrchestratorChatRequest(BaseModel):
    """``POST /api/orchestrator/chat`` 请求体。"""

    scene: Scene
    user_text: str = Field(min_length=1, max_length=2000)
    chat_history: list[ChatTurn] = Field(default_factory=list)
    focused_element: dict[str, Any] | None = None  # 预留，当前未消费


# ChatEvent 用普通 dict 表示（FastAPI 直接用 SSE adapter 序列化，不必走 pydantic）
ChatEvent = dict[str, object]


class OrchestratorService:
    """orchestrator agent 主入口。

    Parameters
    ----------
    client : LLMClient
        三档统一客户端。route 阶段固定调 ``flash``，chat 阶段固定调 ``flash-thinking``。
    runtime_dir : Path
        ``runtime_data/`` 目录，context_builder 从中读 profile / strategy / retro。
    """

    def __init__(self, client: LLMClient, runtime_dir: Path) -> None:
        self._client = client
        self._runtime_dir = runtime_dir

    async def chat_stream(
        self,
        *,
        scene: Scene,
        user_text: str,
        chat_history: Sequence[dict[str, str]] | None = None,
        focused_element: dict[str, Any] | None = None,
    ) -> AsyncIterator[ChatEvent]:
        """跑完 route → context → chat → done，按事件 yield。

        失败时不抛异常，而是 yield 一个 ``error`` 事件让 API 层转给前端。

        Yields
        ------
        dict
            ``{"type": "route", "decision": {...}}`` —— 路由结果（前端可不消费，便于调试）
            ``{"type": "delta", "delta": "..."}``  —— 流式 token
            ``{"type": "done", "sources": [...], "suggestions": [...], "used_fallback": bool}``
            ``{"type": "error", "message": "..."}`` —— LLM 异常等
        """
        history = list(chat_history or [])
        _ = focused_element  # 预留字段，当前不消费但保留参数避免误删

        # Step A · route
        try:
            decision: RouteDecision = await route_decide(
                client=self._client,
                scene=scene,
                user_text=user_text,
                chat_history=history,
            )
        except Exception as e:  # noqa: BLE001
            _log.error("orchestrator.service.route_unhandled", err=str(e))
            yield {"type": "error", "message": "route 阶段异常，请稍后重试"}
            return

        yield {
            "type": "route",
            "decision": decision.model_dump(),
        }

        # Step B · 装配上下文（按 needs_slices 子集）
        slices = build_context(scene, decision.needs_slices, self._runtime_dir)

        # Step C · 流式 chat + source guard
        try:
            async for ev in stream_chat_with_guard(
                client=self._client,
                scene=scene,
                tone=decision.tone,
                slices=slices,
                chat_history=history,
                user_text=user_text,
                expect_suggestions=decision.expect_suggestions,
            ):
                yield ev
        except Exception as e:  # noqa: BLE001
            _log.error("orchestrator.service.chat_unhandled", err=str(e))
            yield {"type": "error", "message": "chat 阶段异常，请稍后重试"}
