"""Onboarding agent 的 FastAPI 路由。

端点：

- ``POST /api/onboarding/start``：触发 ANALYZE，返回 session_id + candidate_claims
- ``POST /api/onboarding/turn``：SSE 流式推进对话
- ``POST /api/onboarding/finalize``：写盘 profile_v1.json

Service 实例从 ``app.state.onboarding`` 取（由 main.py startup hook 注入）。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sse_starlette.sse import EventSourceResponse

from ..agents.onboarding import OnboardingService, SessionNotFoundError

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class TurnRequest(BaseModel):
    """`/turn` 请求体。"""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    user_text: str | None = None


class FinalizeRequest(BaseModel):
    """`/finalize` 请求体。"""

    model_config = ConfigDict(extra="forbid")
    session_id: str


def _service(request: Request) -> OnboardingService:
    """从 ``app.state`` 取已注入的 service；未配置返回 503。"""
    svc = getattr(request.app.state, "onboarding", None)
    if svc is None:
        raise HTTPException(503, detail="onboarding service not initialized")
    return svc


@router.post("/start")
async def start_onboarding(request: Request) -> dict[str, Any]:
    """触发 ANALYZE 并初始化一个新 session。

    缓存策略统一由 ``Settings.use_cached_analysis``（环境变量 ``USE_CACHED_ANALYSIS``）控制，
    默认走 cache；前端不再传 ``mode`` query param。
    """
    svc = _service(request)
    return await svc.start(use_cache=None)


@router.post("/turn")
async def turn(request: Request, body: TurnRequest) -> EventSourceResponse:
    """SSE 流式推进对话。"""
    svc = _service(request)

    async def _gen() -> Any:
        try:
            async for event in svc.turn_stream(
                session_id=body.session_id,
                user_text=body.user_text,
            ):
                yield {"event": event["type"], "data": json.dumps(event, ensure_ascii=False)}
        except SessionNotFoundError:
            yield {"event": "error", "data": json.dumps({"message": "session not found"})}

    return EventSourceResponse(_gen())


@router.post("/finalize")
async def finalize(request: Request, body: FinalizeRequest) -> dict[str, Any]:
    """写 profile_v1.json 并返回 profile。"""
    svc = _service(request)
    try:
        profile = await svc.finalize(body.session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(404, detail="session not found") from exc
    return profile.model_dump(mode="json")


@router.post("/finalize-stream")
async def finalize_stream(request: Request, body: FinalizeRequest) -> EventSourceResponse:
    """SSE 流式版 finalize：边 thinking 边输出。

    Events：
    - ``thinking.delta`` — 推理过程 token
    - ``profile.ready``  — 生成完成，含完整 profile
    - ``error``          — 失败
    """
    svc = _service(request)

    async def _gen() -> Any:
        try:
            async for event in svc.finalize_stream(body.session_id):
                yield {"event": event["type"], "data": json.dumps(event, ensure_ascii=False)}
        except SessionNotFoundError:
            yield {"event": "error", "data": json.dumps({"message": "session not found"})}

    return EventSourceResponse(_gen())
