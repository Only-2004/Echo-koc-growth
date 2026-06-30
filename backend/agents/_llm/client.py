"""LLMClient 抽象 + DeepSeek 实现 + MockLLMClient 测试桩。

设计要点
========

* `ModelTier` 是 agent 层概念上的"模型档位"——flash / flash-thinking / pro-thinking。
  具体 model id 在 DeepSeekClient 内部从 Settings 解析，agent 只关心档位。
* 所有 agent 调用 LLM 都走 `complete`（一次性 JSON / 文本）或 `stream`（SSE 流式 token）。
* `MockLLMClient` 用 `(model, system 头部 hash, last user 头部 hash)` 三元组索引 fixture，
  允许测试用例按需注入"第一次坏 JSON / 第二次合法"等顺序响应。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# 可重试的 HTTP 状态码
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class _RetryableLLMError(Exception):
    """可重试的 LLM 调用错误（网络/限流/服务端错误）。"""

ModelTier = Literal["flash", "flash-thinking", "pro-thinking"]


def fixture_key(tier: ModelTier, system: str, last_user: str) -> str:
    """基于 (tier, system 前 80 字, last_user 前 40 字) 生成稳定 fixture key。

    Parameters
    ----------
    tier : ModelTier
        模型档位。
    system : str
        system prompt 文本。
    last_user : str
        当前轮 user message 文本。

    Returns
    -------
    str
        sha1 摘要前 16 字符。M4 onboarding 测试桩共用。
    """
    raw = f"{tier}|{system[:80]}|{last_user[:40]}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class LLMClient(ABC):
    """三档 DeepSeek 模型的统一接口。"""

    @abstractmethod
    async def complete(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """一次性返回完整文本。

        Parameters
        ----------
        model : ModelTier
            档位（flash / flash-thinking / pro-thinking）。
        system : str
            system prompt（贯穿全部调用的角色与原则）。
        messages : list of dict
            ``[{"role": "user"|"assistant", "content": "..."}]``。
        json_mode : bool, optional
            是否强制 JSON 输出（DeepSeek 需要在 prompt + response_format 双层约束）。
        temperature : float, optional
            采样温度。
        max_tokens : int, optional
            最大输出 token 数。

        Returns
        -------
        str
            完整文本。
        """

    @abstractmethod
    async def stream(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """逐 token 流式返回。

        实现注意：返回的应是 async generator，consumer 用 ``async for chunk in stream(...)``。
        """

    @abstractmethod
    async def stream_typed(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[tuple[str, str]]:
        """同 stream，但同时 yield thinking tokens。

        Yields
        ------
        tuple[str, str]
            ``("thinking", chunk)`` 或 ``("content", chunk)``。
            thinking 内容为模型推理过程（reasoning_content）；
            content 为最终输出。非 thinking 档（flash）只 yield content。
        """


# ---------------------------------------------------------------------------
# DeepSeek 实现（演示路径在主仓库跑；worktree 测试用 MockLLMClient）
# ---------------------------------------------------------------------------


class DeepSeekClient(LLMClient):
    """openai SDK 走 DeepSeek openai-compatible endpoint。

    DeepSeek 实际只暴露两档 model id（``deepseek-v4-flash`` / ``deepseek-v4-pro``）；
    本仓库 agent 层概念上的三档 ``ModelTier`` 由 client 内部映射：

    - ``flash`` → flash 模型，不启 thinking
    - ``flash-thinking`` → flash 模型 + ``thinking.enabled`` + ``reasoning_effort=medium``
    - ``pro-thinking`` → pro 模型 + ``thinking.enabled`` + ``reasoning_effort=high``

    thinking / reasoning_effort 通过 openai SDK 的 ``extra_body`` 透传，
    DeepSeek 端按 vendor 协议解析。
    """

    def __init__(
        self,
        *,
        api_key: str,
        api_base: str,
        model_flash: str,
        model_pro: str,
        max_tokens_by_tier: dict[ModelTier, int],
        max_retries: int = 2,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 8.0,
        timeout_first_token: float = 8.0,
        timeout_total: float = 30.0,
    ) -> None:
        """构造 DeepSeek 客户端。

        Parameters
        ----------
        api_key : str
            DeepSeek API key。
        api_base : str
            openai-compatible endpoint（如 ``https://api.deepseek.com/v1``）。
        model_flash : str
            DeepSeek flash 档 model id（驱动 ``flash`` 与 ``flash-thinking``）。
        model_pro : str
            DeepSeek pro 档 model id（驱动 ``pro-thinking``）。
        max_tokens_by_tier : dict[ModelTier, int]
            每档 ``max_tokens`` 下限。thinking 档的 reasoning tokens 也计入此预算，
            建议 thinking 档至少 8192，pro-thinking 16384。调用方传入的
            ``max_tokens`` 仍可上调，但不会被下调到此值以下。
        max_retries : int
            最大重试次数（不含首次调用）。默认 2。
        retry_min_wait : float
            重试等待下限（秒）。默认 1。
        retry_max_wait : float
            重试等待上限（秒）。默认 8。
        timeout_first_token : float
            首 token 超时（秒）。默认 8。
        timeout_total : float
            总超时（秒）。默认 30。
        """
        # 延迟 import openai：测试环境若未装也不影响 MockLLMClient
        from openai import AsyncOpenAI  # noqa: PLC0415

        timeout = httpx.Timeout(
            connect=10.0,
            read=timeout_total,
            write=10.0,
            pool=10.0,
        )
        self._client = AsyncOpenAI(api_key=api_key, base_url=api_base, timeout=timeout)
        # ModelTier → (实际 model id, extra_body 中的 thinking 配置)
        self._tier_to_config: dict[ModelTier, tuple[str, dict[str, object] | None]] = {
            "flash": (model_flash, None),
            "flash-thinking": (
                model_flash,
                {"thinking": {"type": "enabled"}, "reasoning_effort": "medium"},
            ),
            "pro-thinking": (
                model_pro,
                {"thinking": {"type": "enabled"}, "reasoning_effort": "high"},
            ),
        }
        self._max_tokens_by_tier = dict(max_tokens_by_tier)
        self._max_retries = max_retries
        self._retry_min_wait = retry_min_wait
        self._retry_max_wait = retry_max_wait
        self._timeout_first_token = timeout_first_token

    @classmethod
    def from_settings(cls, settings: object) -> DeepSeekClient:
        """从 ``Settings`` 构造，避免在 5 处调用点重复 wiring。

        Parameters
        ----------
        settings : Settings
            ``backend.config.Settings``；这里用 object 注解避免循环 import，
            实际访问字段在运行时校验。
        """
        return cls(
            api_key=settings.deepseek_api_key,  # type: ignore[attr-defined]
            api_base=settings.deepseek_api_base,  # type: ignore[attr-defined]
            model_flash=settings.model_flash,  # type: ignore[attr-defined]
            model_pro=settings.model_pro,  # type: ignore[attr-defined]
            max_tokens_by_tier={
                "flash": settings.max_tokens_flash,  # type: ignore[attr-defined]
                "flash-thinking": settings.max_tokens_flash_thinking,  # type: ignore[attr-defined]
                "pro-thinking": settings.max_tokens_pro_thinking,  # type: ignore[attr-defined]
            },
            max_retries=settings.llm_max_retries,  # type: ignore[attr-defined]
            retry_min_wait=settings.llm_retry_min_wait,  # type: ignore[attr-defined]
            retry_max_wait=settings.llm_retry_max_wait,  # type: ignore[attr-defined]
            timeout_first_token=settings.llm_timeout_first_token,  # type: ignore[attr-defined]
            timeout_total=settings.llm_timeout_total,  # type: ignore[attr-defined]
        )

    def _resolve(self, tier: ModelTier) -> tuple[str, dict[str, object] | None]:
        """档位 → (model id, extra_body thinking 配置或 None)。"""
        return self._tier_to_config[tier]

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """判断异常是否可重试（429/5xx/网络错误）。"""
        import openai  # noqa: PLC0415
        if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)):
            return True
        if isinstance(exc, openai.APITimeoutError | openai.APIConnectionError):
            return True
        if isinstance(exc, openai.APIStatusError) and exc.status_code in _RETRYABLE_STATUS:
            return True
        if isinstance(exc, openai.RateLimitError):
            return True
        return False

    def _make_retry_decorator(self):
        """构造 tenacity retry 装饰器。"""
        return retry(
            retry=retry_if_exception_type(_RetryableLLMError),
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential(
                min=self._retry_min_wait,
                max=self._retry_max_wait,
            ),
            reraise=True,
            before_sleep=lambda retry_state: logger.warning(
                "LLM 调用重试 attempt=%d, wait=%.1fs, error=%s",
                retry_state.attempt_number,
                retry_state.next_action.sleep if retry_state.next_action else 0,
                retry_state.outcome.exception() if retry_state.outcome else "unknown",
            ),
        )

    async def _retry_call(self, coro_factory):
        """包装一个协程工厂，遇到可重试异常时 tenacity 重试。

        Parameters
        ----------
        coro_factory : callable
            返回协程的无参工厂函数。

        Returns
        -------
        Any
            协程返回值。
        """
        decorated = self._make_retry_decorator()(coro_factory)
        return await decorated()

    async def complete(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """调 DeepSeek chat completion。

        Notes
        -----
        ``json_mode`` 与 thinking（``extra_body.thinking.enabled``）不兼容：
        同时设置会导致 ``content`` 为空。当 thinking 激活时跳过
        ``response_format``，依赖 prompt 中的 JSON 指令。

        thinking 模式下 reasoning tokens 计入 ``max_tokens`` 总额；预算太小
        会被推理独白吃光，content 为空。所以 ``max_tokens`` 取调用方值
        与 ``_max_tokens_by_tier[tier]`` 中的较大者作为下限。content 为空
        时不 fallback 到 ``reasoning_content``（那是 chain-of-thought，
        不是答案）—— 直接返回空让上层重试或报错。
        """
        model_id, extra = self._resolve(model)
        request_messages = [{"role": "system", "content": system}, *messages]
        tier_floor = self._max_tokens_by_tier.get(model, max_tokens)
        effective_max_tokens = max(max_tokens, tier_floor)
        kwargs: dict[str, object] = {
            "model": model_id,
            "messages": request_messages,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
        }
        # thinking 启用时不设 response_format（两者 API 不兼容）
        if json_mode and extra is None:
            kwargs["response_format"] = {"type": "json_object"}
        if extra is not None:
            kwargs["extra_body"] = extra

        async def _call():
            try:
                return await self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
            except Exception as exc:
                if self._is_retryable(exc):
                    raise _RetryableLLMError(str(exc)) from exc
                raise

        response = await self._retry_call(_call)
        message = response.choices[0].message
        content = message.content or ""
        # json_mode 但 thinking 启用时 response_format 被跳过，模型可能输出
        # markdown 代码块包裹的 JSON，在这里统一剥离
        if json_mode and content.startswith("```"):
            for prefix in ("```json\n", "```json\r\n", "```\n", "```\r\n"):
                if content.startswith(prefix):
                    content = content.removeprefix(prefix)
                    break
            if content.endswith("```"):
                content = content.removesuffix("```")
            content = content.strip()
        return content

    async def stream(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """流式 yield token 文本片段（含连接级重试）。"""
        model_id, extra = self._resolve(model)
        request_messages = [{"role": "system", "content": system}, *messages]
        tier_floor = self._max_tokens_by_tier.get(model, max_tokens)
        kwargs: dict[str, object] = {
            "model": model_id,
            "messages": request_messages,
            "temperature": temperature,
            "max_tokens": max(max_tokens, tier_floor),
            "stream": True,
        }
        if extra is not None:
            kwargs["extra_body"] = extra

        async def _connect():
            try:
                return await self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
            except Exception as exc:
                if self._is_retryable(exc):
                    raise _RetryableLLMError(str(exc)) from exc
                raise

        stream = await self._retry_call(_connect)
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def stream_typed(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[tuple[str, str]]:
        """同 stream，但同时 yield thinking tokens。"""
        model_id, extra = self._resolve(model)
        request_messages = [{"role": "system", "content": system}, *messages]
        tier_floor = self._max_tokens_by_tier.get(model, max_tokens)
        kwargs: dict[str, object] = {
            "model": model_id,
            "messages": request_messages,
            "temperature": temperature,
            "max_tokens": max(max_tokens, tier_floor),
            "stream": True,
        }
        if extra is not None:
            kwargs["extra_body"] = extra

        async def _connect():
            try:
                return await self._client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
            except Exception as exc:
                if self._is_retryable(exc):
                    raise _RetryableLLMError(str(exc)) from exc
                raise

        stream = await self._retry_call(_connect)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            # reasoning_content 是 DeepSeek thinking 模式特有字段
            thinking = getattr(delta, "reasoning_content", None)
            content = getattr(delta, "content", None)
            if thinking:
                yield ("thinking", thinking)
            if content:
                yield ("content", content)


# ---------------------------------------------------------------------------
# Mock 测试桩
# ---------------------------------------------------------------------------


@dataclass
class MockResponseSpec:
    """单条 fixture 配置：一次 LLM 调用应返回什么。"""

    text: str
    """完整返回文本（complete 整段返；stream 按 ``stream_chunk_chars`` 切片返）。"""

    stream_chunk_chars: int = 20
    """stream 模式下每片 token 字符数。"""

    stage_key: str | None = None
    """（M6 兼容）register() 注入的 stage 标记，complete/stream 出队时写到 call_log。"""


@dataclass
class MockLLMClient(LLMClient):
    """测试桩：按 (model_tier, marker) 索引 fixture，支持顺序队列。

    使用方式
    --------
    >>> client = MockLLMClient()
    >>> client.queue("pro-thinking", marker="score", responses=[
    ...     MockResponseSpec("not json"),               # 第一次：JSON parse 错误
    ...     MockResponseSpec('{"heat_analysis": ...}'), # 第二次：retry 通过
    ... ])
    >>> # 调用方在 prompt user message 中包含 "marker:score"，桩按队列顺序返回

    Marker 使用 ``[MARKER:xxx]`` 字面字符串嵌入 user message 任意位置。
    若未匹配到 marker，按 ``default_responses`` 返回（也是顺序队列）。
    """

    fixtures: dict[tuple[ModelTier, str], list[MockResponseSpec]] = field(default_factory=dict)
    default_responses: list[MockResponseSpec] = field(default_factory=list)
    call_log: list[dict[str, object]] = field(default_factory=list)

    def queue(
        self,
        model: ModelTier,
        *,
        marker: str,
        responses: list[MockResponseSpec],
    ) -> None:
        """M5 风格：登记一组按 [MARKER:xxx] 路由的 fixture。"""
        self.fixtures[(model, marker)] = list(responses)

    def queue_default(self, *, responses: list[MockResponseSpec]) -> None:
        """登记 default 队列（无 marker 命中时使用）。"""
        self.default_responses = list(responses)

    def register(self, stage_key: str, response: str) -> None:
        """M6 风格：FIFO push 一条 response 到 default 队列；stage_key 写到 call_log。

        Notes
        -----
        M6 测试按 LLM 实际调用顺序 register，default_responses FIFO 即可匹配；
        若需要 retry 路径在同一 stage 给多条响应，用 ``register_sequence``。
        """
        self.default_responses.append(
            MockResponseSpec(text=response, stream_chunk_chars=20, stage_key=stage_key)
        )

    def register_sequence(self, stage_key: str, responses: list[str]) -> None:
        """M6 风格：批量 FIFO push 多条 response 到 default 队列。"""
        for r in responses:
            self.register(stage_key, r)

    def route(  # noqa: D401 - M6 兼容 stub
        self, *, model: ModelTier, system_prefix: str, user_text: str, stage_key: str
    ) -> None:
        """M6 兼容 no-op：M5 版用 [MARKER:] 路由 + default FIFO 退化，无需 hash 路由。"""
        return None

    @staticmethod
    def _detect_marker(messages: list[dict[str, str]]) -> str | None:
        """从最后一条 user message 中找 ``[MARKER:xxx]``，返回 xxx；找不到返 None。"""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                start = content.find("[MARKER:")
                if start != -1:
                    end = content.find("]", start)
                    if end != -1:
                        return content[start + len("[MARKER:") : end]
                break
        return None

    def _next_spec(self, model: ModelTier, messages: list[dict[str, str]]) -> MockResponseSpec:
        marker = self._detect_marker(messages)
        if marker is not None:
            queue = self.fixtures.get((model, marker), [])
            if queue:
                return queue.pop(0)
        if self.default_responses:
            return self.default_responses.pop(0)
        # 最后兜底：把整个调用 hash 出来当文本，便于测试时观察异常
        digest = hashlib.sha1(json.dumps(messages, ensure_ascii=False).encode()).hexdigest()[:8]
        return MockResponseSpec(text=f"<mock-fallback:{model}:{digest}>")

    async def complete(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """同步从队列中取下一条 fixture。"""
        spec = self._next_spec(model, messages)
        self.call_log.append(
            {
                "kind": "complete",
                "model": model,
                "system_head": system[:40],
                "marker": self._detect_marker(messages),
                "stage_key": spec.stage_key,
                "json_mode": json_mode,
            }
        )
        return spec.text

    async def stream(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """按 ``stream_chunk_chars`` 切片 yield。"""
        spec = self._next_spec(model, messages)
        self.call_log.append(
            {
                "kind": "stream",
                "model": model,
                "system_head": system[:40],
                "marker": self._detect_marker(messages),
                "stage_key": spec.stage_key,
            }
        )
        text = spec.text
        size = max(1, spec.stream_chunk_chars)
        for i in range(0, len(text), size):
            yield text[i : i + size]

    async def stream_typed(
        self,
        *,
        model: ModelTier,
        system: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[tuple[str, str]]:
        """Mock 实现：全部 yield 为 content（无 thinking 内容）。"""
        async for chunk in self.stream(
            model=model,
            system=system,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield ("content", chunk)
