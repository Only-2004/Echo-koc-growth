"""``/api/profile/*`` 路由（M4-M6 闭环新增）。

端点：

- ``GET /api/profile/status`` — 前端 boot 时拉，判断 onboarding 是否已完成
- ``GET /api/profile/{version}`` — 拿指定版本的 Profile JSON
- ``GET /api/profile/`` — 默认拿最新版本（前端 ProfileView 用）
- ``POST /api/profile/reset`` — Demo 重置：删除 v4+ profile，清空 service 内存 session

设计：

- ``runtime_data/profile_v{n}.json`` 是 onboarding finalize / retro update_profile 的写盘约定
- 本路由只做读，不做写（reset 是 demo 专属的特殊例外）
- 找 latest 版本：扫文件名取最大 n
- 从 ``app.state.onboarding`` 取 service 拿 ``runtime_dir``（与 onboarding 同源，避免硬编码）

详见 ``.claude/tasks/m4-m6-frontend-loop/plan.md`` Phase A。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..schemas.profile import Profile

router = APIRouter(prefix="/api/profile", tags=["profile"])

_VERSION_PATTERN = re.compile(r"^profile_v(\d+)\.json$")


def _runtime_dir(request: Request) -> Path:
    """从 onboarding service 取 runtime_dir（保持单一来源）。

    Returns
    -------
    Path
        ``<project_root>/runtime_data`` 实例（onboarding service 默认值）。

    Raises
    ------
    HTTPException(503)
        onboarding service 未挂载（启动顺序异常）。
    """
    svc = getattr(request.app.state, "onboarding", None)
    if svc is None:
        raise HTTPException(503, detail="onboarding service 未挂载")
    return svc._runtime_dir  # type: ignore[attr-defined]


def _scan_versions(runtime_dir: Path) -> list[int]:
    """扫 ``runtime_data/`` 列出所有 profile 版本号。

    Returns
    -------
    list[int]
        版本号升序排序，未找到返回空 list。
    """
    if not runtime_dir.is_dir():
        return []
    versions: list[int] = []
    for entry in runtime_dir.iterdir():
        if not entry.is_file():
            continue
        match = _VERSION_PATTERN.match(entry.name)
        if match:
            versions.append(int(match.group(1)))
    return sorted(versions)


def _load_profile(runtime_dir: Path, version: int) -> Profile:
    """读盘并 schema 校验。

    Raises
    ------
    HTTPException(404)
        指定版本文件不存在。
    """
    path = runtime_dir / f"profile_v{version}.json"
    if not path.is_file():
        raise HTTPException(404, detail=f"profile_v{version}.json 不存在")
    return Profile.model_validate(json.loads(path.read_text(encoding="utf-8")))


@router.get("/status")
async def get_profile_status(request: Request) -> dict[str, Any]:
    """profile 状态查询（前端 boot 时调）。

    Returns
    -------
    dict
        ``{"exists": bool, "latest_version": int | None, "user_id": str | None,
        "available_versions": list[int]}``
    """
    runtime_dir = _runtime_dir(request)
    versions = _scan_versions(runtime_dir)
    if not versions:
        return {
            "exists": False,
            "latest_version": None,
            "user_id": None,
            "available_versions": [],
        }
    latest = versions[-1]
    profile = _load_profile(runtime_dir, latest)
    return {
        "exists": True,
        "latest_version": latest,
        "user_id": profile.meta.user_id,
        "available_versions": versions,
    }


@router.get("/")
async def get_latest_profile(request: Request) -> dict[str, Any]:
    """读最新版本 Profile（前端 ProfileView 默认调用）。"""
    runtime_dir = _runtime_dir(request)
    versions = _scan_versions(runtime_dir)
    if not versions:
        raise HTTPException(404, detail="没有任何 profile 版本（未跑过 onboarding finalize）")
    return _load_profile(runtime_dir, versions[-1]).model_dump(mode="json")


@router.get("/{version}")
async def get_profile_by_version(version: int, request: Request) -> dict[str, Any]:
    """读指定版本 Profile（前端 ProfileView History strip 用）。"""
    runtime_dir = _runtime_dir(request)
    return _load_profile(runtime_dir, version).model_dump(mode="json")


# Demo 重置端点常量
_RESET_KEEP_VERSIONS: int = 3


@router.post("/reset")
async def reset_demo(request: Request) -> dict[str, Any]:
    """Demo 重置：删除 profile_v{n>3}.json，清空 service 内存 session。

    Returns
    -------
    dict
        ``{"reset_to": 3, "deleted": [...], "latest_version": 3}``
    """
    runtime_dir = _runtime_dir(request)
    deleted: list[str] = []
    for entry in runtime_dir.iterdir():
        if not entry.is_file():
            continue
        m = _VERSION_PATTERN.match(entry.name)
        if m and int(m.group(1)) > _RESET_KEEP_VERSIONS:
            entry.unlink()
            deleted.append(entry.name)

    # 清空 onboarding / strategy service 的内存 session，避免残留状态
    onb_svc = getattr(request.app.state, "onboarding", None)
    if onb_svc is not None and hasattr(onb_svc, "_sessions"):
        onb_svc._sessions.clear()

    strategy_svc = getattr(request.app.state, "strategy", None)
    if strategy_svc is not None:
        if hasattr(strategy_svc, "_sessions"):
            strategy_svc._sessions.clear()
        if hasattr(strategy_svc, "_snapshots"):
            strategy_svc._snapshots.clear()
        if hasattr(strategy_svc, "_snapshot_versions"):
            strategy_svc._snapshot_versions.clear()

    return {
        "reset_to": _RESET_KEEP_VERSIONS,
        "deleted": sorted(deleted),
        "latest_version": _RESET_KEEP_VERSIONS,
    }
