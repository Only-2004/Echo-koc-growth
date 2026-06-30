"""调试用 /api/mock/* 端点。

仅在 ENABLE_MOCK_DEBUG=true 时挂载。便于前端开发时直接拿到结构化 mock 数据。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/mock", tags=["mock"])


def _bundle(request: Request):
    """从 app.state 拿 mock bundle，未加载时 503。"""
    bundle = getattr(request.app.state, "mock", None)
    if bundle is None:
        raise HTTPException(503, detail="mock bundle not loaded; check ENABLE_MOCK_DEBUG and startup logs")
    return bundle


@router.get("/account")
async def get_account(request: Request) -> dict[str, object]:
    return _bundle(request).account.model_dump(mode="json")


@router.get("/videos")
async def get_videos(request: Request) -> dict[str, object]:
    return _bundle(request).historical_videos.model_dump(mode="json")


@router.get("/comments")
async def get_comments(request: Request) -> dict[str, object]:
    return _bundle(request).comments.model_dump(mode="json")


@router.get("/audience")
async def get_audience(request: Request) -> dict[str, object]:
    return _bundle(request).audience.model_dump(mode="json")


@router.get("/baseline")
async def get_baseline(request: Request) -> dict[str, object]:
    return _bundle(request).baseline.model_dump(mode="json")


@router.get("/trends")
async def get_trends(request: Request) -> dict[str, object]:
    return _bundle(request).external_trends.model_dump(mode="json")


@router.get("/retro-video")
async def get_retro_video(request: Request) -> dict[str, object]:
    return _bundle(request).new_video_for_retro.model_dump(mode="json")


@router.get("/onboarding-template")
async def get_onboarding_template(request: Request) -> dict[str, object]:
    return _bundle(request).onboarding_template.model_dump(mode="json")
