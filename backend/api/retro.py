"""``/api/retro`` 路由。

四个端点（与 ``retro_insight_agent_demo_spec.md`` §6 对齐）：

- ``POST /api/retro/load/{video_id}``  → SSE 流式（LOAD → ... → PRESENT）
- ``POST /api/retro/drill``            → SSE 流式（DRILL）
- ``POST /api/retro/update-profile``   → JSON（UPDATE_PROFILE → FINALIZE）
- ``GET  /api/retro/report/{id}``      → JSON 读盘

Demo 单 persona 单 session：使用全局 dict 持有最近一次 RetroSession，
方便前端按 ``report_id`` 后续追问。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sse_starlette.sse import EventSourceResponse

from backend.agents.retro import RetroService
from backend.agents.retro.state_machine import RetroState
from backend.schemas import (
    AccountBaseline,
    NewVideoForRetro,
    Profile,
    StrategySnapshot,
)

# 演示路径上的三个视频
_ALL_VIDEO_IDS: tuple[str, ...] = ("vid_016", "vid_019", "vid_020")

# 用户在 chat dock 发这些关键词时触发自动写回画像
_UPDATE_PROFILE_KEYWORDS: frozenset[str] = frozenset(
    ["更新画像", "写入画像", "保存画像", "确认更新", "更新我的画像", "更新到画像"]
)

router = APIRouter(prefix="/api/retro", tags=["retro"])
_log = structlog.get_logger("api.retro")


def _get_service(request: Request) -> RetroService:
    """从 app.state 取 RetroService；未挂载时 503。"""
    svc = getattr(request.app.state, "retro_service", None)
    if svc is None:
        raise HTTPException(503, detail="retro service 未挂载，检查 startup 日志")
    return svc


def _get_sessions(request: Request) -> dict[str, Any]:
    """全局 session 字典（report_id → RetroSession）。"""
    sessions = getattr(request.app.state, "retro_sessions", None)
    if sessions is None:
        sessions = {}
        request.app.state.retro_sessions = sessions
    return sessions


def _get_bg_state(app_state: Any) -> dict[str, Any]:
    """获取或初始化后台分析状态字典。

    结构：
    - tasks:   video_id → asyncio.Task  （运行中的任务）
    - results: video_id → dict           （完成的四阶段输出）
    - errors:  video_id → str            （失败原因）
    """
    if not hasattr(app_state, "retro_bg"):
        app_state.retro_bg = {"tasks": {}, "results": {}, "errors": {}}
    return app_state.retro_bg  # type: ignore[no-any-return]


async def _bg_analyze_video(
    app_state: Any,
    svc: RetroService,
    video_id: str,
) -> None:
    """后台分析协程；由 asyncio.create_task() 调度，不随 HTTP 连接关闭而终止。

    完成后将四阶段输出写入 app_state.retro_bg["results"][video_id]，
    并调用 save_cache() 持久化为 per-video cache 文件。
    """
    bg = _get_bg_state(app_state)
    try:
        _log.info("retro.bg.start", video_id=video_id)
        video, baseline = _load_video_and_baseline(svc.mock_dir, video_id)
        profile = _resolve_profile(svc.runtime_dir, fallback_user_id="user_a_001")
        strategy = _resolve_strategy_snapshot(
            svc.runtime_dir,
            fallback_user_id=profile.meta.user_id,
            fallback_video_id=video_id,
        )

        session = svc.new_session(use_cache=False)
        session.load_inputs(
            video_id=video_id,
            profile=profile,
            strategy_snapshot=strategy,
            video=video.model_dump(mode="json"),
            baseline=baseline.model_dump(mode="json"),
        )

        await session.run_analysis_phases()
        session.save_cache()

        bg["results"][video_id] = {
            "compare_output": session.memory.comparison_grid,
            "attribute_output": session.memory.attributions,
            "extract_signals_output": session.memory.audience_signals,
            "synthesize_output": session.memory.insights_report_draft,
        }
        _log.info("retro.bg.done", video_id=video_id)
    except Exception as exc:
        _log.exception("retro.bg.error", video_id=video_id, err=str(exc))
        bg["errors"][video_id] = str(exc)
    finally:
        bg["tasks"].pop(video_id, None)


# ---------------- helpers ----------------

def _stub_strategy_snapshot(*, user_id: str, video_id: str) -> StrategySnapshot:
    """构造一个对齐演示故事线的 StrategySnapshot。

    M5 完成前先用这个 stub；M5 完成后改为读 ``runtime_data/strategy_snapshot_*.json``。
    """
    payload: dict[str, Any] = {
        "strategy_id": "str_001",
        "user_id": user_id,
        "profile_version": 1,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "input": {
            "mode": "idea_driven",
            "user_idea": "考研期间一日三餐怎么吃才能不困",
            "iterations": 1,
        },
        "idea": {
            "topic": "考研期间一日三餐",
            "predicted_pillar": "考研日常",
            "rationale": "融合食堂探店与考研身份双轴",
        },
        "heat_analysis": {
            "trend_score": 0.68,
            "trend_direction": "rising",
            "supply_demand_ratio": 0.4,
            "matched_trends": ["考研日常", "学生饮食"],
            "comment": "考研话题持续上行",
        },
        "profile_fit": {
            "pillar_alignment": [
                {"pillar": "考研日常", "alignment": "high", "evidence": "vid_004 完播 0.45"},
                {"pillar": "食堂探店", "alignment": "medium", "evidence": "近期食堂内容稳定"},
            ],
            "persona_leverage": [
                {
                    "trait": "真实考研身份",
                    "life_context": None,
                    "how_to_use": "前 3 秒用考研倒计时字幕建立身份认同",
                }
            ],
            "to_explore_validation": [
                {
                    "hypothesis_id": "h001",
                    "what_this_tests": "考研内容能否与既有食堂素材自然融合",
                }
            ],
            "fit_score": 0.78,
        },
        "differentiation": [
            {"point": "真实考研身份带来的同好共鸣", "source": "画像驱动"},
            {"point": "食堂场景作差异化锚点", "source": "数据驱动"},
        ],
        "execution": {
            "hook": {
                "design": "前 3 秒展示困到趴桌画面 + 字幕「考研第 67 天」",
                "rationale": "建立身份与情境同时抓注意力",
            },
            "pacing": "中段 3 个解决方案 + b-roll 食堂打饭",
            "cta": "结尾收口到「考研日常」",
            "tags": ["考研", "考研日常", "食堂", "学生饮食"],
            "key_focus": "新粉考研标签占比",
        },
    }
    return StrategySnapshot.model_validate(payload)


def _stub_profile(*, user_id: str) -> Profile:
    """构造一个对齐 onboarding v1 的 stub Profile。

    M4 完成前先用这个 stub；M4 完成后改为读 ``runtime_data/profile_v1.json``。
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "meta": {
            "user_id": user_id,
            "version": 1,
            "created_at": now,
            "session_id": "sess_demo_v1",
        },
        "confirmed": {
            "audience_baseline": {"core_segment": "在校大学生"},
            "content_pillars": [
                {"name": "食堂探店", "evidence_video_ids": ["vid_001", "vid_013"]},
                {"name": "考研日常", "evidence_video_ids": ["vid_004", "vid_010"]},
            ],
            "content_style": {"tone": "真实", "pace": "中速"},
        },
        "personalized": {
            "persona_traits": [
                {
                    "trait": "真实考研身份",
                    "evidence": [
                        {
                            "source_type": "comment",
                            "source_id": "cmt_0042",
                            "snippet": "考研中博主的日常太懂了",
                        }
                    ],
                }
            ],
            "life_context": [
                {
                    "context": "在校大三 · 考研倒计时阶段",
                    "valid_until": None,
                    "evidence": [],
                }
            ],
            "unique_assets": [],
        },
        "to_explore": {
            "open_questions": [],
            "hypotheses": [
                {
                    "hypothesis_id": "h001",
                    "hypothesis": "考研内容能与既有食堂、校园生活素材自然融合",
                    "status": "pending",
                    "evidence_for": [],
                    "evidence_against": [],
                }
            ],
            "aspirations": ["建立真实考研身份的差异化人设"],
        },
        "audit_log": [],
    }
    return Profile.model_validate(payload)


