"""预跑 Strategy SCORE + STRATEGIZE 阶段，固化到 ``cache/strategy_score_strategize.json``。

何时跑
======

* M5 一次：填充 cache 给 demo 用
* 修改 prompt / 模型档位后：重跑覆盖

**重要**：本脚本调用 DeepSeek 在线 API，需要 ``.env`` 中的 ``DEEPSEEK_API_KEY``。
worktree 内没有 ``.env``（CLAUDE.md sandbox 红线），必须切回主仓库执行：

.. code-block:: bash

    cd /Users/zhiyao/Claude/koc-agent-v2
    python backend/scripts/prepare_strategy_cache.py

输出
====

``cache/strategy_score_strategize.json``::

    {
      "generated_at": "2026-04-28T10:00:00+00:00",
      "idea_key": "考研一日三餐",
      "score_output":     { ...SCORE 阶段输出... },
      "strategize_output":{ ...STRATEGIZE 阶段输出... }
    }
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# 让脚本能从项目根直接跑（CLAUDE.md scripts 约定）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.agents._llm.client import DeepSeekClient  # noqa: E402
from backend.agents.strategy import handlers as H  # noqa: E402
from backend.agents.strategy.memory import StrategyShortTermMemory  # noqa: E402
from backend.agents.strategy.service import StrategyService  # noqa: E402
from backend.agents.strategy.state_machine import StrategyState  # noqa: E402
from backend.config import load_settings  # noqa: E402
from backend.mock_loader import load_mock_bundle  # noqa: E402

DEMO_IDEA: str = "考研期间一日三餐怎么吃才能不困"
"""PRD §13.1 演示故事线默认 idea。"""

OUTPUT_PATH: Path = _PROJECT_ROOT / "cache" / "strategy_score_strategize.json"


def _stub_profile(mock_bundle: object) -> dict[str, object]:
    """构造一份贴近 onboarding 输出的 stub profile_v1。

    复用 StrategyService._stub_profile 的逻辑（避免漂移）。
    """
    settings = load_settings(require_keys=False)
    client = DeepSeekClient.from_settings(settings)
    # 借助 service._stub_profile 而无需启动 service
    from backend.agents.strategy.service import StrategyServiceConfig  # noqa: PLC0415

    svc = StrategyService(
        client=client,
        config=StrategyServiceConfig(
            use_cached_analysis=False,
            cache_path=OUTPUT_PATH,
            runtime_dir=_PROJECT_ROOT / "backend" / "runtime_data",
        ),
        mock_bundle=mock_bundle,
    )
    return svc._stub_profile()


async def main() -> None:
    """主流程。"""
    settings = load_settings(require_keys=True)
    if not settings.deepseek_api_key:
        raise SystemExit("缺 DEEPSEEK_API_KEY；请在主仓库 .env 中填好后再跑")

    mock_bundle = load_mock_bundle()
    profile = _stub_profile(mock_bundle)

    client = DeepSeekClient.from_settings(settings)

    short = StrategyShortTermMemory(
        current_state=StrategyState.SCORE,
        current_idea=DEMO_IDEA,
        profile_slice=profile,
        matched_trends=[t.model_dump(mode="json") for t in mock_bundle.external_trends.trends],
        strategy_draft={},
        recent_turns=[],
    )

    print("[1/2] 调 SCORE（pro-thinking）…")
    score_output = await H.handle_score(short=short, client=client)
    short.strategy_draft = dict(score_output)

    print("[2/2] 调 STRATEGIZE（pro-thinking）…")
    top_videos = sorted(
        [v.model_dump(mode="json") for v in mock_bundle.historical_videos.videos],
        key=lambda v: v.get("metrics", {}).get("completion_rate", 0),
        reverse=True,
    )[:3]
    strategize_output = await H.handle_strategize(
        short=short,
        client=client,
        top_videos=top_videos,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "idea_key": "考研一日三餐",
        "demo_idea": DEMO_IDEA,
        "score_output": score_output,
        "strategize_output": strategize_output,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已写入：{OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
