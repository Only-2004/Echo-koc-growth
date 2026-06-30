"""按 ``needs_slices`` 装配 chat 阶段需要的数据切片（M7 · Step 3）。

输入：

- ``scene``：当前 scene（home / onboard / profile / ideate / retro）
- ``needs_slices``：route 阶段决定的子集（``["profile", "strategy", "retro"]`` 任意子集）
- ``runtime_dir``：``runtime_data/`` 目录，从中读取最新的 profile / strategy / retro

输出：一个简短的 dict，每个 slice key 对应一段紧凑的 markdown / json 文本，
单 slice 控制在 ~1500 字符以内（避免 prompt 超长）。

切片选择规则：

- ``profile``：读 ``profile_v{max_n}.json``，提取三态前 3 项 + audit 最近 3 行
- ``strategy``：读 ``strategy_snapshot_*.json`` 最新一份（按 mtime），提取核心字段
- ``retro``：读 ``insights_report_*.json`` 最新一份，提取 strategy_review 摘要 + top 3 insights

文件不存在时该 slice 返回 None，不报错——demo 真实场景下用户可能还没走到那一步。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

import structlog

_log = structlog.get_logger("orchestrator.context")

Scene = Literal["home", "onboard", "profile", "ideate", "retro"]
SliceKey = Literal["profile", "strategy", "retro"]

# 单 slice 字符上限，防 prompt 爆炸
_MAX_SLICE_CHARS = 1500


# ---------------- 公共入口 ----------------


def build_context(
    scene: Scene,
    needs_slices: list[SliceKey],
    runtime_dir: Path,
) -> dict[str, str]:
    """按 ``needs_slices`` 拼上下文切片。

    Parameters
    ----------
    scene : Scene
        当前 scene。当前实现里 scene 只用于日志；真正决定切片的是 ``needs_slices``。
    needs_slices : list[SliceKey]
        route 阶段返回的子集（可空）。
    runtime_dir : Path
        runtime_data 目录。

    Returns
    -------
    dict[str, str]
        key 为 slice 名（"profile" / "strategy" / "retro"），value 为已裁剪的文本块。
        切片文件不存在或读取失败时该 key 不出现在 dict 中。
    """
    out: dict[str, str] = {}

    if "profile" in needs_slices:
        slice_text = _build_profile_slice(runtime_dir)
        if slice_text:
            out["profile"] = slice_text
    if "strategy" in needs_slices:
        slice_text = _build_strategy_slice(runtime_dir)
        if slice_text:
            out["strategy"] = slice_text
    if "retro" in needs_slices:
        slice_text = _build_retro_slice(runtime_dir)
        if slice_text:
            out["retro"] = slice_text

    _log.debug(
        "orchestrator.context.built",
        scene=scene,
        requested=needs_slices,
        delivered=list(out.keys()),
    )
    return out


# ---------------- profile slice ----------------


def _build_profile_slice(runtime_dir: Path) -> str | None:
    """读最新版 profile，提取三态前 N 项 + 最近 audit。"""
    profile = _load_latest_profile(runtime_dir)
    if profile is None:
        return None

    meta = profile.get("meta", {})
    confirmed = profile.get("confirmed", {})
    personalized = profile.get("personalized", {})
    to_explore = profile.get("to_explore", {})
    audit = profile.get("audit_log", []) or []

    pillars = [p.get("name") for p in (confirmed.get("content_pillars") or [])][:3]
    traits = [t.get("trait") for t in (personalized.get("persona_traits") or [])][:3]
    life_ctx = [c.get("context") for c in (personalized.get("life_context") or [])][:2]
    open_qs = [
        q.get("question") for q in (to_explore.get("open_questions") or [])
    ][:3]
    hypotheses = [
        f"{h.get('hypothesis')} [{h.get('status')}]"
        for h in (to_explore.get("hypotheses") or [])
    ][:3]

    audit_recent = [
        f"{e.get('source')}: {e.get('change')}" for e in audit[-3:] if isinstance(e, dict)
    ]

    parts: list[str] = []
    parts.append(
        f"## 画像 v{meta.get('version', '?')} (用户 {meta.get('user_id', '?')})"
    )
    if pillars:
        parts.append("**确定项 · content_pillars**：" + " / ".join(pillars))
    if traits:
        parts.append(
            "**个性化项 · persona_traits**：\n- " + "\n- ".join(traits)
        )
    if life_ctx:
        parts.append("**个性化项 · life_context**：" + " / ".join(life_ctx))
    if open_qs:
        parts.append(
            "**待探索项 · open_questions**（不要合并到上面两态）：\n- "
            + "\n- ".join(open_qs)
        )
    if hypotheses:
        parts.append("**待探索项 · hypotheses**：\n- " + "\n- ".join(hypotheses))
    if audit_recent:
        parts.append("最近 audit：\n- " + "\n- ".join(audit_recent))

    text = "\n\n".join(parts)
    return _truncate(text)


# ---------------- strategy slice ----------------


def _build_strategy_slice(runtime_dir: Path) -> str | None:
    """读最新的 strategy_snapshot_*，提取核心字段。"""
    snapshot = _load_latest_by_pattern(runtime_dir, r"^strategy_snapshot_.*\.json$")
    if snapshot is None:
        return None

    idea = snapshot.get("idea", {}) or {}
    heat = snapshot.get("heat_analysis", {}) or {}
    fit = snapshot.get("profile_fit", {}) or {}
    diff = snapshot.get("differentiation", []) or []
    execu = snapshot.get("execution", {}) or {}

    parts: list[str] = []
    parts.append(
        f"## 最近 strategy_snapshot · {snapshot.get('strategy_id', '?')} "
        f"(profile_v{snapshot.get('profile_version', '?')})"
    )
    parts.append(
        f"**主题**：{idea.get('topic', '?')}\n"
        f"**预测主轴**：{idea.get('predicted_pillar', '?')}\n"
        f"**理由**：{idea.get('rationale', '?')}"
    )
    parts.append(
        "**热度（趋势驱动）**：trend_score="
        f"{heat.get('trend_score', '?')} · 方向={heat.get('trend_direction', '?')} · "
        f"评：{heat.get('comment', '?')}"
    )
    parts.append(
        f"**画像契合度（画像驱动）**：fit_score={fit.get('fit_score', '?')}"
    )
    if diff:
        diff_lines = [
            f"- {d.get('point', '?')} [{d.get('source', '?')}]"
            for d in diff[:3]
            if isinstance(d, dict)
        ]
        parts.append("**差异化点**：\n" + "\n".join(diff_lines))
    if execu:
        hook = (execu.get("hook") or {}).get("design", "?")
        parts.append(
            f"**执行**：hook={hook} · pacing={execu.get('pacing', '?')} · "
            f"cta={execu.get('cta', '?')}"
        )
        if execu.get("key_focus"):
            parts.append(f"**重点观察**：{execu.get('key_focus')}")
    text = "\n\n".join(parts)
    return _truncate(text)


# ---------------- retro slice ----------------


def _build_retro_slice(runtime_dir: Path) -> str | None:
    """读最新的 insights_report_*，提取 strategy_review 摘要 + top insights。"""
    report = _load_latest_by_pattern(runtime_dir, r"^insights_report_.*\.json$")
    if report is None:
        return None

    review = report.get("strategy_review", []) or []
    insights = report.get("insights", []) or []
    cards = report.get("data_cards", []) or []

    parts: list[str] = []
    parts.append(
        f"## 最近 insights_report · {report.get('report_id', '?')} "
        f"(video {report.get('video_id', '?')} · strategy {report.get('strategy_id', '?')})"
    )

    if cards:
        card_lines = []
        for c in cards[:4]:
            if not isinstance(c, dict):
                continue
            verdict = c.get("verdict", "?")
            metric = c.get("metric", "?")
            value = c.get("value", "?")
            card_lines.append(f"- {metric}={value} [{verdict}]")
        if card_lines:
            parts.append("**指标卡**：\n" + "\n".join(card_lines))

    if review:
        review_lines = []
        for r in review[:3]:
            if not isinstance(r, dict):
                continue
            review_lines.append(
                f"- 策略意图：{r.get('predicted', '?')[:60]} → 实际：{r.get('actual', '?')[:60]} "
                f"[{r.get('verdict', '?')}]"
            )
        if review_lines:
            parts.append("**Strategy vs Reality**：\n" + "\n".join(review_lines))

    if insights:
        insight_lines = []
        for ins in insights[:3]:
            if not isinstance(ins, dict):
                continue
            claim = ins.get("claim", "?")
            conf = ins.get("confidence", "?")
            insight_lines.append(f"- ({conf}) {claim}")
        if insight_lines:
            parts.append("**Top Insights**：\n" + "\n".join(insight_lines))

    text = "\n\n".join(parts)
    return _truncate(text)


# ---------------- 通用文件加载 ----------------


def _load_latest_profile(runtime_dir: Path) -> dict[str, Any] | None:
    """读 profile_v{n}.json 中 n 最大的一份。"""
    if not runtime_dir.exists():
        return None
    pattern = re.compile(r"^profile_v(\d+)\.json$")
    best_n = -1
    best_path: Path | None = None
    for p in runtime_dir.iterdir():
        m = pattern.match(p.name)
        if not m:
            continue
        n = int(m.group(1))
        if n > best_n:
            best_n = n
            best_path = p
    if best_path is None:
        return None
    try:
        return json.loads(best_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("orchestrator.context.profile_load_fail", path=str(best_path), err=str(e))
        return None


def _load_latest_by_pattern(runtime_dir: Path, regex: str) -> dict[str, Any] | None:
    """读 runtime_dir 下匹配 regex 的最新文件（按 mtime）。"""
    if not runtime_dir.exists():
        return None
    pattern = re.compile(regex)
    candidates = [p for p in runtime_dir.iterdir() if pattern.match(p.name)]
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("orchestrator.context.load_fail", path=str(latest), err=str(e))
        return None


def _truncate(text: str, limit: int = _MAX_SLICE_CHARS) -> str:
    """超长文本截断，末尾加 ``…(已截断)`` 提示。"""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n…(已截断)"
