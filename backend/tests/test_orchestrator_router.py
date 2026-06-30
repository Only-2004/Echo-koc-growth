"""Orchestrator 路由阶段测试（M7 · Step 4a）。

全部用 :class:`MockLLMClient`，不发起真实 LLM 调用。覆盖：

- 4 种 intent (data_request / clarification / chitchat / action) 各一次成功路由
- needs_slices 子集解析正确
- LLM 第一次返回非 JSON 时 retry，第二次合法 → 命中 retry 分支
- LLM 两次都返回非法 JSON → fallback 到保守 RouteDecision
- pydantic schema 校验失败 → retry → fallback
"""

from __future__ import annotations

import asyncio
import json

import pytest

from backend.agents._common.source_tag import VALID_SOURCE_TAGS  # 仅用于其他模块 import 自检
from backend.agents._llm import MockLLMClient, MockResponseSpec
from backend.agents.orchestrator import RouteDecision, route_decide
from backend.agents.orchestrator.router import FALLBACK_DECISION

_ = VALID_SOURCE_TAGS  # silence unused


def _enq(client: MockLLMClient, text: str) -> None:
    """把单条响应塞进 default 队列（router 不发 marker）。"""
    client.default_responses.append(MockResponseSpec(text=text))


# ---------------- happy paths ----------------


async def _decide(client: MockLLMClient, scene: str, user_text: str) -> RouteDecision:
    return await route_decide(
        client=client,
        scene=scene,  # type: ignore[arg-type]
        user_text=user_text,
        chat_history=[],
    )


def test_route_data_request() -> None:
    """home + 「下一步该做什么」→ data_request + ≥1 切片。"""
    client = MockLLMClient()
    _enq(
        client,
        json.dumps(
            {
                "intent": "data_request",
                "needs_slices": ["profile", "retro"],
                "tone": "concise",
                "expect_suggestions": True,
            }
        ),
    )
    decision = asyncio.run(_decide(client, "home", "我下一步该做什么"))
    assert decision.intent == "data_request"
    assert "profile" in decision.needs_slices
    assert "retro" in decision.needs_slices
    assert decision.tone == "concise"
    assert decision.expect_suggestions is True


def test_route_clarification() -> None:
    """ideate + 追问 → clarification + explainer tone。"""
    client = MockLLMClient()
    _enq(
        client,
        json.dumps(
            {
                "intent": "clarification",
                "needs_slices": ["retro"],
                "tone": "explainer",
                "expect_suggestions": True,
            }
        ),
    )
    decision = asyncio.run(
        _decide(client, "ideate", "你刚说的留存率 35% 是哪条视频")
    )
    assert decision.intent == "clarification"
    assert decision.tone == "explainer"


def test_route_chitchat_no_slices() -> None:
    """home + 「你好」→ chitchat，needs_slices 应为空、suggestions=False。"""
    client = MockLLMClient()
    _enq(
        client,
        json.dumps(
            {
                "intent": "chitchat",
                "needs_slices": [],
                "tone": "concise",
                "expect_suggestions": False,
            }
        ),
    )
    decision = asyncio.run(_decide(client, "home", "你好"))
    assert decision.intent == "chitchat"
    assert decision.needs_slices == []
    assert decision.expect_suggestions is False


def test_route_action() -> None:
    """profile + 「把 X 加到画像」→ action。"""
    client = MockLLMClient()
    _enq(
        client,
        json.dumps(
            {
                "intent": "action",
                "needs_slices": ["profile"],
                "tone": "concise",
                "expect_suggestions": False,
            }
        ),
    )
    decision = asyncio.run(_decide(client, "profile", "把早八食堂加到画像里"))
    assert decision.intent == "action"
    assert decision.needs_slices == ["profile"]


# ---------------- retry / fallback ----------------


def test_route_retry_after_bad_json() -> None:
    """第一次返回纯文本，第二次返合法 JSON → 命中 retry，最终成功。"""
    client = MockLLMClient()
    _enq(client, "this is not json at all")
    _enq(
        client,
        json.dumps(
            {
                "intent": "data_request",
                "needs_slices": ["profile"],
                "tone": "concise",
                "expect_suggestions": True,
            }
        ),
    )
    decision = asyncio.run(_decide(client, "home", "??"))
    assert decision.intent == "data_request"
    # 两次调用都消费了
    assert len(client.call_log) == 2


def test_route_fallback_when_both_attempts_fail() -> None:
    """两次都非 JSON → 保守 fallback。"""
    client = MockLLMClient()
    _enq(client, "garbage")
    _enq(client, "still garbage")
    decision = asyncio.run(_decide(client, "home", "??"))
    assert decision == FALLBACK_DECISION
    assert decision.needs_slices == ["profile", "strategy", "retro"]


def test_route_fallback_when_schema_invalid() -> None:
    """合法 JSON 但 intent 字段非法 → 走 retry，再失败则 fallback。"""
    client = MockLLMClient()
    _enq(
        client,
        json.dumps(
            {
                "intent": "瞎写的",  # 不在 Literal
                "needs_slices": [],
                "tone": "concise",
                "expect_suggestions": True,
            }
        ),
    )
    _enq(client, "still bad")
    decision = asyncio.run(_decide(client, "home", "??"))
    assert decision == FALLBACK_DECISION


def test_route_handles_markdown_fenced_json() -> None:
    """LLM 把 JSON 包在 ```json fence 里也能解析。"""
    client = MockLLMClient()
    payload = json.dumps(
        {
            "intent": "chitchat",
            "needs_slices": [],
            "tone": "concise",
            "expect_suggestions": False,
        }
    )
    _enq(client, f"```json\n{payload}\n```")
    decision = asyncio.run(_decide(client, "home", "你好"))
    assert decision.intent == "chitchat"


def test_route_handles_extra_text_around_json() -> None:
    """LLM 在 JSON 前后多写了几句话，正则还能抠出 JSON。"""
    client = MockLLMClient()
    payload = json.dumps(
        {
            "intent": "data_request",
            "needs_slices": ["profile"],
            "tone": "concise",
            "expect_suggestions": True,
        }
    )
    _enq(client, f"好的，我的判断是：\n{payload}\n（以上）")
    decision = asyncio.run(_decide(client, "home", "??"))
    assert decision.intent == "data_request"
