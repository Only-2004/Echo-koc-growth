"""Onboarding agent 六状态有限状态机。

按 onboarding_agent_demo_spec.md §2 实现：

ANALYZE → PRESENT → VALIDATE ⇄ EXPLORE → SUMMARIZE → FINALIZE → DONE

实际 demo 中：

- ``ANALYZE`` 在 :meth:`OnboardingService.start` 内同步触发（一次）
- 之后每次 ``/turn`` 由 :func:`step` 决定下一个 online state
- ``FINALIZE`` 是 ``/finalize`` 端点的专属态
"""

from __future__ import annotations

from enum import Enum


class OnboardingState(str, Enum):
    """状态枚举。值同时作为 SSE ``state.transition`` 事件载荷。"""

    INIT = "INIT"
    ANALYZE = "ANALYZE"
    PRESENT = "PRESENT"
    VALIDATE = "VALIDATE"
    EXPLORE = "EXPLORE"
    SUMMARIZE = "SUMMARIZE"
    FINALIZE = "FINALIZE"
    DONE = "DONE"


# 合法转移图（assert 用）
_TRANSITIONS: dict[OnboardingState, set[OnboardingState]] = {
    OnboardingState.INIT: {OnboardingState.ANALYZE},
    OnboardingState.ANALYZE: {OnboardingState.PRESENT},
    OnboardingState.PRESENT: {OnboardingState.VALIDATE},
    OnboardingState.VALIDATE: {OnboardingState.EXPLORE, OnboardingState.SUMMARIZE},
    OnboardingState.EXPLORE: {OnboardingState.VALIDATE},
    OnboardingState.SUMMARIZE: {OnboardingState.FINALIZE, OnboardingState.EXPLORE},
    OnboardingState.FINALIZE: {OnboardingState.DONE},
    OnboardingState.DONE: set(),
}


def can_transition(src: OnboardingState, dst: OnboardingState) -> bool:
    """判断是否允许从 ``src`` 转移到 ``dst``。

    Parameters
    ----------
    src : OnboardingState
        源状态。
    dst : OnboardingState
        目标状态。

    Returns
    -------
    bool
        合法返回 True。
    """
    return dst in _TRANSITIONS.get(src, set())


def next_state_after_validate(
    *,
    has_unexplored_high_priority: bool,
    fatigue_strong: bool,
    user_requested_finish: bool,
) -> OnboardingState:
    """VALIDATE 之后的分支决策。

    Parameters
    ----------
    has_unexplored_high_priority : bool
        是否仍有 priority>=1 且未触碰的 to_explore 项。
    fatigue_strong : bool
        用户疲劳是否到 strong（连续短答 / 主动喊停）。
    user_requested_finish : bool
        用户明确要求结束（"够了"、"先这样"等）。

    Returns
    -------
    OnboardingState
        下一个状态：EXPLORE（继续追问）或 SUMMARIZE（收口）。
    """
    if user_requested_finish or fatigue_strong:
        return OnboardingState.SUMMARIZE
    if has_unexplored_high_priority:
        return OnboardingState.EXPLORE
    return OnboardingState.SUMMARIZE