def _resolve_profile(runtime_dir: Path, fallback_user_id: str) -> Profile:
    """优先读 ``runtime_data`` 最新 profile，找不到降级用 stub。

    Parameters
    ----------
    runtime_dir : Path
        ``RetroService.runtime_dir``，即 ``<project_root>/runtime_data``。
    fallback_user_id : str
        没有真 profile 时给 stub 用的 user_id。

    Returns
    -------
    Profile
        优先 runtime；降级 stub。
    """
    if runtime_dir.is_dir():
        candidates = sorted(
            (p for p in runtime_dir.glob("profile_v*.json") if p.is_file()),
            key=lambda p: int(p.stem.removeprefix("profile_v")),
        )
        if candidates:
            return Profile.model_validate(
                json.loads(candidates[-1].read_text(encoding="utf-8"))
            )
    return _stub_profile(user_id=fallback_user_id)


def _resolve_strategy_snapshot(
    runtime_dir: Path,
    *,
    fallback_user_id: str,
    fallback_video_id: str,
) -> StrategySnapshot:
    """优先读 ``runtime_data`` 中最新（按 mtime）的 strategy_snapshot 文件。

    Strategy service 写盘格式：``strategy_snapshot_{snapshot_id}.json`` /
    ``strategy_snapshot_{snapshot_id}_v{n}.json``（refine approve 后的版本）。
    取 mtime 最新一份；找不到降级 stub。
    """
    if runtime_dir.is_dir():
        candidates = sorted(
            (p for p in runtime_dir.glob("strategy_snapshot_*.json") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
        if candidates:
            return StrategySnapshot.model_validate(
                json.loads(candidates[-1].read_text(encoding="utf-8"))
            )
    return _stub_strategy_snapshot(user_id=fallback_user_id, video_id=fallback_video_id)


def _load_video_and_baseline(mock_dir: Path, video_id: str) -> tuple[NewVideoForRetro, AccountBaseline]:
    """从 mock_data 加载视频与基线。

    优先加载 ``new_video_for_retro_{video_id}.json``（独立 mock），
    找不到则降级到 ``new_video_for_retro.json``（vid_020 通用 mock）并覆盖 ID。
    """
    # 优先尝试 per-video 文件
    per_video_path = mock_dir / f"new_video_for_retro_{video_id}.json"
    default_path = mock_dir / "new_video_for_retro.json"

    if per_video_path.is_file():
        video_path = per_video_path
    elif default_path.is_file():
        video_path = default_path
        _log.info("retro.load.video_id_fallback", requested=video_id, using="vid_020")
    else:
        raise HTTPException(404, detail="new_video_for_retro.json 缺失")

    video = NewVideoForRetro.model_validate(
        json.loads(video_path.read_text(encoding="utf-8"))
    )
    # 当 video_id 字段与请求不一致时（降级场景）补齐
    if video.video_id != video_id:
        video = video.model_copy(update={"video_id": video_id})

    baseline_path = mock_dir / "account_baseline.json"
    baseline = AccountBaseline.model_validate(
        json.loads(baseline_path.read_text(encoding="utf-8"))
    )
    return video, baseline


# ---------------- request models ----------------

class DrillRequest(BaseModel):
    """DRILL 请求体。"""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    user_text: str
    element_id: str = "dc_completion"
    element_type: str = "data_card"


class UpdateProfileRequest(BaseModel):
    """UPDATE_PROFILE 请求体。"""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    profile_version_in: int = 1


# ---------------- endpoints ----------------

@router.post("/prefetch")
async def prefetch_analysis(request: Request) -> dict[str, Any]:
    """为演示三视频启动后台 LLM 分析任务。

    已运行或已完成的视频跳过。任务挂载在 asyncio 事件循环，
    HTTP 连接关闭后任务继续运行。

    Returns
    -------
    dict
        started: 本次新启动的 video_id 列表
        already_done: 已有结果的 video_id 列表
        already_running: 已在运行的 video_id 列表
    """
    svc = _get_service(request)
    bg = _get_bg_state(request.app.state)

    started: list[str] = []
    already_done: list[str] = []
    already_running: list[str] = []

    for vid in _ALL_VIDEO_IDS:
        if vid in bg["results"]:
            already_done.append(vid)
        elif vid in bg["tasks"]:
            already_running.append(vid)
        else:
            bg["errors"].pop(vid, None)
            task = asyncio.create_task(
                _bg_analyze_video(request.app.state, svc, vid),
                name=f"retro_bg_{vid}",
            )
            bg["tasks"][vid] = task
            started.append(vid)

    _log.info("retro.prefetch", started=started, running=already_running, done=already_done)
    return {"started": started, "already_running": already_running, "already_done": already_done}


@router.get("/bg-status")
async def bg_status(request: Request) -> dict[str, Any]:
    """返回后台分析任务的状态（调试用）。"""
    bg = _get_bg_state(request.app.state)
    statuses: dict[str, str] = {}
    for vid in _ALL_VIDEO_IDS:
        if vid in bg["results"]:
            statuses[vid] = "done"
        elif vid in bg["tasks"]:
            statuses[vid] = "running"
        elif vid in bg["errors"]:
            statuses[vid] = f"error: {bg['errors'][vid][:80]}"
        else:
            statuses[vid] = "idle"
    return {"statuses": statuses}


@router.post("/load/{video_id}")
async def load_and_present(
    video_id: str,
    request: Request,
) -> EventSourceResponse:
    """加载视频 → 跑完 COMPARE/ATTRIBUTE/EXTRACT/SYNTHESIZE → PRESENT 流式。

    缓存策略由 ``Settings.use_cached_analysis``（环境变量 ``USE_CACHED_ANALYSIS``）决定，
    默认走 cache；前端不再传 ``mode`` query param。

    SSE 事件格式：
    - ``{"type": "stage", "stage": "...", "status": "ok"}``
    - ``{"type": "report", "report_id": "...", "draft": {...}}``
    - ``{"type": "present", "delta": "..."}``
    - ``{"type": "done"}``
    """
    svc = _get_service(request)
    use_cache: bool | None = None
    video, baseline = _load_video_and_baseline(svc.mock_dir, video_id)
    fallback_user_id = "user_a_001"
    profile = _resolve_profile(svc.runtime_dir, fallback_user_id=fallback_user_id)
    strategy = _resolve_strategy_snapshot(
        svc.runtime_dir,
        fallback_user_id=profile.meta.user_id,
        fallback_video_id=video_id,
    )

    session = svc.new_session(use_cache=use_cache)
    sessions = _get_sessions(request)
    sessions[session.report_id] = session

    session.load_inputs(
        video_id=video_id,
        profile=profile,
        strategy_snapshot=strategy,
        video=video.model_dump(mode="json"),
        baseline=baseline.model_dump(mode="json"),
    )

    # live 模式判断：显式 live 或 env 默认 live
    effective_live = use_cache is False or (
        use_cache is None and not svc.settings.use_cached_analysis
    )

    def _stage_evt(stage: str) -> dict[str, str]:
        return {"event": "message", "data": json.dumps({"type": "stage", "stage": stage, "status": "ok"}, ensure_ascii=False)}

    async def gen() -> AsyncIterator[dict[str, str]]:
        try:
            yield _stage_evt("LOAD")

            bg = _get_bg_state(request.app.state)

            if effective_live and video_id in bg["results"]:
                # 后台分析已完成：注入结果，不调 LLM（即时）
                _log.info("retro.load.bg_hit", video_id=video_id)
                session.inject_analysis_results(bg["results"][video_id])
                for stage in ("COMPARE", "ATTRIBUTE", "EXTRACT_SIGNALS", "SYNTHESIZE"):
                    yield _stage_evt(stage)

            elif effective_live and video_id in bg["tasks"]:
                # 后台任务进行中：等待（最多 5 分钟），保持 SSE 连接存活
                _log.info("retro.load.bg_wait", video_id=video_id)
                yield _stage_evt("COMPARE")
                waited = 0
                while video_id in bg["tasks"] and waited < 300:
                    await asyncio.sleep(2)
                    waited += 2

                if video_id in bg["errors"]:
                    yield {"event": "message", "data": json.dumps({"type": "error", "message": bg["errors"][video_id]}, ensure_ascii=False)}
                    return

                if video_id in bg["results"]:
                    session.inject_analysis_results(bg["results"][video_id])
                    for stage in ("ATTRIBUTE", "EXTRACT_SIGNALS", "SYNTHESIZE"):
                        yield _stage_evt(stage)
                else:
                    # 超时 fallback：inline live（不常见，兜底）
                    _log.warning("retro.load.bg_timeout_fallback", video_id=video_id)
                    async for ev_type, payload in session.run_analysis_phases_streaming():
                        if ev_type == "stage":
                            yield _stage_evt(payload)
                        elif ev_type == "thinking":
                            yield {"event": "message", "data": json.dumps({"type": "thinking.delta", "text": payload}, ensure_ascii=False)}
                    session.save_cache()

            else:
                # 正常流程（cache 模式 or inline live，无后台任务）
                async for ev_type, payload in session.run_analysis_phases_streaming():
                    if ev_type == "stage":
                        yield _stage_evt(payload)
                    elif ev_type == "thinking":
                        yield {"event": "message", "data": json.dumps({"type": "thinking.delta", "text": payload}, ensure_ascii=False)}
                if effective_live:
                    session.save_cache()

            yield {
                "event": "message",
                "data": json.dumps(
                    {
                        "type": "report",
                        "report_id": session.report_id,
                        "draft": session.memory.insights_report_draft,
                    },
                    ensure_ascii=False,
                ),
            }
            # PRESENT 阶段（含思考过程）
            async for chunk_type, chunk in session.stream_present_typed():
                if chunk_type == "thinking":
                    yield {"event": "message", "data": json.dumps({"type": "thinking.delta", "text": chunk}, ensure_ascii=False)}
                else:
                    _chunk_size = 24
                    for i in range(0, len(chunk), _chunk_size):
                        yield {"event": "message", "data": json.dumps({"type": "present", "delta": chunk[i : i + _chunk_size]}, ensure_ascii=False)}
            yield {"event": "message", "data": json.dumps({"type": "done"}, ensure_ascii=False)}
        except Exception as exc:  # pragma: no cover
            _log.exception("retro.load.failed", err=str(exc))
            yield {"event": "message", "data": json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/drill")
async def drill(req: DrillRequest, request: Request) -> EventSourceResponse:
    """DRILL：用户对 dashboard 元素追问，flash-thinking 流式输出。

    若用户文本含更新画像关键词（更新画像 / 写入画像 / 确认更新 等），
    drill 结束后自动执行 UPDATE_PROFILE → FINALIZE，并在 SSE 末尾
    emit ``{"type": "profile_updated", "profile_version_out": N}``。
    """
    sessions = _get_sessions(request)
    session = sessions.get(req.report_id)
    if session is None:
        raise HTTPException(404, detail=f"未找到 report_id={req.report_id} 对应的 session")

    should_update = any(kw in req.user_text for kw in _UPDATE_PROFILE_KEYWORDS)

    async def gen() -> AsyncIterator[dict[str, str]]:
        try:
            async for chunk in session.stream_drill(
                element_id=req.element_id,
                element_type=req.element_type,
                user_text=req.user_text,
            ):
                yield {"event": "message", "data": json.dumps({"type": "drill", "delta": chunk}, ensure_ascii=False)}

            # 检测到更新画像意图且状态允许（DRILL / PRESENT）
            if should_update and session.fsm.state in (RetroState.DRILL, RetroState.PRESENT):
                try:
                    profile_in = Profile.model_validate(session.memory.inputs["profile"])
                    delta, new_profile = await session.update_profile(profile_in=profile_in)
                    session.write_profile(new_profile)
                    session.finalize(
                        user_id="user_a_001",
                        video_id=session.memory.inputs["video_id"],
                        strategy_id=session.memory.inputs["strategy_snapshot"]["strategy_id"],
                        profile_version_in=profile_in.meta.version,
                        profile_delta=delta,
                    )
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {"type": "profile_updated", "profile_version_out": new_profile.meta.version},
                            ensure_ascii=False,
                        ),
                    }
                except Exception as exc:  # pragma: no cover
                    _log.warning("retro.drill.update_profile.failed", err=str(exc))

            yield {"event": "message", "data": json.dumps({"type": "done"}, ensure_ascii=False)}
        except Exception as exc:  # pragma: no cover
            _log.exception("retro.drill.failed", err=str(exc))
            yield {"event": "message", "data": json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)}

    return EventSourceResponse(gen())


