"""Strategy 各状态的 LLM handler。

每个 handler 拿到 ``StrategyShortTermMemory`` + ``LLMClient`` 后：
1. 加载对应 prompt 模板，做变量替换
2. 调 LLMClient（complete / stream）
3. 返回结构化结果（dict / 字符串）

复杂的 retry / fallback / source-tag 校验在 :mod:`service` 层统一处理，
handler 只关注"按 spec 调一次 LLM 并解析"。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from .._llm.client import LLMClient
from .memory import ConversationTurn, StrategyShortTermMemory

SYSTEM_PROMPT = """你是一个为早期视频类 KOC 提供内容策略的 AI 顾问。
你的目标是把用户的一个想法或一个空白，转化为一份带证据的、
可执行的、可被后续复盘验证的内容策略。

你必须遵守以下原则：

1. 双轴决策。每条建议都明示其来源：
   "画像驱动" / "趋势驱动" / "数据驱动" / "历史复盘" / "用户偏好驱动"。
   不要给黑箱建议。

2. 差异化优先于热度。当画像与趋势冲突时，优先保护用户的人格独特性，
   不为流量牺牲账号定位。

3. 可验证。所有预测必须落到具体可观测指标（完播率区间、
   关注转化率、评论关键词），并明示哪个指标是这次的核心 KPI。

4. 承接 to_explore。生成策略时主动检查 profile 中的待探索项，
   尽量让一条内容同时承担"试图涨粉"和"验证假设"两个目标。

