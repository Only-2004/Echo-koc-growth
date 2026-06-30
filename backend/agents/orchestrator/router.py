"""Orchestrator Step A · 路由分类（M7 · Step 4a）。

用 ``flash`` 无 thinking 跑一次 JSON 分类，决定下游 chat 阶段挂什么切片、用什么语气。
极轻量（< 200 tokens prompt + < 100 tokens 输出），平均 300-600ms 延迟，给整体 chat
体验加一点点 perceived latency 换取更精准的上下文。

设计要点：

- prompt 只看 scene + 最近 2 轮 history + 当前 user_text，不挂业务切片
- JSON parse 失败 retry 1 次（附加 "请严格按 schema 输出 JSON" 约束）
- 仍失败走保守 fallback：``RouteDecision(intent="data_request",
  needs_slices=["profile","strategy","retro"], tone="concise",
  expect_suggestions=True)``。多挂切片只是浪费 token，不会出错。
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, Field, ValidationError

from .._llm import LLMClient

_log = structlog.get_logger("orchestrator.router")

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts" / "orchestrator"

Intent = Literal["data_request", "clarification", "chitchat", "action"]
SliceKey = Literal["profile", "strategy", "retro"]
Tone = Literal["concise", "explainer", "encouraging"]
Scene = Literal["home", "onboard", "profile", "ideate", "retro"]


class RouteDecision(BaseModel):
    """Route 阶段输出 schema。"""

    intent: Intent
    needs_slices: list[SliceKey] = Field(default_factory=list)
    tone: Tone = "concise"
    expect_suggestions: bool = True


# 当 LLM 两次都吐不出合法 JSON 时的保守 fallback
FALLBACK_DECISION = RouteDecision(
    intent="data_request",
    needs_slices=["profile", "strategy", "retro"],
    tone="concise",
    expect_suggestions=True,
)


def _load_prompt(name: str) -> str:
    """加载 backend/prompts/orchestrator/{name}.txt。"""
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _build_route_user_message(
    *,
    scene: Scene,
    user_text: str,
    chat_history: Sequence[dict[str, str]],
) -> str:
    """拼 router 阶段的 user message。

    Parameters
    ----------
    scene : Scene
        当前 scene。
    user_text : str
        当前轮 user 发言。
    chat_history : Sequence[dict]
        ``[{"role": "user"|"ai"|"system", "text": "..."}]``。
        router 只看最近 2 轮 user/ai（system 跳过）。
    """
    recent: list[str] = []
    for turn in list(chat_history)[-6:]:  # 末 6 项里挑最近 2 轮 user/ai
        role = turn.get("role")
        text = (turn.get("text") or "").strip()
        if not text or role not in ("user", "ai"):
            continue
        prefix = "用户" if role == "user" else "AI"
        recent.append(f"{prefix}：{text[:120]}")
    recent_lines = "\n".join(recent[-4:]) or "（首轮）"

    examples = _load_prompt("route_examples.txt")
    return (
        f"{examples}\n"
        f"---\n"
        f"scene: {scene}\n"
        f"history (recent):\n{recent_lines}\n"
        f"user: {user_text}\n"
        f"output:"
    )


_JSON_OBJECT_RE = re.compile(r"\{.*?\}", re.DOTALL)


def _extract_json(text: str) -> dict[str, object] | None:
    """从 LLM 输出里抽出第一个 JSON object，失败返 None。"""
    text = text.strip()
    # 去 markdown fence
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)  # 整段就是 JSON 的情况
    except json.JSONDecodeError:
        pass
    # 否则贪婪找第一个 { ... }
    m = _JSON_OBJECT_RE.search(text)
    if m is None:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def route_decide(
    *,
    client: LLMClient,
    scene: Scene,
    user_text: str,
    chat_history: Sequence[dict[str, str]],
) -> RouteDecision:
    """跑一次 LLM route，失败 retry 1 次后 fallback。

    Parameters
    ----------
    client : LLMClient
        flash 档客户端（实际 tier 在内部固定为 ``"flash"``）。
    scene : Scene
        当前 scene。
    user_text : str
        当前轮 user 发言。
    chat_history : Sequence[dict]
        最近若干轮对话，至少含最末两条 user/ai。

    Returns
    -------
    RouteDecision
        永远返回合法对象，不抛异常（LLM 异常被消化为 fallback）。
    """
    system = _load_prompt("route_system.txt")
    base_user = _build_route_user_message(
        scene=scene, user_text=user_text, chat_history=chat_history
    )

    for attempt in (1, 2):
        user_msg = base_user
        if attempt == 2:
            user_msg += "\n\n（上一次输出 JSON 不合法。请严格按 schema 输出，不要写任何额外字符。）"
        try:
            raw = await client.complete(
                model="flash",
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                json_mode=True,
                temperature=0.0,
                max_tokens=200,
            )
        except Exception as e:  # noqa: BLE001 — 任何 LLM 异常都不该让 chat 整条挂掉
            _log.warning(
                "orchestrator.route.llm_error",
                attempt=attempt,
                err=str(e),
            )
            continue
        parsed = _extract_json(raw or "")
        if parsed is None:
            _log.warning(
                "orchestrator.route.json_parse_fail",
                attempt=attempt,
                raw_head=(raw or "")[:120],
            )
            continue
        try:
            decision = RouteDecision.model_validate(parsed)
        except ValidationError as e:
            _log.warning(
                "orchestrator.route.schema_fail",
                attempt=attempt,
                err=str(e)[:200],
            )
            continue
        _log.debug(
            "orchestrator.route.ok",
            attempt=attempt,
            intent=decision.intent,
            slices=decision.needs_slices,
            tone=decision.tone,
        )
        return decision

    _log.warning("orchestrator.route.fallback")
    return FALLBACK_DECISION
