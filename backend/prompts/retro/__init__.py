"""Retro agent 的 prompt 文件汇总入口。

每段 prompt 对应 ``retro_insight_agent_demo_spec.md §5`` 中的一个 phase。
"""

from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt(filename: str) -> str:
    """读取 prompts/retro 目录下指定文件的文本。

    Parameters
    ----------
    filename : str
        prompt 文件名（如 ``02_compare.txt``）。

    Returns
    -------
    str
        文件内容。

    Raises
    ------
    FileNotFoundError
        指定文件不存在。
    """
    path = _PROMPT_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"prompt 文件缺失：{path}")
    return path.read_text(encoding="utf-8")
