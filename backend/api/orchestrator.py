"""``/api/orchestrator/*`` 路由（M7 · Step 5）。

唯一端点：``POST /api/orchestrator/chat`` —— SSE 流式，由
:class:`OrchestratorService` 驱动 (route → context → chat)。

事件协议（与 ``backend/api/retro.py:drill`` 对齐风格）：

- ``{"type": "route",  "decision": {...}}``      —— 路由结果（debug 用，前端可忽略）
- ``{"type": "delta",  "delta": "..."}``          —— 流式 token
- ``{"type": "done",   "sources": [...], "suggestions": [...], "used_fallback": bool}``
- ``{"type": "error",  "message": "..."}``        —— 异常兜底

接收前端 ``ChatTurn`` 数组（最多 6 轮），后端不持久化对话历史（demo 单 persona 单机）。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from backend.agents.orchestrator import (
    OrchestratorChatRequest,
    OrchestratorService,
)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])
_log = structlog.get_logger("api.orchestrator")


def _get_service(request: Request) -> OrchestratorService:
    """从 ``app.state`` 取 orchestrator service；未挂载返 503。"""
    svc = getattr(request.app.state, "orchestrator", None)
    if svc is None:
        raise HTTPException(503, detail="orchestrator service 未挂载，检查 startup 日志")
    return svc


@router.post("/chat")
async def chat(req: OrchestratorChatRequest, request: Request) -> EventSourceResponse:
    """orchestrator chat 端点。

    Parameters
    ----------
    req : OrchestratorChatRequest
        ``{scene, user_text, chat_history?, focused_element?}``。

    Returns
    -------
    EventSourceResponse
        SSE 流；事件 schema 见模块 docstring。
    """
    svc = _get_service(request)

    history = [t.model_dump() for t in req.chat_history]

    async def gen() -> AsyncIterator[dict[str, str]]:
        try:
            async for ev in svc.chat_stream(
                scene=req.scene,
                user_text=req.user_text,
                chat_history=history,
                focused_element=req.focused_element,
            ):
                yield {
                    "event": "message",
                    "data": json.dumps(ev, ensure_ascii=False),
                }
        except Exception as exc:  # pragma: no cover
            _log.exception("orchestrator.chat.failed", err=str(exc))
            yield {
                "event": "message",
                "data": json.dumps(
                    {"type": "error", "message": str(exc)}, ensure_ascii=False
                ),
            }

    return EventSourceResponse(gen())
