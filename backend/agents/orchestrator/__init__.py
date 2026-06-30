"""Orchestrator agent · chat dock 的轻量路由层 + 通用对话 agent（M7）。

设计要点（PRD §6.7 + §12.8）：

1. **两阶段**：先 :func:`router._route` 用 flash 无 thinking 跑 JSON 分类
   （决定 needs_slices / tone / expect_suggestions），再 :func:`service.chat_stream`
   用 flash-thinking SSE 流式生成。route 阶段不挂业务切片，chat 阶段按 needs_slices
   子集裁切片，避免给 thinking 模型塞无关数据浪费 token。

2. **Source tag 强校验**：chat 阶段 _stream_with_source_guard() 流结束后校验末行 tag，
   无 tag retry 1 次，仍无注入 fallback ``[数据驱动]``，确保产品红线（每条 AI 消息
   至少一个 source tag）不破。校验工具来自 :mod:`backend.agents._common.source_tag`。

3. **覆盖范围**：home / onboard / profile / ideate / retro 五个 scene 的 chat dock
   兜底。前端 useChatSend.ts 中 ideate (含 snapshot) → strategy/refine、
   retro (含 report) → retro/drill 这两条专属路径不变；orchestrator 接管其余全部。

公开接口：

- :class:`service.OrchestratorService` — 主服务类
- :class:`router.RouteDecision` — 路由 schema
"""

from .router import RouteDecision, route_decide
from .service import (
    ChatEvent,
    OrchestratorChatRequest,
    OrchestratorService,
)

__all__ = [
    "ChatEvent",
    "OrchestratorChatRequest",
    "OrchestratorService",
    "RouteDecision",
    "route_decide",
]
