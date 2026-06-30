"""Retro 阶段预跑缓存脚本：COMPARE / ATTRIBUTE / EXTRACT_SIGNALS / SYNTHESIZE。

把四个结构化阶段一次性跑出来，落到 ``cache/retro_synthesis.json``，
demo 路径上的 ``RetroSession.run_analysis_phases()`` 在 ``USE_CACHED_ANALYSIS=true`` 时
直接读取，避免现场 LLM 抖动（PRD §7.3）。

仅在主仓库（持有 ``.env`` + venv）下运行：

    python backend/scripts/prepare_retro_cache.py

Notes
-----
* 脚本不在 worktree shell 跑（worktree 看不到 ``.env``）。
* 输入：``backend/mock_data/new_video_for_retro.json`` + 一份 stub StrategySnapshot
  + 一份 stub Profile（与 ``backend/api/retro.py`` 中的 ``_stub_*`` 共享）。
* 输出 schema：

    {
      "generated_at": "...",
      "video_id": "vid_020",
      "compare_output": {...},
      "attribute_output": {...},
      "extract_signals_output": {...},
      "synthesize_output": {...}
    }

* 失败时不写文件；保留上一次缓存。
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 允许 ``python backend/scripts/prepare_retro_cache.py`` 从项目根直接跑
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.agents._llm import DeepSeekClient  # noqa: E402
from backend.agents.retro import handlers  # noqa: E402
from backend.agents.retro.memory import RetroMemory  # noqa: E402
from backend.api.retro import _stub_profile, _stub_strategy_snapshot  # noqa: E402
from backend.config import load_settings  # noqa: E402
from backend.schemas import AccountBaseline, NewVideoForRetro  # noqa: E402


_BACKEND = _PROJECT_ROOT / "backend"
_MOCK_DIR = _BACKEND / "mock_data"
_CACHE_DIR = _PROJECT_ROOT / "cache"


async def _run() -> Path:
    """跑四个阶段并写文件。

    Returns
    -------
    Path
        缓存输出路径。
    """
    settings = load_settings(require_keys=True)  # 这一脚本必须有真实 key
    llm = DeepSeekClient.from_settings(settings)

    video = NewVideoForRetro.model_validate(
        json.loads((_MOCK_DIR / "new_video_for_retro.json").read_text(encoding="utf-8"))
    )
    baseline = AccountBaseline.model_validate(
        json.loads((_MOCK_DIR / "account_baseline.json").read_text(encoding="utf-8"))
    )
    profile = _stub_profile(user_id="user_a_001")
    strategy = _stub_strategy_snapshot(user_id="user_a_001", video_id=video.video_id)

    memory = RetroMemory()
    memory.inputs = {
        "video_id": video.video_id,
        "profile": profile.model_dump(mode="json"),
        "strategy_snapshot": strategy.model_dump(mode="json"),
        "video": video.model_dump(mode="json"),
        "baseline": baseline.model_dump(mode="json"),
    }

    print("[1/4] COMPARE …")
    compare_out = await handlers.run_compare(llm=llm, memory=memory)
    print("[2/4] ATTRIBUTE …")
    attribute_out = await handlers.run_attribute(llm=llm, memory=memory)
    print("[3/4] EXTRACT_SIGNALS …")
    signals_out = await handlers.run_extract_signals(llm=llm, memory=memory)
    print("[4/4] SYNTHESIZE …")
    synth_out = await handlers.run_synthesize(llm=llm, memory=memory)

    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "video_id": video.video_id,
        "compare_output": compare_out,
        "attribute_output": attribute_out,
        "extract_signals_output": signals_out,
        "synthesize_output": synth_out,
    }

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _CACHE_DIR / "retro_synthesis.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✅ 写入缓存：{out_path}")
    return out_path


def main() -> int:
    """脚本入口。失败返回非零 exit code。"""
    try:
        asyncio.run(_run())
        return 0
    except Exception as exc:  # noqa: BLE001  - 顶层兜底
        print(f"❌ 预跑失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
