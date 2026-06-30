"""Orchestrator chat 阶段的 LLM 调用 handler（M7 · Step 4）。

职责单一：把 system + scene_prompt + slices + history + user_text 拼成 prompt，
调 LLM 流式 stream，返回 ``(text, sources, suggestions)``。source tag 强约束在这里收敛。

接口：

- :func:`stream_chat_with_guard`：流式调用 + 边收边 yield delta，**最终一次性**
  校验末行 tag（无 tag retry 1 次再 fallback）；同时解析 ``SUGGESTIONS:`` 行。

注：流式前端体验上，正文边收边渲染；source chip 与 suggestion chip 在 done 事件里
返回，前端在收到 done 后再渲染。这意味着第一遍 LLM 没打 tag 时 **不会**让前端多段
重写——直接走 retry / fallback 在后端补全 sources，前端只看到一个 done 事件。
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Literal

import structlog

from .._common.source_tag import (
    SOURCE_TAG_FALLBACK,
    extract_sources,
    validate_and_extract,
)
from .._llm import LLMClient

_log = structlog.get_logger("orchestrator.handlers")

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts" / "orchestrator"

Scene = Literal["home", "onboard", "profile", "ideate", "retro"]
Tone = Literal["concise", "explainer", "encouraging"]

_TONE_HINT: dict[Tone, str] = {
    "concise": "（语气：简洁直接，不超过 80 字）",
    "explainer": "（语气：解释推理链，分点列出依据）",
    "encouraging": "（语气：先共情再分析，不替用户下结论）",
}

_SUGGESTIONS_PATTERN = re.compile(r"^\s*SUGGESTIONS:\s*(.+?)\s*$", re.MULTILINE)


def load_prompt(name: str) -> str:
    """加载 backend/prompts/orchestrator/{name}.txt。"""
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _build_system(*, scene: Scene, tone: Tone, slices: dict[str, str]) -> str:
    """拼 chat 阶段的 system prompt。

    顺序：通用 system → scene-specific → tone hint → slices（按 needs_slices 注入）。
    """
    parts: list[str] = [load_prompt("system.txt"), load_prompt(f"scene_{scene}.txt")]
    parts.append(_TONE_HINT[tone])
    if slices:
        slice_text = "\n\n".join(
            f"---\n[切片 · {key}]\n{val}" for key, val in slices.items()
        )
        parts.append("以下是当前会话可引用的数据切片（不在切片里的事实不要编造）：\n\n" + slice_text)
    return "\n\n".join(parts)


def _build_messages(
    *,
    chat_history: Sequence[dict[str, str]],
    user_text: str,
    expect_suggestions: bool,
) -> list[dict[str, str]]:
    """把 chat_history + 当前 user_text 转成 LLM messages。"""
    messages: list[dict[str, str]] = []
    for turn in list(chat_history)[-6:]:
        role = turn.get("role")
        text = (turn.get("text") or "").strip()
        if not text or role == "system":
            continue
        if role == "user":
            messages.append({"role": "user", "content": text})
        elif role == "ai":
            messages.append({"role": "assistant", "content": text})
    suffix = (
        "\n\n（提示：本轮请在末行给出 source tag；并可在末行之前另起一行写 SUGGESTIONS: 建议1 | 建议2 | 建议3）"
        if expect_suggestions
        else "\n\n（提示：本轮请在末行给出 source tag；不需要 SUGGESTIONS 行）"
    )
    messages.append({"role": "user", "content": user_text + suffix})
    return messages


def _parse_suggestions(text: str) -> tuple[str, list[str]]:
    """抽出 ``SUGGESTIONS: a | b | c`` 行，返回 (剥除后正文, 建议列表)。

    最多保留 3 条；普通建议截到 30 字；[GENERATE_BRIEF] 前缀的不截断（需保留完整选题）。
    整行未匹配返回 (原文, [])。
    """
    m = _SUGGESTIONS_PATTERN.search(text)
    if m is None:
        return text, []
    raw = m.group(1)
    items: list[str] = []
    for s in raw.split("|"):
        s = s.strip()
        if not s:
            continue
        # [GENERATE_BRIEF] 是 action trigger，完整保留选题文本；普通建议截 30 字
        items.append(s if s.startswith("[GENERATE_BRIEF]") else s[:30])
    items = items[:3]
    cleaned = (text[: m.start()] + text[m.end() :]).strip()
    return cleaned, items


async def stream_chat_with_guard(
    *,
    client: LLMClient,
    scene: Scene,
    tone: Tone,
    slices: dict[str, str],
    chat_history: Sequence[dict[str, str]],
    user_text: str,
    expect_suggestions: bool,
    max_retries: int = 1,
) -> AsyncIterator[dict[str, object]]:
    """流式调 chat LLM，最终保证 sources ≥ 1 + 解析 suggestions。

    Yields
    ------
    dict
        - ``{"type": "delta", "delta": "..."}`` —— 流式 token（前端实时拼接）
        - ``{"type": "done", "sources": [...], "suggestions": [...], "used_fallback": bool}``
          —— 流结束 + 已校验

    Notes
    -----
    实现策略：先逐 chunk yield delta；流结束时把累积 text 抽 source tag。
    无 tag 时 retry：retry 的输出**不再**逐字 yield，而是在校验后整体决定 sources，
    前端只看到一个 done 事件。这避免了"前端文字突然重写"的怪异 UX。
    fallback 时同理——sources 注入 ``[数据驱动]``，前端正常渲染 chip。
    """
    system = _build_system(scene=scene, tone=tone, slices=slices)
    messages = _build_messages(
        chat_history=chat_history,
        user_text=user_text,
        expect_suggestions=expect_suggestions,
    )

    accumulated = ""
    async for chunk in client.stream(
        model="flash-thinking",
        system=system,
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    ):
        accumulated += chunk
        yield {"type": "delta", "delta": chunk}

    # 流式结束，做 source tag 校验
    cleaned, suggestions = _parse_suggestions(accumulated)
    no_suggestion_clean, sources = extract_sources(cleaned)

    if sources:
        yield {
            "type": "done",
            "text": no_suggestion_clean,
            "sources": sources,
            "suggestions": suggestions,
            "used_fallback": False,
        }
        return

    _log.warning(
        "orchestrator.chat.no_source_tag.retry",
        scene=scene,
        text_len=len(accumulated),
    )
    # Retry：用 complete 一次（非流式）拿一段带 tag 的兜底输出
    # 不再 yield delta，因为前端已经有第一次的正文；只要在 done 事件里给 sources 就行。
    if max_retries >= 1:
        try:
            retry_user = (
                user_text
                + "\n\n（上一次没在末行给 source tag。请只输出末行：[画像驱动] 或"
                  " [趋势驱动] 或 [数据驱动]，单独一行，不要重复正文。）"
            )
            retry_raw = await client.complete(
                model="flash",
                system=system,
                messages=messages[:-1] + [{"role": "user", "content": retry_user}],
                temperature=0.0,
                max_tokens=64,
            )
            _, retry_sources = extract_sources(retry_raw or "")
            if retry_sources:
                yield {
                    "type": "done",
                    "text": no_suggestion_clean,
                    "sources": retry_sources,
                    "suggestions": suggestions,
                    "used_fallback": False,
                }
                return
        except Exception as e:  # noqa: BLE001
            _log.warning("orchestrator.chat.retry_error", err=str(e))

    # Fallback：注入默认 tag，红线不破
    _log.warning("orchestrator.chat.source_tag.fallback", scene=scene)
    _, fb_sources, _ = validate_and_extract(no_suggestion_clean, fallback=SOURCE_TAG_FALLBACK)
    yield {
        "type": "done",
        "text": no_suggestion_clean,
        "sources": fb_sources,
        "suggestions": suggestions,
        "used_fallback": True,
    }