5. 简洁、专业、不油腻。中文回复。
"""


_PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts" / "strategy"


def _load_prompt(name: str) -> str:
    """加载提示词模板文件。"""
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")


def _render(template: str, context: dict[str, str]) -> str:
    """超简单 Mustache 替换。"""
    out = template
    for k, v in context.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _build_recent_turns_block(turns: list[ConversationTurn]) -> str:
    """把最近若干轮对话渲染成自然语言上下文。"""
    if not turns:
        return "（无历史对话）"
    lines = []
    for t in turns:
        role = "用户" if t.role == "user" else "AI"
        lines.append(f"[{role}] {t.text}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 各状态 handler
# ---------------------------------------------------------------------------


async def handle_analyze_idea(
    *,
    short: StrategyShortTermMemory,
    client: LLMClient,
) -> str:
    """ANALYZE_IDEA：返回一段简短的语义分析文本。

    使用 flash-thinking（对话式，不需要 JSON）。
    """
    template = _load_prompt("01_analyze_idea.txt")
    user_msg = _render(
        template,
        {
            "idea_text": short.current_idea,
            "profile_slice_json": json.dumps(short.profile_slice, ensure_ascii=False),
            "trends_json": json.dumps(short.matched_trends, ensure_ascii=False),
        },
    )
    return await client.complete(
        model="flash-thinking",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.6,
        max_tokens=400,
    )


async def handle_generate_ideas(
    *,
    short: StrategyShortTermMemory,
    client: LLMClient,
) -> dict[str, Any]:
    """GENERATE_IDEAS（discovery 模式）。返回 ``{"candidate_ideas": [...]}``。"""
    template = _load_prompt("02_generate_ideas.txt")
    user_msg = _render(
        template,
        {
            "profile_json": json.dumps(short.profile_slice, ensure_ascii=False),
            "trends_json": json.dumps(short.matched_trends, ensure_ascii=False),
        },
    )
    raw = await client.complete(
        model="pro-thinking",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        json_mode=True,
        temperature=0.7,
        max_tokens=1500,
    )
    return json.loads(raw)


async def handle_score(
    *,
    short: StrategyShortTermMemory,
    client: LLMClient,
) -> dict[str, Any]:
    """SCORE：输出 heat_analysis + profile_fit + idea_summary。"""
    template = _load_prompt("03_score.txt")
    user_msg = _render(
        template,
        {
            "idea_text": short.current_idea,
            "profile_slice_json": json.dumps(short.profile_slice, ensure_ascii=False),
            "trends_json": json.dumps(short.matched_trends, ensure_ascii=False),
        },
    )
    raw = await client.complete(
        model="pro-thinking",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        json_mode=True,
        temperature=0.4,
        max_tokens=2048,
    )
    return json.loads(raw)


async def stream_score_typed(
    *,
    short: StrategyShortTermMemory,
    client: LLMClient,
) -> AsyncIterator[tuple[str, str]]:
    """SCORE 流式版（live LLM 路径）：同时 yield thinking token 与 content token。

    Yields
    ------
    tuple[str, str]
        ``("thinking", chunk)`` 或 ``("content", chunk)``。
        content 完整拼接后须是合法 JSON（与 handle_score 输出 schema 相同）。
    """
    template = _load_prompt("03_score.txt")
    user_msg = _render(
        template,
        {
            "idea_text": short.current_idea,
            "profile_slice_json": json.dumps(short.profile_slice, ensure_ascii=False),
            "trends_json": json.dumps(short.matched_trends, ensure_ascii=False),
        },
    )
    async for chunk_type, chunk in client.stream_typed(
        model="pro-thinking",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.4,
        max_tokens=2048,
    ):
        yield chunk_type, chunk


async def handle_strategize(
    *,
    short: StrategyShortTermMemory,
    client: LLMClient,
    top_videos: list[dict[str, Any]],
) -> dict[str, Any]:
    """STRATEGIZE：输出 differentiation + execution（hook+pacing+cta+key_focus）。"""
    template = _load_prompt("04_strategize.txt")
    draft = short.strategy_draft
    user_msg = _render(
        template,
        {
            "heat_json": json.dumps(draft.get("heat_analysis", {}), ensure_ascii=False),
            "fit_json": json.dumps(draft.get("profile_fit", {}), ensure_ascii=False),
            "top_videos_json": json.dumps(top_videos, ensure_ascii=False),
        },
    )
    raw = await client.complete(
        model="pro-thinking",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        json_mode=True,
        temperature=0.5,
        max_tokens=2048,
    )
    return json.loads(raw)


async def stream_strategize_typed(
    *,
    short: StrategyShortTermMemory,
    client: LLMClient,
    top_videos: list[dict[str, Any]],
) -> AsyncIterator[tuple[str, str]]:
    """STRATEGIZE 流式版（live LLM 路径）：同时 yield thinking token 与 content token。

    Yields
    ------
    tuple[str, str]
        ``("thinking", chunk)`` 或 ``("content", chunk)``。
        content 完整拼接后须是合法 JSON（与 handle_strategize 输出 schema 相同）。
    """
    template = _load_prompt("04_strategize.txt")
    draft = short.strategy_draft
    user_msg = _render(
        template,
        {
            "heat_json": json.dumps(draft.get("heat_analysis", {}), ensure_ascii=False),
            "fit_json": json.dumps(draft.get("profile_fit", {}), ensure_ascii=False),
            "top_videos_json": json.dumps(top_videos, ensure_ascii=False),
        },
    )
    async for chunk_type, chunk in client.stream_typed(
        model="pro-thinking",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.5,
        max_tokens=2048,
    ):
        yield chunk_type, chunk


def render_present_prompt(strategy_draft: dict[str, Any]) -> str:
    """构造 PRESENT 阶段 user prompt。

    单独抽出便于 service 层 retry 时附加额外约束。
    """
    template = _load_prompt("05_present.txt")
    return _render(
        template,
        {"strategy_draft_json": json.dumps(strategy_draft, ensure_ascii=False)},
    )


async def stream_present(
    *,
    strategy_draft: dict[str, Any],
    client: LLMClient,
    extra_constraint: str = "",
) -> AsyncIterator[str]:
    """PRESENT：流式返回自然语言策略陈述（仅 content，不含 thinking）。

    Parameters
    ----------
    strategy_draft : dict
        SCORE + STRATEGIZE 合并后的 draft。
    client : LLMClient
        LLM 客户端。
    extra_constraint : str, optional
        retry 时附加在 system prompt 末尾的额外约束。
    """
    user_msg = render_present_prompt(strategy_draft)
    system = SYSTEM_PROMPT
    if extra_constraint:
        system = SYSTEM_PROMPT + "\n\n附加要求：" + extra_constraint
    async for chunk in client.stream(
        model="flash-thinking",
        system=system,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.65,
        max_tokens=900,
    ):
        yield chunk


async def stream_present_typed(
    *,
    strategy_draft: dict[str, Any],
    client: LLMClient,
    extra_constraint: str = "",
) -> AsyncIterator[tuple[str, str]]:
    """PRESENT（typed 版）：yields ``("thinking", chunk)`` 或 ``("content", chunk)``。

    使用 ``flash-thinking`` 的 reasoning_content 字段，把思考过程与正文分开，
    让前端可以同时展示思考进度和最终策略文本。

    Parameters
    ----------
    strategy_draft : dict
        SCORE + STRATEGIZE 合并后的 draft。
    client : LLMClient
        LLM 客户端（需支持 stream_typed）。
    extra_constraint : str, optional
        retry 时附加在 system prompt 末尾的额外约束。
    """
    user_msg = render_present_prompt(strategy_draft)
    system = SYSTEM_PROMPT
    if extra_constraint:
        system = SYSTEM_PROMPT + "\n\n附加要求：" + extra_constraint
    async for chunk_type, chunk in client.stream_typed(
        model="flash-thinking",
        system=system,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.65,
        max_tokens=900,
    ):
        yield chunk_type, chunk


async def classify_refine_feedback(
    *,
    user_text: str,
    client: LLMClient,
) -> str:
    """REFINE 子步骤：用 flash 把用户反馈分类。

    Returns
    -------
    str
        ``"challenge"`` / ``"adjust"`` / ``"approve"``。解析失败默认 ``"challenge"``。
    """
    template = _load_prompt("06a_classify_feedback.txt")
    user_msg = _render(template, {"user_text": user_text})
    raw = await client.complete(
        model="flash",
        system="你是一个把用户文本分类成固定标签的助手。",
        messages=[{"role": "user", "content": user_msg}],
        json_mode=True,
        temperature=0.0,
        max_tokens=64,
    )
    try:
        parsed = json.loads(raw)
        feedback_type = parsed.get("feedback_type", "challenge")
    except json.JSONDecodeError:
        feedback_type = "challenge"
    if feedback_type not in {"challenge", "adjust", "approve"}:
        feedback_type = "challenge"
    return feedback_type


async def stream_refine_reply(
    *,
    strategy_draft: dict[str, Any],
    feedback_type: str,
    user_text: str,
    client: LLMClient,
    extra_constraint: str = "",
) -> AsyncIterator[str]:
    """REFINE：流式返回回复文本。"""
    template = _load_prompt("06_refine.txt")
    user_msg = _render(
        template,
        {
            "strategy_draft_json": json.dumps(strategy_draft, ensure_ascii=False),
            "feedback_type": feedback_type,
            "user_text": user_text,
        },
    )
    system = SYSTEM_PROMPT
    if extra_constraint:
        system = SYSTEM_PROMPT + "\n\n附加要求：" + extra_constraint
    async for chunk in client.stream(
        model="flash-thinking",
        system=system,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.6,
        max_tokens=600,
    ):
        yield chunk
