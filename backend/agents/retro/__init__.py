"""Retro Insight Agent 包入口。

九状态 FSM：LOAD → COMPARE → ATTRIBUTE → EXTRACT_SIGNALS → SYNTHESIZE
            → PRESENT → DRILL → UPDATE_PROFILE → FINALIZE

详见 ``retro_insight_agent_demo_spec.md``。
"""

from .memory import RetroMemory
from .profile_merger import merge_profile_delta
from .service import RetroService
from .state_machine import RetroState, RetroStateMachine

__all__ = [
    "RetroState",
    "RetroStateMachine",
    "RetroMemory",
    "RetroService",
    "merge_profile_delta",
]
