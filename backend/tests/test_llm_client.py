"""DeepSeekClient 行为测试。

覆盖：
- thinking 激活时跳过 response_format（不兼容）
- thinking 激活时 max_tokens 抬到至少 8192（reasoning 吃 token 预算）
- content 为空时直接返回空（reasoning_content 是 chain-of-thought，非答案）
- json_mode + 无 thinking 时正常设置 response_format
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents._llm.client import DeepSeekClient


def _make_client(
    *,
    max_tokens_by_tier: dict | None = None,
) -> DeepSeekClient:
    """构造一个不发起真实网络调用的 DeepSeekClient。"""
    with patch("backend.agents._llm.client.DeepSeekClient.__init__.__wrapped__", create=True):
        pass
    client = DeepSeekClient.__new__(DeepSeekClient)
    client._tier_to_config = {
        "flash": ("deepseek-v4-flash", None),
        "flash-thinking": (
            "deepseek-v4-flash",
            {"thinking": {"type": "enabled"}, "reasoning_effort": "medium"},
        ),
        "pro-thinking": (
            "deepseek-v4-pro",
            {"thinking": {"type": "enabled"}, "reasoning_effort": "high"},
        ),
    }
    client._max_tokens_by_tier = max_tokens_by_tier or {
        "flash": 2048,
        "flash-thinking": 8192,
        "pro-thinking": 16384,
    }
    client._max_retries = 2
    client._retry_min_wait = 0.01
    client._retry_max_wait = 0.02
    client._timeout_first_token = 8.0
    client._timeout_total = 30.0
    return client


def _mock_response(content: str, reasoning_content: str | None = None):
    """构造 openai SDK ChatCompletion 风格的 mock 响应。"""
    message = SimpleNamespace(content=content, reasoning_content=reasoning_content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


@pytest.mark.asyncio
async def test_json_mode_not_set_when_thinking_active():
    """thinking 激活时不应设置 response_format（避免 API 冲突）。"""
    client = _make_client()
    captured: list[dict] = []

    async def fake_create(**kwargs):
        captured.append(dict(kwargs))
        return _mock_response('{"ok": true}')

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = fake_create
    client._client = mock_openai

    await client.complete(
        model="pro-thinking",
        system="sys",
        messages=[{"role": "user", "content": "go"}],
        json_mode=True,
    )

    assert "response_format" not in captured[0], (
        "thinking 激活时不应透传 response_format"
    )
    assert "extra_body" in captured[0]


@pytest.mark.asyncio
async def test_json_mode_set_when_no_thinking():
    """非 thinking 档位时 json_mode 应正常设置 response_format。"""
    client = _make_client()
    captured: list[dict] = []

    async def fake_create(**kwargs):
        captured.append(dict(kwargs))
        return _mock_response('{"ok": true}')

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = fake_create
    client._client = mock_openai

    await client.complete(
        model="flash",
        system="sys",
        messages=[{"role": "user", "content": "go"}],
        json_mode=True,
    )

    assert captured[0].get("response_format") == {"type": "json_object"}
    assert "extra_body" not in captured[0]


@pytest.mark.asyncio
async def test_thinking_mode_bumps_max_tokens():
    """thinking 激活时 max_tokens 应被抬到至少 8192。"""
    client = _make_client()
    captured: list[dict] = []

    async def fake_create(**kwargs):
        captured.append(dict(kwargs))
        return _mock_response('{"ok": true}')

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = fake_create
    client._client = mock_openai

    await client.complete(
        model="pro-thinking",
        system="sys",
        messages=[{"role": "user", "content": "go"}],
        max_tokens=2048,
    )

    assert captured[0]["max_tokens"] >= 8192


@pytest.mark.asyncio
async def test_thinking_mode_respects_higher_caller_max_tokens():
    """调用方传入 > 8192 的 max_tokens 时不应被下调。"""
    client = _make_client()
    captured: list[dict] = []

    async def fake_create(**kwargs):
        captured.append(dict(kwargs))
        return _mock_response('{"ok": true}')

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = fake_create
    client._client = mock_openai

    await client.complete(
        model="pro-thinking",
        system="sys",
        messages=[{"role": "user", "content": "go"}],
        max_tokens=16384,
    )

    assert captured[0]["max_tokens"] == 16384


@pytest.mark.asyncio
async def test_empty_content_in_thinking_returns_empty():
    """thinking 激活但 content 为空时应直接返回空（不读 reasoning_content）。"""
    client = _make_client()

    async def fake_create(**kwargs):
        return _mock_response(
            content="",
            reasoning_content="思考独白不应作为答案返回",
        )

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = fake_create
    client._client = mock_openai

    result = await client.complete(
        model="pro-thinking",
        system="sys",
        messages=[{"role": "user", "content": "go"}],
    )

    assert result == ""


@pytest.mark.asyncio
async def test_no_fallback_when_content_present():
    """content 有内容时正常返回。"""
    client = _make_client()

    async def fake_create(**kwargs):
        return _mock_response(
            content='{"answer": 42}',
            reasoning_content="这是思考过程，不应被返回",
        )

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = fake_create
    client._client = mock_openai

    result = await client.complete(
        model="pro-thinking",
        system="sys",
        messages=[{"role": "user", "content": "go"}],
    )

    assert result == '{"answer": 42}'
