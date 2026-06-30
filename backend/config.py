"""Beacon 后端运行时配置。

负责从根目录 `.env` 加载环境变量并校验。
按 CLAUDE.md 编程规范：必填项不允许默认值，缺失立即抛 ConfigError。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """配置缺失或非法时抛出。"""


def _load_dotenv_from_project_root() -> None:
    """从项目根目录加载 .env。

    backend/ 在 worktree 与主仓库都可能；.env 永远只在主仓库根。
    sandbox 可能禁止跨目录读 .env（CLAUDE.md 红线），此时静默跳过。
    """
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / ".env"
        try:
            is_file = candidate.is_file()
        except PermissionError:
            # sandbox 禁止访问该 .env（合规预期），跳过该层继续向上
            continue
        if is_file:
            try:
                load_dotenv(candidate, override=False)
            except PermissionError:
                continue
            return
    # 没找到可读 .env 也不立即抛错，留到具体字段缺失时报错
    return


_load_dotenv_from_project_root()


def _required(name: str) -> str:
    """读取必填环境变量；缺失或为空时抛 ConfigError。

    Parameters
    ----------
    name : str
        环境变量名。

    Returns
    -------
    str
        环境变量值（已去除首尾空白）。

    Raises
    ------
    ConfigError
        当变量未设置或为空字符串。
    """
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise ConfigError(f"必填环境变量缺失：{name}（请在 .env 中填写，参考 .env.example）")
    return value.strip()


def _bool(name: str, *, default: bool) -> bool:
    """读取布尔环境变量。"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """统一的应用配置对象。

    Attributes
    ----------
    deepseek_api_key : str
        DeepSeek v4 API key（必填）。
    deepseek_api_base : str
        DeepSeek API endpoint（必填）。
    model_flash : str
        DeepSeek flash 档 model id（驱动 ModelTier ``flash`` 与 ``flash-thinking``，
        后者由 client 通过 ``extra_body.thinking`` 启用）。
    model_pro : str
        DeepSeek pro 档 model id（驱动 ModelTier ``pro-thinking``）。
    max_tokens_flash : int
        ``flash`` 档（无 reasoning）的 ``max_tokens`` 下限。
    max_tokens_flash_thinking : int
        ``flash-thinking`` 档的 ``max_tokens`` 下限；reasoning tokens 计入此预算。
    max_tokens_pro_thinking : int
        ``pro-thinking`` 档的 ``max_tokens`` 下限；reasoning_effort=high 推理较长，
        预算应留充裕余量给 final answer。
    use_cached_analysis : bool
        是否走预跑缓存。Demo 默认 True。
    log_level : str
        structlog / uvicorn 日志级别。
    port : int
        FastAPI 监听端口。
    cors_origin : str
        前端允许源。
    enable_mock_debug : bool
        是否暴露 /api/mock/* 调试端点。
    """

    deepseek_api_key: str
    deepseek_api_base: str
    model_flash: str
    model_pro: str
    max_tokens_flash: int
    max_tokens_flash_thinking: int
    max_tokens_pro_thinking: int
    use_cached_analysis: bool
    use_fallback_all: bool
    llm_max_retries: int
    llm_retry_min_wait: float
    llm_retry_max_wait: float
    llm_timeout_first_token: float
    llm_timeout_total: float
    admin_token: str
    log_level: str
    port: int
    cors_origin: str
    enable_mock_debug: bool


def load_settings(*, require_keys: bool = True) -> Settings:
    """构造 Settings。

    Parameters
    ----------
    require_keys : bool, optional
        True 时缺失 DEEPSEEK_API_KEY / DEEPSEEK_API_BASE 抛错；False 时仅警告，
        允许 /api/health 等不依赖 LLM 的端点工作。M0 启动时 False，业务路由
        启动前再切到 True。

    Returns
    -------
    Settings
        冻结的配置对象。
    """
    if require_keys:
        api_key = _required("DEEPSEEK_API_KEY")
        api_base = _required("DEEPSEEK_API_BASE")
        model_flash = _required("MODEL_FLASH")
        model_pro = _required("MODEL_PRO")
    else:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        api_base = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1").strip()
        model_flash = os.environ.get("MODEL_FLASH", "deepseek-v4-flash").strip()
        model_pro = os.environ.get("MODEL_PRO", "deepseek-v4-pro").strip()

    return Settings(
        deepseek_api_key=api_key,
        deepseek_api_base=api_base,
        model_flash=model_flash,
        model_pro=model_pro,
        max_tokens_flash=int(os.environ.get("MAX_TOKENS_FLASH", "2048")),
        max_tokens_flash_thinking=int(os.environ.get("MAX_TOKENS_FLASH_THINKING", "8192")),
        max_tokens_pro_thinking=int(os.environ.get("MAX_TOKENS_PRO_THINKING", "16384")),
        use_cached_analysis=_bool("USE_CACHED_ANALYSIS", default=True),
        use_fallback_all=_bool("USE_FALLBACK_ALL", default=False),
        llm_max_retries=int(os.environ.get("LLM_MAX_RETRIES", "2")),
        llm_retry_min_wait=float(os.environ.get("LLM_RETRY_MIN_WAIT", "1")),
        llm_retry_max_wait=float(os.environ.get("LLM_RETRY_MAX_WAIT", "8")),
        llm_timeout_first_token=float(os.environ.get("LLM_TIMEOUT_FIRST_TOKEN", "8")),
        llm_timeout_total=float(os.environ.get("LLM_TIMEOUT_TOTAL", "30")),
        admin_token=os.environ.get("ADMIN_TOKEN", ""),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        port=int(os.environ.get("PORT", "8000")),
        cors_origin=os.environ.get("CORS_ORIGIN", "http://localhost:5173"),
        enable_mock_debug=_bool("ENABLE_MOCK_DEBUG", default=True),
    )
