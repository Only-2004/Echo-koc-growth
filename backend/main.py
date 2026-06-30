"""Beacon 后端入口（FastAPI app）。

按里程碑挂载路由：
- M0 /api/health
- M1 /api/mock/*（仅 enable_mock_debug 时挂）
- M4 /api/onboarding/*
- M5 /api/strategy/*
- M6 /api/retro/*
- M7 /api/orchestrator/*
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .agents._llm import DeepSeekClient, MockLLMClient
from .agents.onboarding import OnboardingService
from .agents.orchestrator import OrchestratorService
from .agents.retro import RetroService
from .agents.strategy.service import StrategyService, StrategyServiceConfig
from .api import admin as admin_routes
from .api import log as log_routes
from .api import mock as mock_routes
from .api import onboarding as onboarding_routes
from .api import orchestrator as orchestrator_routes
from .api import profile as profile_routes
from .api import retro as retro_routes
from .api import strategy as strategy_routes
from .config import Settings, load_settings
from .mock_loader import load_mock_bundle


def configure_logging(level: str) -> None:
    """配置 structlog + 标准 logging。

    Parameters
    ----------
    level : str
        日志级别名（debug / info / warning / error）。
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """构造 FastAPI app。

    Parameters
    ----------
    settings : Settings, optional
        配置对象；为空则用 load_settings(require_keys=False)（M0 默认）。

    Returns
    -------
    FastAPI
        已挂载基础中间件 + /api/health + onboarding + strategy + retro 路由。
    """
    cfg = settings or load_settings(require_keys=False)
    configure_logging(cfg.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """启动时加载 mock 数据并构建 onboarding / strategy / retro service。

        - mock 数据 schema 校验失败 → 直接 fail
        - DEEPSEEK_API_KEY 未填 → 用 MockLLMClient（worktree / detached HEAD
          也能跑非真 LLM 路径；演示走 USE_CACHED_ANALYSIS=true + cache 兜底）
        """
        try:
            bundle = load_mock_bundle()
            app.state.mock = bundle
        except Exception as exc:  # pragma: no cover - 启动失败立即可见
            raise RuntimeError(f"mock 数据加载失败：{exc}") from exc

        llm = (
            DeepSeekClient.from_settings(cfg)
            if cfg.deepseek_api_key
            else MockLLMClient()
        )
        app.state.onboarding = OnboardingService(llm=llm, bundle=bundle, settings=cfg)
        app.state.strategy = _build_strategy_service(cfg, llm, bundle)
        app.state.retro_service = RetroService(llm=llm, settings=cfg)
        app.state.retro_sessions = {}
        app.state.orchestrator = OrchestratorService(
            client=llm,
            runtime_dir=Path(__file__).resolve().parents[1] / "runtime_data",
        )
        yield

    app = FastAPI(
        title="Beacon · KOC 成长伙伴 · API",
        version="0.1.0",
        description="DeepSeek v4 驱动的 KOC 成长伙伴后端。详见 PRD §4 §9。",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cfg.cors_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    async def health() -> dict[str, object]:
        """健康检查。生产环境返回最少信息（不泄露 settings）。"""
        return {
            "ok": True,
            "service": "beacon-backend",
            "version": app.version,
        }

    if cfg.enable_mock_debug:
        app.include_router(mock_routes.router)
    app.include_router(onboarding_routes.router)
    app.include_router(profile_routes.router)
    app.include_router(strategy_routes.router)
    app.include_router(retro_routes.router)
    app.include_router(orchestrator_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(log_routes.router)

    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """注册全量异常处理器：4xx / 5xx / unhandled 全打 structlog。

    SSE 流式路径里 generator 内部抛异常已由 sse_starlette 处理；这里只兜底
    路由层 / 中间件层未捕获异常，保证生产可观测。
    """

    err_logger = structlog.get_logger("beacon.error")

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # 4xx 一律 warning，避免与 5xx 混淆
        log = err_logger.warning if exc.status_code < 500 else err_logger.error
        log(
            "http_exception",
            path=request.url.path,
            method=request.method,
            status=exc.status_code,
            detail=exc.detail,
            client=request.client.host if request.client else None,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "http_error", "status": exc.status_code, "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        err_logger.warning(
            "request_validation_error",
            path=request.url.path,
            method=request.method,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={"error": "validation_error", "detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _unhandled_exc_handler(request: Request, exc: Exception) -> JSONResponse:
        # structlog .exception 自动带 traceback
        err_logger.exception(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            client=request.client.host if request.client else None,
            exc_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "type": type(exc).__name__},
        )


def _build_strategy_service(
    cfg: Settings,
    client: DeepSeekClient | MockLLMClient,
    mock_bundle: object,
) -> StrategyService:
    """构造 :class:`StrategyService`。共享 onboarding 的 LLM client。

    runtime_dir 与 onboarding / retro 对齐到 ``<project_root>/runtime_data``，
    保证三个 agent 写盘 / 读盘指向同一目录（闭环依赖）。
    """
    project_root = Path(__file__).resolve().parents[1]
    cache_path = project_root / "cache" / "strategy_score_strategize.json"
    runtime_dir = project_root / "runtime_data"

    return StrategyService(
        client=client,
        config=StrategyServiceConfig(
            use_cached_analysis=cfg.use_cached_analysis,
            cache_path=cache_path,
            runtime_dir=runtime_dir,
        ),
        mock_bundle=mock_bundle,
    )


# uvicorn main:app
app = create_app()
