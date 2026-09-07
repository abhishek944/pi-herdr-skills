#!/usr/bin/env python3
"""Checks durable, one-retry pane-readiness state transitions."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("state-store.py")
SPEC = importlib.util.spec_from_file_location("implement_state_store_readiness", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("FAIL: cannot load state-store.py")
store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(store)


def stamp(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def artifact(run: Path, name: str, payload: dict[str, object]) -> dict[str, str]:
    path = run / "outputs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return {"path": f"outputs/{name}", "digest": hashlib.sha256(path.read_bytes()).hexdigest()}


def require(condition: bool, message: object) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="pane-readiness-state-"))
    feature = "readiness-state"
    run = root / "var" / feature / "implement"
    state_path = run / "state.json"
    created = datetime.now(timezone.utc).replace(microsecond=0)
    deadline = created + timedelta(seconds=30)
    created_text, deadline_text = stamp(created), stamp(deadline)
    capability = "root-capability"
    state = {
        "feature_name": feature,
        "revision": 0,
        "updated_at": created_text,
        "run": {
            "repo_root": str(root),
            "root_task_id": "task-0001",
            "coordinator_lease": {"id": "lease", "expires_at": stamp(created + timedelta(hours=1))},
            "reconciliation_required": False,
            "status": "running",
            "phase": "execute",
            "limits": copy.deepcopy(store.HARD_LIMITS),
        },
        "integration": {"certification": None},
        "tasks": {
            "task-0001": {
                "capability_hash": store.token_hash(capability),
                "allow_subagents": True,
                "updated_at": created_text,
                "runtime_intents": [
                    {
                        "id": "pane-intent",
                        "kind": "pane",
                        "status": "bound",
                        "resource_id": "w1:p2",
                        "created_at": created_text,
                        "target_task_id": "task-0002",
                    },
                    {
                        "id": "agent-intent",
                        "kind": "agent",
                        "status": "planned",
                        "created_at": created_text,
                        "target_task_id": "task-0002",
                    },
                ],
                "runtime_resources": [],
            },
            "task-0002": {"parent_id": "task-0001"},
        },
    }
    original_validate = store.validate
    store.validate = lambda *_args, **_kwargs: None
    try:
        shell = {"pid": 100, "name": "zsh"}
        helper = {"pid": 101, "name": "python"}
        busy_snapshot = artifact(run, "busy-snapshot.json", {
            "id": "cli:pane:process_info",
            "result": {"type": "pane_process_info", "process_info": {"pane_id": "w1:p2", "shell_pid": 100, "foreground_processes": [shell, helper]}},
        })
        busy_class = artifact(run, "busy-class.json", {
            "classification": "busy", "expectedPane": "w1:p2", "paneId": "w1:p2",
            "createdAt": created_text, "deadlineAt": deadline_text, "shellPid": 100,
        })
        busy_start = artifact(run, "busy-start.json", {"error": {"code": "agent_pane_busy"}})
        busy_event = {
            "type": "record-pane-readiness", "intent_id": "agent-intent", "pane_intent_id": "pane-intent",
            "pane_id": "w1:p2", "deadline_at": deadline_text, "classification": "busy",
            "snapshot_artifact": busy_snapshot, "classification_artifact": busy_class,
            "busy_start_artifact": busy_start,
        }
        store.apply_event(state, state_path, "task-0001", capability, "lease", busy_event)
        readiness = state["tasks"]["task-0001"]["runtime_intents"][1]["readiness"]
        require(readiness["busy_start_count"] == 1, readiness)
        duplicate = copy.deepcopy(busy_event)
        try:
            store.apply_event(state, state_path, "task-0001", capability, "lease", duplicate)
        except SystemExit:
            pass
        else:
            raise SystemExit("FAIL: a second agent_pane_busy response was accepted")
        ready_snapshot = artifact(run, "ready-snapshot.json", {
            "id": "cli:pane:process_info",
            "result": {"type": "pane_process_info", "process_info": {"pane_id": "w1:p2", "shell_pid": 100, "foreground_processes": [shell]}},
        })
        ready_class = artifact(run, "ready-class.json", {
            "classification": "ready", "expectedPane": "w1:p2", "paneId": "w1:p2",
            "createdAt": created_text, "deadlineAt": deadline_text, "shellPid": 100,
        })
        store.apply_event(state, state_path, "task-0001", capability, "lease", {
            "type": "record-pane-readiness", "intent_id": "agent-intent", "pane_intent_id": "pane-intent",
            "pane_id": "w1:p2", "deadline_at": deadline_text, "classification": "ready",
            "snapshot_artifact": ready_snapshot, "classification_artifact": ready_class,
        })
        readiness = state["tasks"]["task-0001"]["runtime_intents"][1]["readiness"]
        require(readiness["probes"][-1]["classification"] == "ready", readiness)
    finally:
        store.validate = original_validate
    print("PASS: durable pane readiness state")


if __name__ == "__main__":
    main()
