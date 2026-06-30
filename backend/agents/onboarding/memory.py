"""Onboarding agent 三层 memory（spec §3）。

- **short_term**：当前 session 的 turn buffer（最近 N 轮）
- **working**：draft_profile 累积 + ANALYZE 候选 claims + 状态切换日志
- **long_term**：跨 session 历史画像（M4 仅占位 schema）

为简单起见，三层都驻留在进程内存（单 persona demo）。session 由
:class:`OnboardingService` 持有，进程退出即丢弃，与 PRD §10 单 persona 假设一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .state_machine import OnboardingState


@dataclass(slots=True)
class Turn:
    """一轮对话单元。

    Parameters
    ----------
    role : str
        ``"ai"`` | ``"user"`` | ``"system"``。
    text : str
        文本内容（不含 source tag）。
    sources : list[str]
        AI 消息的 source tag（user / system 留空）。
    state : OnboardingState
        本轮发生时的状态。
    ts : datetime
        UTC 时间戳。
    """

    role: str
    text: str
    sources: list[str] = field(default_factory=list)
    state: OnboardingState = OnboardingState.INIT
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class CandidateClaim:
    """ANALYZE 阶段产出的候选 claim。"""

    claim_id: str
    claim_text: str
    category: str
    proposed_state: str  # confirmed / personalized / to_explore
    evidence: list[dict[str, Any]] = field(default_factory=list)
    touched: bool = False  # 是否在 PRESENT/VALIDATE 中讨论过


@dataclass(slots=True)
class OnboardingMemory:
    """单个 session 的全部 memory（三层合并）。

    Attributes
    ----------
    session_id : str
        session 标识（``onb_{ts}_{user_id}``）。
    user_id : str
        用户 id。
    state : OnboardingState
        当前 FSM 状态。
    short_term : list[Turn]
        对话 turn buffer（无上限，PRESENT/EXPLORE 取最近 4–6 条进 prompt）。
    candidate_claims : list[CandidateClaim]
        ANALYZE 输出。
    draft_profile : dict
        逐步累积的画像草稿（spec §4 schema 的可写副本）。
    state_log : list[tuple[datetime, OnboardingState, OnboardingState]]
        状态切换日志，便于审计与 retro。
    long_term : dict
        跨 session 历史（M4 占位）。
    """

    session_id: str
    user_id: str
    state: OnboardingState = OnboardingState.INIT
    short_term: list[Turn] = field(default_factory=list)
    candidate_claims: list[CandidateClaim] = field(default_factory=list)
    draft_profile: dict[str, Any] = field(default_factory=dict)
    state_log: list[tuple[datetime, OnboardingState, OnboardingState]] = field(default_factory=list)
    long_term: dict[str, Any] = field(default_factory=dict)
    fatigue_level: str = "none"  # none / mild / strong
    user_requested_finish: bool = False
    summarized: bool = False  # SUMMARIZE 已经发过 → 等待 FINALIZE

    def append_turn(
        self,
        *,
        role: str,
        text: str,
        sources: list[str] | None = None,
        state: OnboardingState | None = None,
    ) -> Turn:
        """追加一条对话。"""
        turn = Turn(
            role=role,
            text=text,
            sources=list(sources or []),
            state=state or self.state,
        )
        self.short_term.append(turn)
        return turn

    def transition(self, new_state: OnboardingState) -> None:
        """切换状态并写入 log。"""
        self.state_log.append((datetime.now(timezone.utc), self.state, new_state))
        self.state = new_state

    def recent_turns(self, k: int = 6) -> list[Turn]:
        """返回最近 ``k`` 轮（含本轮），用于 prompt 拼接。"""
        return self.short_term[-k:]

    def has_unexplored_high_priority(self) -> bool:
        """``draft_profile.to_explore.open_questions`` 中是否仍有未触碰高优先级项。"""
        questions = (
            self.draft_profile.get("to_explore", {}).get("open_questions", [])
            if isinstance(self.draft_profile, dict)
            else []
        )
        for q in questions:
            if not isinstance(q, dict):
                continue
            if q.get("priority", 99) <= 2 and not q.get("_touched", False):
                return True
        return False
