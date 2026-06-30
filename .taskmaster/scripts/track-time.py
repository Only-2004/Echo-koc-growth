#!/usr/bin/env python3
"""以 UTC 时间戳记录任务开始 / 结束时间。"""
import json, sys, os
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(".taskmaster/state/time-tracking.json")

def load():
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text())
    return {"tasks": {}}

def save(data):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def now_iso():
    return datetime.now(timezone.utc).isoformat()

if len(sys.argv) < 3:
    print("用法：track-time.py start|complete <task_id> [subtask_id]")
    sys.exit(1)

action, task_id = sys.argv[1], sys.argv[2]
subtask_id = sys.argv[3] if len(sys.argv) > 3 else None
data = load()

key = f"{task_id}" + (f".{subtask_id}" if subtask_id else "")

if action == "start":
    data["tasks"][key] = {"started": now_iso(), "status": "in_progress"}
    save(data)
    print(json.dumps({"ok": True, "action": "started", "key": key, "time": now_iso()}, ensure_ascii=False))
elif action == "complete":
    entry = data["tasks"].get(key, {})
    entry["completed"] = now_iso()
    entry["status"] = "done"
    if "started" in entry:
        from datetime import datetime as dt
        start = dt.fromisoformat(entry["started"])
        end = dt.fromisoformat(entry["completed"])
        entry["duration_minutes"] = round((end - start).total_seconds() / 60, 1)
    data["tasks"][key] = entry
    save(data)
    print(json.dumps({"ok": True, "action": "completed", "key": key, "duration": entry.get("duration_minutes")}, ensure_ascii=False))
else:
    print(json.dumps({"ok": False, "error": f"未知操作：{action}"}, ensure_ascii=False))
    sys.exit(1)
