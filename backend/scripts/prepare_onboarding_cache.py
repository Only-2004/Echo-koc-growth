"""ANALYZE 阶段预跑脚本。

**何时跑**：M4 实施期一次性，或当 mock 数据 / prompt 改动后重新跑。
**在哪跑**：项目根目录（主仓库），需要 ``.env`` 中的 ``DEEPSEEK_API_KEY``。

  cd /Users/zhiyao/Claude/koc-agent-v2
  python backend/scripts/prepare_onboarding_cache.py

输出：``cache/onb_analyze.json``，schema：

::

    {
      "generated_at": "ISO8601",
      "model": "pro-thinking",
      "candidate_claims": [...],
      "draft_profile_seed": {...}
    }

USE_CACHED_ANALYSIS=true 时 OnboardingService.start() 直接读取该文件。

Notes
-----
worktree 没有 ``.env``，**请在主仓库执行**。
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 按 CLAUDE.md scripts 约定：脚本顶部塞 sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.agents._llm import DeepSeekClient  # noqa: E402
from backend.agents.onboarding.handlers import run_analyze  # noqa: E402
from backend.config import load_settings  # noqa: E402
from backend.mock_loader import load_mock_bundle  # noqa: E402


async def _amain() -> None:
    """异步主入口：跑 ANALYZE → 写 cache/onb_analyze.json。"""
    settings = load_settings(require_keys=True)
    bundle = load_mock_bundle()
    llm = DeepSeekClient.from_settings(settings)

    print("[prepare_onboarding_cache] 调用 ANALYZE（pro-thinking）...")
    output = await run_analyze(llm=llm, bundle=bundle)

    cache_dir = _PROJECT_ROOT / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "pro-thinking",
        **output,
    }

    out_path = cache_dir / "onb_analyze.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    claim_count = len(output.get("candidate_claims", []))
    print(f"[prepare_onboarding_cache] 已写入 {out_path}（{claim_count} 个 candidate claims）")


def main() -> None:
    """同步包装。"""
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
