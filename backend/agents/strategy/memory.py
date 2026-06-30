"""Strategy Agent 三层 memory。

对应 spec §3：

* Layer 1 ShortTerm：当前调用要塞进 prompt 的 in-context slice
* Layer 2 Working：当前 session 的 strategy_draft / refinement_history
* Layer 3 LongTerm：跨模块共享（strategy_snapshots 仓库），由 service 层负责持久化
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .state_machine import StrategyState


@dataclass
class ConversationTurn:
    """一轮对话记录。"""

    role: str
    """``"user"`` / ``"agent"``。"""
    text: str
    """文本内容。"""
    sources: list[str] = field(default_factory=list)
    """source tag（仅 agent 消息有）。"""


@dataclass
class StrategyShortTermMemory:
    """Layer 1：每次 LLM 调用现场拼装的 in-context slice。

    使用方式：handler 临时构造，不长期保存。
    """

    current_state: StrategyState
    current_idea: str
    profile_slice: dict[str, Any] = field(default_factory=dict)
    matched_trends: list[dict[str, Any]] = field(default_factory=list)
    strategy_draft: dict[str, Any] = field(default_factory=dict)
    recent_turns: list[ConversationTurn] = field(default_factory=list)


@dataclass
class StrategyWorkingMemory:
    """Layer 2：单 session 持久化记忆。

    Service 层每次 LLM 调用后更新这里；FINALIZE 时把 strategy_draft 落库。
    """

    session_id: str
    full_profile: dict[str, Any] = field(default_factory=dict)
    full_trends: list[dict[str, Any]] = field(default_factory=list)
    strategy_draft: dict[str, Any] = field(default_factory=dict)
    refinement_history: list[dict[str, Any]] = field(default_factory=list)
    conversation: list[ConversationTurn] = field(default_factory=list)

    def append_turn(self, turn: ConversationTurn) -> None:
        """追加一条对话。"""
        self.conversation.append(turn)

    def recent_turns(self, n: int = 4) -> list[ConversationTurn]:
        """最近 n 轮对话（用于 ShortTerm 拼装）。"""
        return list(self.conversation[-n:])
