"""Retro agent 九状态 FSM。

LOAD → COMPARE → ATTRIBUTE → EXTRACT_SIGNALS → SYNTHESIZE
     → PRESENT → DRILL（循环） → UPDATE_PROFILE → FINALIZE

转移由 ``transition`` 显式触发；非法转移直接 raise。日志通过 structlog 留痕。
"""

from __future__ import annotations

from enum import Enum

import structlog


class RetroState(str, Enum):
    """Retro agent 状态。"""

    LOAD = "LOAD"
    COMPARE = "COMPARE"
    ATTRIBUTE = "ATTRIBUTE"
    EXTRACT_SIGNALS = "EXTRACT_SIGNALS"
    SYNTHESIZE = "SYNTHESIZE"
    PRESENT = "PRESENT"
    DRILL = "DRILL"
    UPDATE_PROFILE = "UPDATE_PROFILE"
    FINALIZE = "FINALIZE"


# 允许的状态转移（DRILL 可自循环；UPDATE_PROFILE 可从 PRESENT 直接跳过 DRILL）
_ALLOWED: dict[RetroState, set[RetroState]] = {
    RetroState.LOAD: {RetroState.COMPARE},
    RetroState.COMPARE: {RetroState.ATTRIBUTE},
    RetroState.ATTRIBUTE: {RetroState.EXTRACT_SIGNALS},
    RetroState.EXTRACT_SIGNALS: {RetroState.SYNTHESIZE},
    RetroState.SYNTHESIZE: {RetroState.PRESENT},
    RetroState.PRESENT: {RetroState.DRILL, RetroState.UPDATE_PROFILE},
    RetroState.DRILL: {RetroState.DRILL, RetroState.UPDATE_PROFILE},
    RetroState.UPDATE_PROFILE: {RetroState.FINALIZE},
    RetroState.FINALIZE: set(),
}


class RetroStateMachine:
    """轻量 FSM。

    Attributes
    ----------
    state : RetroState
        当前状态。
    history : list[RetroState]
        转移历史，便于测试与日志。
    """

    def __init__(self, *, initial: RetroState = RetroState.LOAD) -> None:
        """构造 FSM；默认起点为 LOAD。"""
        self._log = structlog.get_logger("retro.fsm")
        self.state: RetroState = initial
        self.history: list[RetroState] = [initial]

    def transition(self, target: RetroState) -> None:
        """显式转移；非法时抛 RuntimeError。

        Parameters
        ----------
        target : RetroState
            目标状态。

        Raises
        ------
        RuntimeError
            当前状态不允许转移到 ``target``。
        """
        if target not in _ALLOWED[self.state]:
            raise RuntimeError(f"非法状态转移：{self.state.value} -> {target.value}")
        self._log.info("retro.transition", from_=self.state.value, to=target.value)
        self.state = target
        self.history.append(target)

    def reset(self) -> None:
        """回到 LOAD 起点（用于复用同一 service 跑多视频复盘）。"""
        self.state = RetroState.LOAD
        self.history = [RetroState.LOAD]
