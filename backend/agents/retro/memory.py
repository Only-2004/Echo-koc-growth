"""Retro agent 三层 memory。

按 ``retro_insight_agent_demo_spec.md §3``：

- Layer 1：会话工作记忆（in-context 切片，每次 LLM 调用前由 handler 现场组装）
- Layer 2：会话持久化记忆（``RetroMemory`` 这个对象本身，单次 retro 会话生命周期）
- Layer 3：跨模块共享（写盘到 ``runtime_data/insights_report_*.json`` 与
  ``runtime_data/profile_v*.json``，此处只暴露读写接口）

memory 不直接承担 LLM 调用，所有 LLM IO 在 handlers.py。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DrillTurn:
    """一轮 DRILL 交互。"""

    element_id: str
    element_type: str
    user_text: str
    answer_text: str


@dataclass
class RetroMemory:
    """单次 retro 会话的所有内存状态。

    所有阶段的中间产物都挂在这里，便于 handlers 互相读取，也便于测试断言。

    Attributes
    ----------
    inputs : dict[str, object]
        LOAD 阶段加载的全部输入，含 keys：
        ``profile``, ``strategy_snapshot``, ``video``, ``baseline``, ``comments_block``。
    comparison_grid : dict[str, object] | None
        COMPARE 阶段输出。
    attributions : dict[str, object] | None
        ATTRIBUTE 阶段输出。
    audience_signals : dict[str, object] | None
        EXTRACT_SIGNALS 阶段输出。
    insights_report_draft : dict[str, object] | None
        SYNTHESIZE 阶段输出（不含 profile_delta）。
    presentation_text : str
        PRESENT 阶段累积的自然语言总览。
    drill_history : deque[DrillTurn]
        DRILL 阶段的回合缓冲（最大 4 条）。
    profile_delta_dict : dict[str, object] | None
        UPDATE_PROFILE 阶段输出（pydantic 构造前的 dict）。
    """

    inputs: dict[str, Any] = field(default_factory=dict)
    comparison_grid: dict[str, Any] | None = None
    attributions: dict[str, Any] | None = None
    audience_signals: dict[str, Any] | None = None
    insights_report_draft: dict[str, Any] | None = None
    presentation_text: str = ""
    drill_history: deque[DrillTurn] = field(default_factory=lambda: deque(maxlen=4))
    profile_delta_dict: dict[str, Any] | None = None

    def push_drill(self, turn: DrillTurn) -> None:
        """记录一轮 DRILL（自动按容量裁剪）。"""
        self.drill_history.append(turn)

    def recent_drill_brief(self) -> list[dict[str, str]]:
        """返回最近 DRILL 历史的紧凑表示（用于注入下一次 prompt）。"""
        return [
            {
                "element_id": t.element_id,
                "user_text": t.user_text,
                "answer_text": t.answer_text[:120],
            }
            for t in self.drill_history
        ]
