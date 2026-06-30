"""Source tag 末行抽取与校验工具（PRD §6.7 红线契约）。

PRD §6.7 + §12.8 规定：每条 AI 消息至少要有一个 source tag。本模块提供：

- :data:`VALID_SOURCE_TAGS`：合法 tag 集合（与 PRD §6.7 对齐的 3 个）
- :func:`extract_sources`：从 LLM 输出末行剥出 ``[tag1 tag2]`` 形式的 tag
- :func:`validate_and_extract`：业务封装，无 tag 时按 ``fallback`` 注入，并报告是否 fallback

实现源自 ``backend/agents/onboarding/handlers.py`` 中的 ``extract_sources``，
M7 抽出共享，供 orchestrator 使用。**老 agent 维持现状不动**（onboarding /
strategy / retro 各自有自己的 source tag 校验，格式不统一是历史债，
短周期下不重构）。

Examples
--------
>>> extract_sources("正文…\\n[画像驱动]")
('正文…', ['画像驱动'])
>>> extract_sources("正文…\\n[画像驱动 数据驱动]")
('正文…', ['画像驱动', '数据驱动'])
>>> extract_sources("正文…\\n[随便写]")
('正文…\\n[随便写]', [])
"""

from __future__ import annotations

import re

# Source tag 强约束（PRD §6.7 canonical，与 strategy schema SourceTag 对齐）
VALID_SOURCE_TAGS: frozenset[str] = frozenset({"画像驱动", "趋势驱动", "数据驱动", "历史复盘", "用户偏好驱动"})

# 模型实在打不出 tag 时的兜底注入值
SOURCE_TAG_FALLBACK: str = "数据驱动"

# 匹配末行 ``[tag1 tag2]`` 形式（允许逗号 / 顿号 / 中文逗号 / 空白分隔）
_SOURCE_TAG_PATTERN = re.compile(r"\[([^\[\]]+)\]\s*$")
_SPLIT_PATTERN = re.compile(r"[\s,，、]+")


def extract_sources(text: str) -> tuple[str, list[str]]:
    """从文本末尾抽取 ``[tag]`` 标签，返回 ``(clean_text, tags)``。

    Parameters
    ----------
    text : str
        原始 LLM 输出文本，可能末尾有一组或多组 ``[tag]`` 行。

    Returns
    -------
    tuple[str, list[str]]
        - ``clean_text``：剥除合法 tag 行后的纯净文本（trailing whitespace 已 strip）
        - ``tags``：识别到的合法 source tag 列表（按出现顺序，去重）

    Notes
    -----
    若末行不是合法 tag（例如文本里出现的 ``[随便写]``），则返回原文 + 空列表，
    caller 决定是否 retry / fallback。

    LLM 可能输出多个并列 tag 行：

        ``...正文\\n[数据驱动]\\n[画像驱动]``

    此函数会循环消耗末尾每一对 ``[xxx]``，直到末尾不再是合法 tag 集合。
    """
    stripped = text.rstrip()
    seen: list[str] = []

    while True:
        match = _SOURCE_TAG_PATTERN.search(stripped)
        if not match:
            break
        raw = match.group(1)
        candidates = [t.strip() for t in _SPLIT_PATTERN.split(raw) if t.strip()]
        # 整个 [] 内必须**全部**是合法 tag，才算 source tag 行；否则可能是
        # 正文中出现的真实方括号（例如引用），不能误剥。
        if not candidates or not all(c in VALID_SOURCE_TAGS for c in candidates):
            break
        for tag in candidates:
            if tag not in seen:
                seen.append(tag)
        stripped = stripped[: match.start()].rstrip()

    return stripped, seen


def validate_and_extract(
    text: str,
    *,
    fallback: str = SOURCE_TAG_FALLBACK,
) -> tuple[str, list[str], bool]:
    """业务封装：抽 tag，没有就注入 ``fallback``。

    用于 orchestrator chat 阶段的最终保底——LLM 经过 retry 仍打不出 tag 时，
    宁可注入一个保守 tag 让产品红线（每条 AI 消息至少 1 个 tag）不破，
    也不让前端渲染一条无 chip 的 AI 消息。

    Parameters
    ----------
    text : str
        原始 LLM 输出。
    fallback : str, default "数据驱动"
        无合法 tag 时注入的 tag。必须在 :data:`VALID_SOURCE_TAGS` 中。

    Returns
    -------
    tuple[str, list[str], bool]
        - ``clean_text``：剥除合法 tag 行后的纯净文本
        - ``tags``：长度 ≥ 1 的 tag 列表
        - ``used_fallback``：True 表示原文本无合法 tag，注入了 ``fallback``

    Raises
    ------
    ValueError
        ``fallback`` 不在 :data:`VALID_SOURCE_TAGS` 中。
    """
    if fallback not in VALID_SOURCE_TAGS:
        raise ValueError(
            f"fallback {fallback!r} not in VALID_SOURCE_TAGS={set(VALID_SOURCE_TAGS)}"
        )
    clean, tags = extract_sources(text)
    if tags:
        return clean, tags, False
    return clean, [fallback], True
