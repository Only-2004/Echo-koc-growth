"""Agent 共享工具包（M7 起新增）。

提供跨 agent 复用的轻量工具，避免在 onboarding / strategy / retro / orchestrator
四个 agent 之间各自抄一份。

当前导出：

- :mod:`source_tag`：source tag 末行抽取与校验（PRD §6.7 红线）
"""

from .source_tag import (
    SOURCE_TAG_FALLBACK,
    VALID_SOURCE_TAGS,
    extract_sources,
    validate_and_extract,
)

__all__ = [
    "VALID_SOURCE_TAGS",
    "SOURCE_TAG_FALLBACK",
    "extract_sources",
    "validate_and_extract",
]
