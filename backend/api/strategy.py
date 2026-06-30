"""``/api/strategy/*`` 路由。

* ``POST /api/strategy/submit``：触发 idea-driven 主流程，SSE 流式返回事件。
* ``POST /api/strategy/refine``：REFINE 阶段（含分类 + 回复 + 可选 approve 落库）。
* ``GET  /api/strategy/snapshot/{id}``：读取已落库 snapshot JSON。

注：service 实例由 main.py 在 startup 时注入到 app.state.strategy。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from ..agents.strategy.service import StrategyService

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


class SubmitIdeaRequest(BaseModel):
    """``/submit`` 请求体。"""

    idea_text: str = Field(min_length=1, max_length=400)
    profile_id: str | None = None


class RefineRequest(BaseModel):
    """``/refine`` 请求体。"""

    snapshot_id: str
    user_text: str = Field(min_length=1, max_length=600)


def _service(request: Request) -> StrategyService:
    """从 app.state 取出 service 实例。"""
    svc = getattr(request.app.state, "strategy", None)
    if svc is None:
        raise HTTPException(503, "strategy service 未挂载（缺 startup 注入）")
    return svc


@router.post("/submit")
async def submit_idea(
    request: Request,
    body: SubmitIdeaRequest,
) -> EventSourceResponse:
    """SSE 流式：每条事件 ``event=state|delta|done``。

    缓存策略由 ``Settings.use_cached_analysis``（环境变量 ``USE_CACHED_ANALYSIS``）决定，
    默认走 cache；前端不再传 ``mode`` query param。
    """
    service = _service(request)

    async def _gen() -> Any:
        async for ev in service.submit_idea(idea_text=body.idea_text, use_cache=None):
            yield {"event": ev.get("event", "message"), "data": json.dumps(ev, ensure_ascii=False)}

    return EventSourceResponse(_gen())


@router.post("/refine")
async def refine_strategy(request: Request, body: RefineRequest) -> dict[str, Any]:
    """单次 REFINE：分类 + 生成回复 + 视情况落新版本 snapshot。"""
    service = _service(request)
    try:
        result = await service.refine(snapshot_id=body.snapshot_id, user_text=body.user_text)
    except KeyError as exc:
        raise HTTPException(404, f"snapshot 不存在：{exc.args[0]}") from None
    return {
        "snapshot_id": result.snapshot_id,
        "feedback_type": result.feedback_type,
        "final_text": result.final_text,
        "sources": result.sources,
        "persisted_version": result.persisted_version,
    }


@router.get("/snapshot/{snapshot_id}")
async def get_snapshot(request: Request, snapshot_id: str, version: int | None = None) -> dict[str, Any]:
    """读已落库 snapshot。"""
    service = _service(request)
    try:
        return service.get_snapshot_payload(snapshot_id=snapshot_id, version=version)
    except FileNotFoundError as exc:
        raise HTTPException(404, f"snapshot 文件不存在：{exc}") from None
