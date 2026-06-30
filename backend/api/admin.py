"""Admin API 端点。

提供运行时切换 fallback 模式等管理功能，受 ADMIN_TOKEN 保护。
T51: 应急切换脚本依赖此端点。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _verify_admin_token(request: Request) -> None:
    """验证 admin token。"""
    from backend.config import load_settings  # noqa: PLC0415

    settings = load_settings(require_keys=False)
    token = settings.admin_token
    if not token:
        raise HTTPException(status_code=403, detail="Admin API 未启用（ADMIN_TOKEN 未设置）")

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        provided = auth[7:]
    else:
        provided = request.query_params.get("token", "")

    if provided != token:
        raise HTTPException(status_code=401, detail="Admin token 无效")


class ModeRequest(BaseModel):
    """切换模式请求。"""

    use_fallback_all: bool
    use_cached_analysis: bool | None = None


class ModeResponse(BaseModel):
    """切换模式响应。"""

    use_fallback_all: bool
    use_cached_analysis: bool


@router.post("/mode", response_model=ModeResponse, dependencies=[Depends(_verify_admin_token)])
async def switch_mode(req: ModeRequest) -> ModeResponse:
    """运行时切换 fallback / cached 模式。

    此端点通过修改全局 Settings 对象的属性实现热切换。
    注意：Settings 是 frozen dataclass，需要通过 object.__setattr__ 绕过。

    Parameters
    ----------
    req : ModeRequest
        目标模式配置。

    Returns
    -------
    ModeResponse
        当前生效的模式配置。
    """
    from backend.config import load_settings  # noqa: PLC0415

    settings = load_settings(require_keys=False)

    # frozen dataclass 需要 object.__setattr__ 绕过
    object.__setattr__(settings, "use_fallback_all", req.use_fallback_all)
    if req.use_cached_analysis is not None:
        object.__setattr__(settings, "use_cached_analysis", req.use_cached_analysis)

    logger.warning(
        "Admin 模式切换: use_fallback_all=%s, use_cached_analysis=%s",
        settings.use_fallback_all,
        settings.use_cached_analysis,
    )

    return ModeResponse(
        use_fallback_all=settings.use_fallback_all,
        use_cached_analysis=settings.use_cached_analysis,
    )


@router.get("/status", dependencies=[Depends(_verify_admin_token)])
async def get_status() -> dict[str, object]:
    """获取当前模式状态。"""
    from backend.config import load_settings  # noqa: PLC0415

    settings = load_settings(require_keys=False)
    return {
        "use_fallback_all": settings.use_fallback_all,
        "use_cached_analysis": settings.use_cached_analysis,
    }
