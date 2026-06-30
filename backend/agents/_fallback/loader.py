"""Fallback 响应加载器。

从 responses.json 加载预定义响应，提供按 agent+state 索引的能力，
支持模拟流式输出（30ms/字符）。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RESPONSES_PATH = Path(__file__).parent / "responses.json"


@dataclass
class FallbackResponse:
    """一条 fallback 响应。"""

    text: str
    sources: list[str]
    suggestions: list[str]


class FallbackLoader:
    """加载并索引 fallback 响应。"""

    def __init__(self) -> None:
        with open(_RESPONSES_PATH, encoding="utf-8") as f:
            self._data: dict[str, dict[str, Any]] = json.load(f)
        logger.info("Fallback responses loaded from %s", _RESPONSES_PATH)

    def get(self, agent: str, state: str) -> FallbackResponse | None:
        """按 agent + state 获取 fallback 响应。

        Parameters
        ----------
        agent : str
            agent 名称（onboarding / strategy / retro / orchestrator）。
        state : str
            状态名称（present / explore / summarize / drill 等）。

        Returns
        -------
        FallbackResponse | None
            找到时返回 FallbackResponse，否则返回 None。
        """
        agent_data = self._data.get(agent)
        if not agent_data:
            return None
        resp = agent_data.get(state)
        if not resp:
            return None
        return FallbackResponse(
            text=resp["text"],
            sources=resp.get("sources", ["数据驱动"]),
            suggestions=resp.get("suggestions", []),
        )

    def get_or_default(self, agent: str, state: str) -> FallbackResponse:
        """按 agent + state 获取 fallback，找不到时返回通用兜底。"""
        resp = self.get(agent, state)
        if resp is not None:
            return resp
        return FallbackResponse(
            text="抱歉，AI 服务暂时不可用，请稍后再试。\n\n[数据驱动]",
            sources=["数据驱动"],
            suggestions=["重试", "回到首页"],
        )

    async def stream(self, agent: str, state: str, *, chunk_delay: float = 0.03) -> AsyncIterator[str]:
        """模拟流式输出 fallback 响应（按字符 yield，每字符间隔 chunk_delay 秒）。

        Parameters
        ----------
        agent : str
            agent 名称。
        state : str
            状态名称。
        chunk_delay : float
            每字符间隔（秒），默认 0.03。
        """
        resp = self.get_or_default(agent, state)
        for char in resp.text:
            yield char
            await asyncio.sleep(chunk_delay)

    async def stream_with_metadata(
        self, agent: str, state: str, *, chunk_delay: float = 0.03
    ) -> AsyncIterator[tuple[str, str]]:
        """流式输出 + 最终 metadata 事件。

        Yields
        ------
        tuple[str, str]
            ``("content", chunk)`` 或 ``("done", json_metadata)``。
        """
        resp = self.get_or_default(agent, state)
        for char in resp.text:
            yield ("content", char)
            await asyncio.sleep(chunk_delay)
        import json as _json

        meta = _json.dumps(
            {
                "type": "done",
                "sources": resp.sources,
                "suggestions": resp.suggestions,
                "used_fallback": True,
            },
            ensure_ascii=False,
        )
        yield ("done", meta)


# 全局单例
_loader: FallbackLoader | None = None


def get_loader() -> FallbackLoader:
    """获取全局 FallbackLoader 单例。"""
    global _loader  # noqa: PLW0603
    if _loader is None:
        _loader = FallbackLoader()
    return _loader
