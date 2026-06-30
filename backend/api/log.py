"""``/api/log/*`` 路由：前端异常上报落到后端结构化日志。

设计：
- 仅记录到 stdout 的 structlog（docker json-file driver 自动落盘 + 滚动）
- 不入库、不做去重
- payload 结构化但宽松，未来可演进
- 失败安全：解析异常也不抛 500，让前端的 fire-and-forget 不影响 UX
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/log", tags=["log"])

_logger = structlog.get_logger("beacon.client_error")


class ClientErrorPayload(BaseModel):
    """前端异常上报载荷。所有字段都允许缺省。"""

    kind: str = Field(default="error", description="error / unhandledrejection / boundary")
    message: str = Field(default="", max_length=4000)
    stack: str | None = Field(default=None, max_length=8000)
    source: str | None = Field(default=None, max_length=512)
    line: int | None = None
    column: int | None = None
    url: str | None = Field(default=None, max_length=1024)
    user_agent: str | None = Field(default=None, max_length=512)
    extra: dict[str, Any] | None = None


@router.post("/client-error")
async def report_client_error(payload: ClientErrorPayload, request: Request) -> dict[str, bool]:
    """接收前端 panic / unhandledrejection / ErrorBoundary 上报。"""
    try:
        _logger.error(
            "client_error",
            kind=payload.kind,
            message=payload.message,
            stack=payload.stack,
            source=payload.source,
            line=payload.line,
            column=payload.column,
            url=payload.url,
            user_agent=payload.user_agent or request.headers.get("user-agent"),
            client=request.client.host if request.client else None,
            extra=payload.extra,
        )
    except Exception:
        # 上报通道异常不能反过来打挂调用方；本地兜底打 root logger
        structlog.get_logger().exception("client_error.log_failed")
    return {"ok": True}
