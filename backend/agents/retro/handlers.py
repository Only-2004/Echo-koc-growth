"""Retro agent 各阶段 handler。

每个 handler：
1. 从 ``RetroMemory`` 读取所需切片
2. 渲染对应 prompt
3. 调 LLM 客户端
4. 校验输出（JSON / source tag），失败时按策略 retry / fallback
5. 把结果写回 ``RetroMemory``

handler 不直接读写文件，全部 IO 在 service.py。
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator
from typing import Any

import structlog

from backend.prompts.retro import load_prompt

from .._llm import LLMClient
from .memory import DrillTurn, RetroMemory

_log = structlog.get_logger("retro.handlers")

# 五个合法 source tag（PRD §7 + strategy schema 同步）
SOURCE_TAGS: set[str] = {
    "画像驱动",
    "趋势驱动",
    "数据驱动",
    "历史复盘",
    "用户偏好驱动",
}

_SOURCE_PATTERN = re.compile(r"<source:(画像驱动|趋势驱动|数据驱动|历史复盘|用户偏好驱动)>")

# 共享 system 头部
_RETRO_SYSTEM_HEADER = (
    "你是 Echo 的 Retro & Insight Agent。中文回复。"
    "对不确定性诚实；证据可追溯；给选项不下处方；契约式归因。"
)


# ---------------- 工具函数 ----------------

def _render(template: str, **mapping: Any) -> str:
    """简单的 ``{{key}}`` 替换。"""
    out = template
    for k, v in mapping.items():
        if not isinstance(v, str):
            v = json.dumps(v, ensure_ascii=False, default=str, indent=2)
        out = out.replace("{{" + k + "}}", v)
    return out


def _extract_json_block(text: str) -> dict[str, Any]:
    """从 LLM 输出中抽取 JSON 对象。

    支持以下情况：
    - 整段就是 JSON
    - 被 ```json ... ``` 包围
    - 前后有解释文字（用括号深度匹配找正确的起止位置）
    - thinking 模式下 content 含 JSON + 额外说明文字

    过滤策略：只处理 ``{`` 后（忽略空白）紧跟 ``"`` 的位置，
    跳过中文括号 / JS 风格非引号 key 等非标准 JSON。

    Raises
    ------
    json.JSONDecodeError
        无法解析时透传。
    """
    text = text.strip()
    # 去除 fenced code block
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    # 直接尝试整段
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 遍历所有 { 候选位置，只保留后面紧跟（忽略空白）" 的，用括号深度匹配
    for m in re.finditer(r"\{", text):
        start = m.start()
        tail = text[start + 1 :].lstrip()
        if not tail or tail[0] != '"':
            continue
        depth = 0
        in_string = False
        escape_next = False
        end = -1
        for i, ch in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
            elif not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
        if end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("无法在 LLM 输出中找到 JSON 对象", text, 0)


def _has_source_tag(text: str) -> bool:
    """文本是否含 source chip。"""
    return bool(_SOURCE_PATTERN.search(text))


def _ensure_source_tag(text: str, *, fallback: str = "数据驱动") -> str:
    """若文本缺 source tag，则在末尾追加一个兜底 chip。"""
    if _has_source_tag(text):
        return text
    return text.rstrip() + f"\n\n<source:{fallback}>（系统兜底）"


# ---------------- 结构化阶段 handler ----------------

async def run_compare(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "pro-thinking",
    max_retries: int = 1,
) -> dict[str, Any]:
    """COMPARE：构造预测 vs 实际对比表。

    Parameters
    ----------
    llm : LLMClient
        模型客户端（生产 DeepSeek / 测试 Mock）。
    memory : RetroMemory
        会话内存。
    model : str, optional
        模型档位，默认 pro-thinking。
    max_retries : int, optional
        JSON 校验失败时的重试次数。

    Returns
    -------
    dict[str, Any]
        ``{"data_cards": [...], "strategy_review": [...]}``。
    """
    prompt = load_prompt("02_compare.txt")
    rendered = _render(
        prompt,
        strategy_snapshot_json=memory.inputs["strategy_snapshot"],
        video_metrics_json=memory.inputs["video"]["metrics"],
        account_baseline_json=memory.inputs["baseline"],
    )
    return await _structured_call(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 COMPARE。",
        max_retries=max_retries,
        stage="COMPARE",
        memory_field="comparison_grid",
        memory=memory,
        required_keys=("data_cards", "strategy_review"),
    )


async def run_attribute(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "pro-thinking",
    max_retries: int = 1,
) -> dict[str, Any]:
    """ATTRIBUTE：对 verdict ≠ hit 的项做归因。"""
    prompt = load_prompt("03_attribute.txt")
    rendered = _render(
        prompt,
        comparison_grid_json=memory.comparison_grid,
        drop_off_curve=memory.inputs["video"]["drop_off_curve_points"],
        comments_json=memory.inputs["video"]["comments"],
        strategy_snapshot_json=memory.inputs["strategy_snapshot"],
    )
    return await _structured_call(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 ATTRIBUTE。",
        max_retries=max_retries,
        stage="ATTRIBUTE",
        memory_field="attributions",
        memory=memory,
        required_keys=("attributions",),
    )


async def run_extract_signals(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "flash-thinking",
    max_retries: int = 1,
) -> dict[str, Any]:
    """EXTRACT_SIGNALS：从评论中聚类挖信号。"""
    prompt = load_prompt("04_extract_signals.txt")
    rendered = _render(
        prompt,
        comments_json=memory.inputs["video"]["comments"],
        relevant_profile_slice=_profile_slice(memory.inputs["profile"]),
        strategy_snapshot_json=memory.inputs["strategy_snapshot"],
    )
    return await _structured_call(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 EXTRACT_SIGNALS。",
        max_retries=max_retries,
        stage="EXTRACT_SIGNALS",
        memory_field="audience_signals",
        memory=memory,
        required_keys=("audience_signals", "clusters"),
    )


async def run_synthesize(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "pro-thinking",
    max_retries: int = 2,
) -> dict[str, Any]:
    """SYNTHESIZE：组装 InsightsReport（不含 profile_delta）。

    Notes
    -----
    本阶段必须保证 JSON 严格合法 + 必含字段，retry 上限默认 2 次。
    """
    prompt = load_prompt("05_synthesize.txt")
    rendered = _render(
        prompt,
        data_cards_json=(memory.comparison_grid or {}).get("data_cards", []),
        strategy_review_json=(memory.comparison_grid or {}).get("strategy_review", []),
        attributions_json=(memory.attributions or {}).get("attributions", []),
        signals_json=(memory.audience_signals or {}).get("audience_signals", []),
    )
    return await _structured_call(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 SYNTHESIZE。",
        max_retries=max_retries,
        stage="SYNTHESIZE",
        memory_field="insights_report_draft",
        memory=memory,
        required_keys=(
            "data_cards",
            "strategy_review",
            "insights",
            "audience_signals",
            "suggestions",
        ),
    )


async def run_update_profile(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "flash-thinking",
    max_retries: int = 1,
) -> dict[str, Any]:
    """UPDATE_PROFILE：生成 ProfileDelta（dict 形式，由 service 走 schema 校验）。"""
    prompt = load_prompt("08_update_profile.txt")
    rendered = _render(
        prompt,
        insights_report_json=memory.insights_report_draft,
        profile_json=memory.inputs["profile"],
        strategy_snapshot_json=memory.inputs["strategy_snapshot"],
    )
    delta = await _structured_call(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 UPDATE_PROFILE。",
        max_retries=max_retries,
        stage="UPDATE_PROFILE",
        memory_field="profile_delta_dict",
        memory=memory,
        required_keys=("add_evidence", "promote", "new_observations", "audit_entries"),
    )
    return delta


# ---------------- 流式阶段 handler ----------------

async def stream_present(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "flash-thinking",
) -> AsyncIterator[str]:
    """PRESENT：四段式自然语言总览，流式产出（仅 content）。

    内置 source-tag 保护：
    - 流式期间累积 buffer
    - 流结束后若 buffer 不含 chip，retry 1 次（用同样的 prompt 但加强 system 提示）
    - 仍无 chip 时 fallback 追加兜底 chip

    Yields
    ------
    str
        逐段流式文本（含最终 fallback chip）。
    """
    prompt = load_prompt("06_present.txt")
    rendered = _render(prompt, insights_report_json=memory.insights_report_draft)

    full_text, retries = await _stream_with_source_tag_guard(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="请按四段式输出 retro 总览。",
        max_retries=1,
    )
    memory.presentation_text = full_text
    _log.info("retro.present.done", chars=len(full_text), retries=retries)
    # 重新以一段段流式吐回
    chunk = 24
    for i in range(0, len(full_text), chunk):
        yield full_text[i : i + chunk]


async def stream_present_typed(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "flash-thinking",
) -> AsyncIterator[tuple[str, str]]:
    """PRESENT（typed 版）：yields ``("thinking", chunk)`` 或 ``("content", chunk)``。

    thinking chunk 实时 yield，content 在 source-tag 校验通过后一次性 yield。

    Yields
    ------
    tuple[str, str]
        ``("thinking", chunk)``：思考过程片段（实时）。
        ``("content", full_text)``：最终验证过的完整正文（一条）。
    """
    prompt = load_prompt("06_present.txt")
    rendered = _render(prompt, insights_report_json=memory.insights_report_draft)
    system = _RETRO_SYSTEM_HEADER + "\n\n" + rendered

    content_parts: list[str] = []
    async for chunk_type, chunk in llm.stream_typed(
        model=model,  # type: ignore[arg-type]
        system=system,
        messages=[{"role": "user", "content": "请按四段式输出 retro 总览。"}],
        temperature=0.7,
        max_tokens=1024,
    ):
        if chunk_type == "thinking":
            yield "thinking", chunk
        else:
            content_parts.append(chunk)

    raw = "".join(content_parts)

    # source tag 校验
    if not _has_source_tag(raw):
        _log.warning("retro.present_typed.no_source_tag.retry")
        retry_text = ""
        async for chunk in llm.stream(
            model=model,  # type: ignore[arg-type]
            system=system,
            messages=[{"role": "user", "content": "请按四段式输出 retro 总览。"}],
            temperature=0.7,
            max_tokens=1024,
        ):
            retry_text += chunk
        raw = retry_text if _has_source_tag(retry_text) else _ensure_source_tag(raw)

    memory.presentation_text = raw
    _log.info("retro.present_typed.done", chars=len(raw))
    yield "content", raw


async def stream_drill(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    element_id: str,
    element_type: str,
    user_text: str,
    model: str = "flash-thinking",
) -> AsyncIterator[str]:
    """DRILL：沿被点击元素 evidence 链回答用户追问。"""
    prompt = load_prompt("07_drill.txt")
    rendered = _render(
        prompt,
        insights_report_json=memory.insights_report_draft,
        element_id_and_type=f"{element_type}:{element_id}",
        user_text=user_text,
        drill_history=memory.recent_drill_brief(),
    )
    full_text, _ = await _stream_with_source_tag_guard(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg=user_text,
        max_retries=1,
    )
    memory.push_drill(
        DrillTurn(
            element_id=element_id,
            element_type=element_type,
            user_text=user_text,
            answer_text=full_text,
        )
    )
    chunk = 24
    for i in range(0, len(full_text), chunk):
        yield full_text[i : i + chunk]


# ---------------- 内部 utils ----------------

def _profile_slice(profile: dict[str, Any] | Any) -> dict[str, Any]:
    """从 profile 中切出与 retro 相关的字段（避免 prompt 过大）。"""
    p = profile if isinstance(profile, dict) else profile.model_dump(mode="json")
    return {
        "confirmed_pillars": [
            cp["name"] for cp in p.get("confirmed", {}).get("content_pillars", [])
        ],
        "persona_traits": [
            t["trait"] for t in p.get("personalized", {}).get("persona_traits", [])
        ],
        "to_explore_questions": [
            q["question"] for q in p.get("to_explore", {}).get("open_questions", [])
        ],
        "hypotheses": [
            {"id": h["hypothesis_id"], "text": h["hypothesis"], "status": h["status"]}
            for h in p.get("to_explore", {}).get("hypotheses", [])
        ],
    }


async def _structured_call(
    *,
    llm: LLMClient,
    model: Any,
    system: str,
    user_msg: str,
    max_retries: int,
    stage: str,
    memory_field: str,
    memory: RetroMemory,
    required_keys: tuple[str, ...],
) -> dict[str, Any]:
    """统一的结构化阶段调用：JSON 校验 + retry + 写回 memory。"""
    last_err: str | None = None
    for attempt in range(max_retries + 1):
        t0 = time.time()
        text = await llm.complete(
            model=model,
            system=_RETRO_SYSTEM_HEADER + "\n\n" + system,
            messages=[{"role": "user", "content": user_msg}],
            json_mode=True,
            temperature=0.4,
            max_tokens=2048,
        )
        try:
            data = _extract_json_block(text)
            missing = [k for k in required_keys if k not in data]
            if missing:
                raise ValueError(f"必填字段缺失：{missing}")
        except (json.JSONDecodeError, ValueError) as exc:
            last_err = str(exc)
            _log.warning(
                "retro.stage.json_invalid",
                stage=stage,
                attempt=attempt,
                err=last_err,
            )
            continue
        setattr(memory, memory_field, data)
        _log.info(
            "retro.stage.ok",
            stage=stage,
            duration_ms=int((time.time() - t0) * 1000),
            attempts=attempt + 1,
        )
        return data
    raise RuntimeError(f"{stage} 阶段连续 {max_retries + 1} 次 JSON 校验失败：{last_err}")


async def _structured_call_streaming(
    *,
    llm: LLMClient,
    model: Any,
    system: str,
    user_msg: str,
    max_retries: int,
    stage: str,
    memory_field: str,
    memory: RetroMemory,
    required_keys: tuple[str, ...],
) -> AsyncIterator[tuple[str, str]]:
    """_structured_call 的流式版：实时 yield ("thinking", chunk)，最终写 memory。

    thinking 模型（pro-thinking / flash-thinking）的推理过程通过 stream_typed 捕获并实时
    yield 给调用方；content 积累后同 _structured_call 一样做 JSON 校验 + retry。

    Yields
    ------
    tuple[str, str]
        ("thinking", chunk) 思考过程片段（实时）。
    """
    system_full = _RETRO_SYSTEM_HEADER + "\n\n" + system
    last_err: str | None = None
    for attempt in range(max_retries + 1):
        t0 = time.time()
        content_parts: list[str] = []
        async for chunk_type, chunk in llm.stream_typed(
            model=model,
            system=system_full,
            messages=[{"role": "user", "content": user_msg}],
            temperature=0.4,
            max_tokens=2048,
        ):
            if chunk_type == "thinking":
                yield "thinking", chunk
            else:
                content_parts.append(chunk)
        text = "".join(content_parts)
        try:
            data = _extract_json_block(text)
            missing = [k for k in required_keys if k not in data]
            if missing:
                raise ValueError(f"必填字段缺失：{missing}")
        except (json.JSONDecodeError, ValueError) as exc:
            last_err = str(exc)
            _log.warning("retro.stage.json_invalid", stage=stage, attempt=attempt, err=last_err)
            continue
        setattr(memory, memory_field, data)
        _log.info("retro.stage.ok", stage=stage, duration_ms=int((time.time() - t0) * 1000), attempts=attempt + 1)
        return
    raise RuntimeError(f"{stage} 阶段连续 {max_retries + 1} 次 JSON 校验失败：{last_err}")


async def run_compare_streaming(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "pro-thinking",
    max_retries: int = 1,
) -> AsyncIterator[tuple[str, str]]:
    """COMPARE 的流式版：实时 yield thinking 事件。"""
    prompt = load_prompt("02_compare.txt")
    rendered = _render(
        prompt,
        strategy_snapshot_json=memory.inputs["strategy_snapshot"],
        video_metrics_json=memory.inputs["video"]["metrics"],
        account_baseline_json=memory.inputs["baseline"],
    )
    async for ev in _structured_call_streaming(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 COMPARE。",
        max_retries=max_retries,
        stage="COMPARE",
        memory_field="comparison_grid",
        memory=memory,
        required_keys=("data_cards", "strategy_review"),
    ):
        yield ev


async def run_attribute_streaming(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "pro-thinking",
    max_retries: int = 1,
) -> AsyncIterator[tuple[str, str]]:
    """ATTRIBUTE 的流式版：实时 yield thinking 事件。"""
    prompt = load_prompt("03_attribute.txt")
    rendered = _render(
        prompt,
        comparison_grid_json=memory.comparison_grid,
        drop_off_curve=memory.inputs["video"]["drop_off_curve_points"],
        comments_json=memory.inputs["video"]["comments"],
        strategy_snapshot_json=memory.inputs["strategy_snapshot"],
    )
    async for ev in _structured_call_streaming(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 ATTRIBUTE。",
        max_retries=max_retries,
        stage="ATTRIBUTE",
        memory_field="attributions",
        memory=memory,
        required_keys=("attributions",),
    ):
        yield ev


async def run_extract_signals_streaming(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "flash-thinking",
    max_retries: int = 1,
) -> AsyncIterator[tuple[str, str]]:
    """EXTRACT_SIGNALS 的流式版：实时 yield thinking 事件。"""
    prompt = load_prompt("04_extract_signals.txt")
    rendered = _render(
        prompt,
        comments_json=memory.inputs["video"]["comments"],
        relevant_profile_slice=_profile_slice(memory.inputs["profile"]),
        strategy_snapshot_json=memory.inputs["strategy_snapshot"],
    )
    async for ev in _structured_call_streaming(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 EXTRACT_SIGNALS。",
        max_retries=max_retries,
        stage="EXTRACT_SIGNALS",
        memory_field="audience_signals",
        memory=memory,
        required_keys=("audience_signals", "clusters"),
    ):
        yield ev


async def run_synthesize_streaming(
    *,
    llm: LLMClient,
    memory: RetroMemory,
    model: str = "pro-thinking",
    max_retries: int = 2,
) -> AsyncIterator[tuple[str, str]]:
    """SYNTHESIZE 的流式版：实时 yield thinking 事件。"""
    prompt = load_prompt("05_synthesize.txt")
    rendered = _render(
        prompt,
        data_cards_json=(memory.comparison_grid or {}).get("data_cards", []),
        strategy_review_json=(memory.comparison_grid or {}).get("strategy_review", []),
        attributions_json=(memory.attributions or {}).get("attributions", []),
        signals_json=(memory.audience_signals or {}).get("audience_signals", []),
    )
    async for ev in _structured_call_streaming(
        llm=llm,
        model=model,  # type: ignore[arg-type]
        system=rendered,
        user_msg="开始 SYNTHESIZE。",
        max_retries=max_retries,
        stage="SYNTHESIZE",
        memory_field="insights_report_draft",
        memory=memory,
        required_keys=(
            "data_cards",
            "strategy_review",
            "insights",
            "audience_signals",
            "suggestions",
        ),
    ):
        yield ev


async def _stream_with_source_tag_guard(
    *,
    llm: LLMClient,
    model: Any,
    system: str,
    user_msg: str,
    max_retries: int,
) -> tuple[str, int]:
    """流式调用 + source tag 强约束。

    Returns
    -------
    tuple[str, int]
        (最终累积文本, 实际重试次数)。
    """
    text = ""
    retries = 0
    for attempt in range(max_retries + 1):
        text = ""
        async for chunk in llm.stream(
            model=model,
            system=_RETRO_SYSTEM_HEADER + "\n\n" + system,
            messages=[{"role": "user", "content": user_msg}],
            temperature=0.7,
            max_tokens=1024,
        ):
            text += chunk
        if _has_source_tag(text):
            return text, retries
        retries += 1
        _log.warning("retro.present_drill.no_source_tag", attempt=attempt, len=len(text))
    # fallback 兜底
    return _ensure_source_tag(text), retries
