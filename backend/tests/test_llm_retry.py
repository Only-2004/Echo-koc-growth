"""T49: LLM 全链路 retry + 超时测试。

测试 DeepSeekClient 的 tenacity 重试行为：
- 429/5xx 自动重试
- 网络错误自动重试
- 非可重试错误直接抛出
- 重试成功后正常返回
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents._llm.client import DeepSeekClient, _RetryableLLMError


@pytest.fixture
def client() -> DeepSeekClient:
    """构造一个 max_retries=2 的测试客户端，mock 掉底层 openai client。"""
    c = DeepSeekClient.__new__(DeepSeekClient)
    # 直接设置内部属性，绕过 AsyncOpenAI 构造
    c._client = MagicMock()
    c._tier_to_config = {
        "flash": ("deepseek-v4-flash", None),
        "flash-thinking": ("deepseek-v4-flash", {"thinking": {"type": "enabled"}, "reasoning_effort": "medium"}),
        "pro-thinking": ("deepseek-v4-pro", {"thinking": {"type": "enabled"}, "reasoning_effort": "high"}),
    }
    c._max_tokens_by_tier = {"flash": 2048, "flash-thinking": 8192, "pro-thinking": 16384}
    c._max_retries = 2
    c._retry_min_wait = 0.01
    c._retry_max_wait = 0.02
    c._timeout_first_token = 8.0
    c._timeout_total = 30.0
    return c


class TestIsRetryable:
    """_is_retryable 静态方法测试。"""

    def test_rate_limit_is_retryable(self) -> None:
        import httpx
        from openai import RateLimitError

        exc = RateLimitError(
            response=MagicMock(status_code=429, headers={}),
            message="rate limited",
            body=None,
        )
        assert DeepSeekClient._is_retryable(exc) is True

    def test_server_error_is_retryable(self) -> None:
        from openai import APIStatusError

        exc = APIStatusError(
            message="server error",
            response=MagicMock(status_code=500, headers={}),
            body=None,
        )
        assert DeepSeekClient._is_retryable(exc) is True

    def test_timeout_is_retryable(self) -> None:
        import httpx

        exc = httpx.TimeoutException("timeout")
        assert DeepSeekClient._is_retryable(exc) is True

    def test_connect_error_is_retryable(self) -> None:
        import httpx

        exc = httpx.ConnectError("connection refused")
        assert DeepSeekClient._is_retryable(exc) is True

    def test_auth_error_is_not_retryable(self) -> None:
        from openai import AuthenticationError

        exc = AuthenticationError(
            response=MagicMock(status_code=401, headers={}),
            message="invalid key",
            body=None,
        )
        assert DeepSeekClient._is_retryable(exc) is False

    def test_validation_error_is_not_retryable(self) -> None:
        from openai import BadRequestError

        exc = BadRequestError(
            response=MagicMock(status_code=400, headers={}),
            message="bad request",
            body=None,
        )
        assert DeepSeekClient._is_retryable(exc) is False


class TestCompleteRetry:
    """complete() 方法的重试行为测试。"""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self, client: DeepSeekClient) -> None:
        """正常响应不触发重试。"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="hello"))]
        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.complete(
            model="flash",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result == "hello"
        assert client._client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit_then_success(self, client: DeepSeekClient) -> None:
        """第一次 429，第二次成功。"""
        from openai import RateLimitError

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError(
                    response=MagicMock(status_code=429, headers={}),
                    message="rate limited",
                    body=None,
                )
            return mock_response

        client._client.chat.completions.create = AsyncMock(side_effect=side_effect)

        result = await client.complete(
            model="flash",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, client: DeepSeekClient) -> None:
        """重试全部失败后抛出异常。"""
        from openai import RateLimitError

        async def always_fail(**kwargs):
            raise RateLimitError(
                response=MagicMock(status_code=429, headers={}),
                message="rate limited",
                body=None,
            )

        client._client.chat.completions.create = AsyncMock(side_effect=always_fail)

        with pytest.raises(_RetryableLLMError):
            await client.complete(
                model="flash",
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
            )
        # 1 initial + 2 retries = 3 attempts
        assert client._client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self, client: DeepSeekClient) -> None:
        """非可重试错误（如 401）不重试，直接抛出。"""
        from openai import AuthenticationError

        async def auth_fail(**kwargs):
            raise AuthenticationError(
                response=MagicMock(status_code=401, headers={}),
                message="invalid key",
                body=None,
            )

        client._client.chat.completions.create = AsyncMock(side_effect=auth_fail)

        with pytest.raises(AuthenticationError):
            await client.complete(
                model="flash",
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
            )
        assert client._client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_json_mode_retry_then_success(self, client: DeepSeekClient) -> None:
        """JSON 模式下重试成功。"""
        from openai import APIStatusError

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"result": "ok"}'))]

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise APIStatusError(
                    message="server error",
                    response=MagicMock(status_code=503, headers={}),
                    body=None,
                )
            return mock_response

        client._client.chat.completions.create = AsyncMock(side_effect=side_effect)

        result = await client.complete(
            model="flash",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            json_mode=True,
        )
        assert result == '{"result": "ok"}'
        assert call_count == 2
