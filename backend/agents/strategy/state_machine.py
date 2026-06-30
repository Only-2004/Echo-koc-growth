"""Strategy Agent 八状态有限状态机。

参照 ``content_strategy_agent_demo_spec.md`` §2：

::

    RECEIVE_IDEA → ANALYZE_IDEA → GENERATE_IDEAS? → SCORE → STRATEGIZE
                  → PRESENT → REFINE → FINALIZE

GENERATE_IDEAS 仅在 discovery 模式启用；idea-driven（demo 默认）跳过。
REFINE 通过 feedback_type 分支：approve → FINALIZE；challenge/adjust → 留在 PRESENT/REFINE 循环。
"""

from __future__ import annotations

from enum import StrEnum


class StrategyState(StrEnum):
    """八个核心状态。"""

    RECEIVE_IDEA = "RECEIVE_IDEA"
    ANALYZE_IDEA = "ANALYZE_IDEA"
    GENERATE_IDEAS = "GENERATE_IDEAS"
    SCORE = "SCORE"
    STRATEGIZE = "STRATEGIZE"
    PRESENT = "PRESENT"
    REFINE = "REFINE"
    FINALIZE = "FINALIZE"


# 合法转移表（白名单）
_ALLOWED_TRANSITIONS: dict[StrategyState, set[StrategyState]] = {
    StrategyState.RECEIVE_IDEA: {StrategyState.ANALYZE_IDEA, StrategyState.GENERATE_IDEAS},
    StrategyState.GENERATE_IDEAS: {StrategyState.ANALYZE_IDEA},
    StrategyState.ANALYZE_IDEA: {StrategyState.SCORE},
    StrategyState.SCORE: {StrategyState.STRATEGIZE},
    StrategyState.STRATEGIZE: {StrategyState.PRESENT},
    StrategyState.PRESENT: {StrategyState.REFINE, StrategyState.FINALIZE},
    StrategyState.REFINE: {
        StrategyState.PRESENT,
        StrategyState.FINALIZE,
        StrategyState.SCORE,  # reject_full / 大改时回退
        StrategyState.STRATEGIZE,  # 部分调整时只重跑 strategize
    },
    StrategyState.FINALIZE: set(),  # 终态
}


def assert_can_transition(src: StrategyState, dst: StrategyState) -> None:
    """断言 src → dst 是合法的状态转移。

    Parameters
    ----------
    src : StrategyState
        当前状态。
    dst : StrategyState
        目标状态。

    Raises
    ------
    ValueError
        非法转移。
    """
    allowed = _ALLOWED_TRANSITIONS.get(src, set())
    if dst not in allowed:
        raise ValueError(f"非法状态转移：{src.value} → {dst.value}（合法目标：{[s.value for s in allowed]}）")
