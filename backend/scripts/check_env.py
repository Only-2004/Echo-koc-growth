"""检查 .env 中所有必填变量的可达性。

按 CLAUDE.md 红线：脚本输出**不回显原文**，只报状态。
直接运行：
    python backend/scripts/check_env.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 允许以 `python backend/scripts/check_env.py` 方式直接运行
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.config import _load_dotenv_from_project_root  # noqa: E402
import os  # noqa: E402

REQUIRED = [
    ("DEEPSEEK_API_KEY", "主力 LLM key（必填）"),
    ("DEEPSEEK_API_BASE", "DeepSeek API endpoint（必填）"),
    ("MODEL_FLASH", "flash 模型 ID（必填，驱动 flash + flash-thinking 两档）"),
    ("MODEL_PRO", "pro 模型 ID（必填，驱动 pro-thinking 档）"),
]

OPTIONAL = [
    ("USE_CACHED_ANALYSIS", "缓存模式开关（demo 默认 true）"),
    ("LOG_LEVEL", "日志级别"),
    ("PORT", "后端端口"),
    ("CORS_ORIGIN", "前端允许源"),
    ("TENCENT_SECRET_ID", "腾讯云（生产）"),
    ("TENCENT_SECRET_KEY", "腾讯云（生产）"),
    ("TENCENT_REGION", "腾讯云区域"),
    ("TENCENT_COS_BUCKET", "COS bucket"),
    ("PUBLIC_BASE_URL", "公网 URL"),
]


def _mask(name: str) -> str:
    """返回该变量的可达性状态字符串（不回显原文）。"""
    raw = os.environ.get(name)
    if raw is None:
        return "未设置"
    raw = raw.strip()
    if not raw:
        return "为空"
    if raw.startswith("your_") or raw.startswith("YOUR_"):
        return "占位符（未替换）"
    # 仅返回长度信息，不暴露字符
    return f"已设置（长度 {len(raw)}）"


def main() -> int:
    """打印检查报告，返回非零 exit code 表示有必填项缺失。"""
    _load_dotenv_from_project_root()

    print("=" * 60)
    print("Echo 配置自检（不回显原文）")
    print("=" * 60)

    missing = 0
    print("\n[必填]")
    for name, desc in REQUIRED:
        status = _mask(name)
        ok = status.startswith("已设置")
        if not ok:
            missing += 1
        flag = "✅" if ok else "❌"
        print(f"  {flag} {name:<26} {status:<22} {desc}")

    print("\n[可选]")
    for name, desc in OPTIONAL:
        status = _mask(name)
        flag = "✅" if status.startswith("已设置") else "·"
        print(f"  {flag} {name:<26} {status:<22} {desc}")

    print("\n" + "=" * 60)
    if missing:
        print(f"⚠️  {missing} 个必填项未填，请编辑 .env（参考 .env.example）")
        return 1
    print("✅ 所有必填项已设置")
    return 0


if __name__ == "__main__":
    sys.exit(main())