@router.post("/update-profile")
async def update_profile(req: UpdateProfileRequest, request: Request) -> dict[str, Any]:
    """UPDATE_PROFILE → FINALIZE：生成 ProfileDelta + 合并 → 写 v(n+1) + InsightsReport。"""
    svc = _get_service(request)
    sessions = _get_sessions(request)
    session = sessions.get(req.report_id)
    if session is None:
        raise HTTPException(404, detail=f"未找到 report_id={req.report_id}")

    user_id = "user_a_001"
    # Demo 路径：先尝试读 runtime_data/profile_v{n}.json，没有则用 stub
    profile_path = svc.runtime_dir / f"profile_v{req.profile_version_in}.json"
    if profile_path.is_file():
        profile_in = Profile.model_validate(
            json.loads(profile_path.read_text(encoding="utf-8"))
        )
    else:
        profile_in = _stub_profile(user_id=user_id)

    delta, new_profile = await session.update_profile(profile_in=profile_in)
    new_path = session.write_profile(new_profile)
    report = session.finalize(
        user_id=user_id,
        video_id=session.memory.inputs["video_id"],
        strategy_id=session.memory.inputs["strategy_snapshot"]["strategy_id"],
        profile_version_in=profile_in.meta.version,
        profile_delta=delta,
    )

    return {
        "ok": True,
        "report_id": report.report_id,
        "profile_version_out": new_profile.meta.version,
        "profile_path": str(new_path),
        "report_path": str(svc.runtime_dir / f"insights_report_{report.report_id}.json"),
        "delta_summary": {
            "add_evidence": len(delta.add_evidence),
            "promote": len(delta.promote),
            "new_observations": len(delta.new_observations),
        },
    }


@router.get("/report/{report_id}")
async def get_report(report_id: str, request: Request) -> dict[str, Any]:
    """读盘 InsightsReport JSON。"""
    svc = _get_service(request)
    path = svc.runtime_dir / f"insights_report_{report_id}.json"
    if not path.is_file():
        raise HTTPException(404, detail=f"report 未找到：{path}")
    return json.loads(path.read_text(encoding="utf-8"))
