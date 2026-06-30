"""Strategy Agent 包。

对应 ``content_strategy_agent_demo_spec.md``：八状态状态机、三层 memory、6 段 prompt。
对外门面是 :class:`StrategyService`。
"""

from .service import StrategyService
from .state_machine import StrategyState

__all__ = ["StrategyService", "StrategyState"]
