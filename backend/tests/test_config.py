"""backend.config 模块的测试。

覆盖：
- require_keys=False 时允许空值，提供合理 default
- require_keys=True 时缺失必填项抛 ConfigError
- _bool 解析
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from backend.config import ConfigError, _bool, load_settings


@pytest.fixture(autouse=True)
def _clear_env() -> Iterator[None]:
    """每个测试前清掉相关环境变量，避免泄漏。"""
    keys = [
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_API_BASE",
        "MODEL_FLASH",
        "MODEL_PRO",
        "MAX_TOKENS_FLASH",
        "MAX_TOKENS_FLASH_THINKING",
        "MAX_TOKENS_PRO_THINKING",
        "USE_CACHED_ANALYSIS",
        "LOG_LEVEL",
        "PORT",
        "CORS_ORIGIN",
        "ENABLE_MOCK_DEBUG",
    ]
    saved = {k: os.environ.pop(k, None) for k in keys}
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def test_load_settings_lenient_returns_defaults() -> None:
    """require_keys=False 时即便没填 key 也能拿到 Settings。"""
    settings = load_settings(require_keys=False)
    assert settings.deepseek_api_key == ""
    assert settings.deepseek_api_base == "https://api.deepseek.com/v1"
    assert settings.use_cached_analysis is True
    assert settings.port == 8000
    assert settings.max_tokens_flash == 2048
    assert settings.max_tokens_flash_thinking == 8192
    assert settings.max_tokens_pro_thinking == 16384


def test_max_tokens_env_override() -> None:
    """MAX_TOKENS_* 环境变量应覆盖默认。"""
    os.environ["MAX_TOKENS_PRO_THINKING"] = "32000"
    settings = load_settings(require_keys=False)
    assert settings.max_tokens_pro_thinking == 32000


def test_load_settings_strict_missing_key_raises() -> None:
    """require_keys=True 且 DEEPSEEK_API_KEY 未设置时抛 ConfigError。"""
    with pytest.raises(ConfigError) as exc:
        load_settings(require_keys=True)
    assert "DEEPSEEK_API_KEY" in str(exc.value)


def test_bool_parser() -> None:
    """_bool 应识别常见真值。"""
    os.environ["FLAG"] = "true"
    assert _bool("FLAG", default=False) is True
    os.environ["FLAG"] = "0"
    assert _bool("FLAG", default=True) is False
    os.environ.pop("FLAG", None)
    assert _bool("FLAG", default=True) is True
