"""共享 source_tag util 单元测试（M7 · Step 1）。

覆盖：
- :func:`extract_sources` 正常路径（单 tag / 多 tag / 多并列 [tag] 行）
- :func:`extract_sources` 不剥非法方括号（用户引用了 ``[随便写]``）
- :func:`extract_sources` 完全没 tag 时返回空列表
- :func:`validate_and_extract` 注入 fallback
- :func:`validate_and_extract` fallback 非法时 raise
"""

from __future__ import annotations

import pytest

from backend.agents._common.source_tag import (
    SOURCE_TAG_FALLBACK,
    VALID_SOURCE_TAGS,
    extract_sources,
    validate_and_extract,
)


def test_extract_single_tag() -> None:
    """末行单 tag 应被剥出。"""
    clean, tags = extract_sources("正文段落\n[画像驱动]")
    assert clean == "正文段落"
    assert tags == ["画像驱动"]


def test_extract_multi_tag_in_one_line() -> None:
    """单行内多 tag（空格 / 顿号 / 中文逗号 / 半角逗号分隔）都识别。"""
    for sep in [" ", "、", "，", ", "]:
        clean, tags = extract_sources(f"正文\n[画像驱动{sep}数据驱动]")
        assert clean == "正文"
        assert tags == ["画像驱动", "数据驱动"]


def test_extract_multiple_tag_lines() -> None:
    """末尾多个 [tag] 行应循环剥出。

    实现是从末尾倒着剥的，所以最后一行先入列表（与 onboarding 老逻辑一致）。
    """
    clean, tags = extract_sources("正文\n[数据驱动]\n[画像驱动]")
    assert clean == "正文"
    # 末尾的 [画像驱动] 先剥出，所以排在前
    assert tags == ["画像驱动", "数据驱动"]


def test_extract_dedupes() -> None:
    """同一 tag 重复出现只保留首次。"""
    clean, tags = extract_sources("正文\n[画像驱动 画像驱动]")
    assert clean == "正文"
    assert tags == ["画像驱动"]


def test_extract_no_tag_returns_empty() -> None:
    """文本无任何方括号时返回空列表 + 原文。"""
    clean, tags = extract_sources("普通正文，没标签")
    assert clean == "普通正文，没标签"
    assert tags == []


def test_extract_invalid_bracket_not_stripped() -> None:
    """末行方括号内不是合法 tag 时不剥（保留正文中的真实括号）。"""
    clean, tags = extract_sources("引用一句\n[这是用户原话]")
    assert clean == "引用一句\n[这是用户原话]"
    assert tags == []


def test_extract_invalid_third_tag_blocks_strip() -> None:
    """[] 内只要有一个非法 tag，整组都不剥（保守策略）。"""
    clean, tags = extract_sources("正文\n[画像驱动 乱写]")
    assert "[画像驱动 乱写]" in clean
    assert tags == []


def test_extract_trailing_whitespace_stripped() -> None:
    """末尾空白 / 多余换行都应清理。"""
    clean, tags = extract_sources("正文段落\n\n[画像驱动]\n   \n")
    assert clean == "正文段落"
    assert tags == ["画像驱动"]


def test_validate_and_extract_passthrough() -> None:
    """有 tag 时不触发 fallback。"""
    clean, tags, used_fallback = validate_and_extract("正文\n[趋势驱动]")
    assert clean == "正文"
    assert tags == ["趋势驱动"]
    assert used_fallback is False


def test_validate_and_extract_fallback_injected() -> None:
    """无 tag 时注入默认 fallback ``数据驱动``。"""
    clean, tags, used_fallback = validate_and_extract("没标签的正文")
    assert clean == "没标签的正文"
    assert tags == [SOURCE_TAG_FALLBACK]
    assert tags == ["数据驱动"]
    assert used_fallback is True


def test_validate_and_extract_custom_fallback() -> None:
    """fallback 可指定为任意合法 tag。"""
    _clean, tags, used = validate_and_extract("无 tag 文本", fallback="趋势驱动")
    assert tags == ["趋势驱动"]
    assert used is True


def test_validate_and_extract_illegal_fallback_raises() -> None:
    """fallback 非法时直接 raise，避免错误注入。"""
    with pytest.raises(ValueError, match="fallback"):
        validate_and_extract("文本", fallback="瞎写的")


def test_canonical_tag_set_is_five() -> None:
    """canonical 集合与 strategy schema SourceTag 对齐（5 个）。"""
    assert VALID_SOURCE_TAGS == frozenset({"画像驱动", "趋势驱动", "数据驱动", "历史复盘", "用户偏好驱动"})
    assert SOURCE_TAG_FALLBACK in VALID_SOURCE_TAGS
