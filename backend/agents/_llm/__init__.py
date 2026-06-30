"""LLM client 抽象层（M4 / M5 / M6 共享）。

提供统一的 ``LLMClient`` ABC 与两份实现：

- ``DeepSeekClient``：通过 openai SDK 调用 DeepSeek v4 openai-compatible endpoint
- ``MockLLMClient``：测试桩，按 (tier, system, user) 命中 fixture
"""

from __future__ import annotations

from .client import (
    DeepSeekClient,
    LLMClient,
    MockLLMClient,
    MockResponseSpec,
    ModelTier,
    fixture_key,
)

__all__ = [
    "LLMClient",
    "DeepSeekClient",
    "MockLLMClient",
    "MockResponseSpec",
    "ModelTier",
    "fixture_key",
]
