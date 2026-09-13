#!/usr/bin/env python3
"""Atomic single-file state store for recursive implement runs."""

from __future__ import annotations

import argparse
import copy
import difflib
import fcntl
import hashlib
import json
import os
import posixpath
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TASK_ID_RE = re.compile(r"task-(\d{4,})$")
TODO_ID_RE = re.compile(r"todo-(\d{4,})$")
TASK_STATUSES = {
    "planning",
    "queued",
    "launching",
    "working",
    "waiting",
    "integrating",
    "cancelling",
    "done",
    "blocked",
    "cancelled",
}
TODO_STATUSES = {"pending", "working", "done", "blocked", "cancelled"}
RUN_STATUSES = {"running", "blocked", "complete", "cancelled"}
RUN_PHASES = {
    "bootstrap",
    "plan",
    "execute",
    "integrate",
    "review",
    "complete",
    "blocked",
}
TASK_CLASSES = {
    "coordination",
    "architecture",
    "implementation",
    "exploration",
    "focused-edit",
    "multimodal",
    "review",
    "integration",
}
PI_THINKING_ORDER = ("off", "minimal", "low", "medium", "high", "xhigh", "max")
PI_THINKING_LEVELS = set(PI_THINKING_ORDER)
PI_THINKING_RANK = {value: index for index, value in enumerate(PI_THINKING_ORDER)}
CATALOG_THINKING_LEVELS = PI_THINKING_LEVELS
CATALOG_INPUT_TYPES = {"text", "image", "video", "audio", "pdf"}
REVIEW_TIER_RANK = {"basic": 1, "standard": 2, "strong": 3, "expert": 4}
REVIEW_TIERS = set(REVIEW_TIER_RANK)
REVIEW_COMPLEXITIES = {"simple", "complicated"}
RESOURCE_STATUSES = {"live", "closed", "preserved"}
READINESS_OVERFLOW_REASON = "derived deadline exceeds the supported timestamp range"
PANE_READINESS_TIMEOUT = timedelta(seconds=300)
MAX_UTC_TIMESTAMP = datetime.max.replace(tzinfo=timezone.utc)
RUNTIME_STATUSES = {
    "not-started",
    "reserved",
    "starting",
    "working",
    "blocked",
    "settled",
    "stopped",
    "cancellation-requested",
    "cancelled",
}
RUNTIME_TRANSITIONS = {
    "not-started": {"reserved", "stopped", "cancelled"},
    "reserved": {"starting", "stopped", "cancellation-requested"},
    "starting": {"working", "blocked", "stopped", "cancellation-requested"},
    "working": {"blocked", "settled", "stopped", "cancellation-requested"},
    "blocked": {"working", "stopped", "cancellation-requested"},
    "cancellation-requested": {"stopped", "cancelled"},
    "settled": {"cancelled"},
    "stopped": {"cancelled"},
    "cancelled": set(),
}
SETTLED = {"done", "cancelled"}
HARD_LIMITS = {
    "max_depth": 2,
    "max_children_per_task": 6,
    "max_total_tasks": 18,
    "max_active_agents": 6,
}
GLOBAL_MODEL_CATALOG = (
    Path.home() / ".pi" / "agent" / "skills" / "model-routing-policy" / "models.json"
)
TASK_PHASES = {
    "planning": "plan",
    "queued": "plan",
    "launching": "launch",
    "working": "work",
    "waiting": "wait-for-children",
    "integrating": "integrate-subtree",
    "cancelling": "cancel",
    "done": "done",
    "blocked": "blocked",
    "cancelled": "cancelled",
}
TASK_TRANSITIONS = {
    "planning": {"queued", "launching", "working", "blocked", "cancelling"},
    "queued": {"launching", "blocked", "cancelling"},
    "launching": {"working", "blocked", "cancelling"},
    "working": {"waiting", "integrating", "done", "blocked", "cancelling"},
    "waiting": {"working", "integrating", "blocked", "cancelling"},
    "integrating": {"working", "done", "blocked", "cancelling"},
    "blocked": {"planning", "queued", "launching", "working", "cancelling"},
    "cancelling": {"cancelled", "blocked"},
    "done": set(),
    "cancelled": set(),
}
RUN_TRANSITIONS = {
    "bootstrap": {"plan", "blocked"},
    "plan": {"execute", "blocked"},
    "execute": {"integrate", "blocked"},
    "integrate": {"review", "execute", "blocked"},
    "review": {"integrate", "complete", "blocked"},
    "blocked": {"plan", "execute", "integrate", "review"},
    "complete": set(),
}
SUPPORTED_EVENT_TYPES = (
    "set-run", "set-run-phase", "finish-reconciliation", "update-contract",
    "replan-child", "add-todo", "set-todo", "add-child", "record-model",
    "reserve-slot", "record-runtime",
    "record-launch-verification", "record-productive-prompt",
    "record-usable-contribution", "release-slot", "fail-launch",
    "prepare-fallback", "add-runtime-intent", "record-pane-readiness",
    "bind-runtime-intent", "fail-runtime-intent", "settle-runtime-resource",
    "record-result", "accept-task", "set-task-status", "cancel-subtree",
    "finalize-cancellation", "cancel-run", "update-integration", "complete-run",
)
DEPRECATED_EVENT_TYPES = {
    "add-runtime-resource": "record and bind a runtime intent instead",
}


def event_catalog() -> dict[str, Any]:
    return {
        "mutation": "none",
        "event_types": list(SUPPORTED_EVENT_TYPES),
        "deprecated_event_types": DEPRECATED_EVENT_TYPES,
        "root_bootstrap_sequence": [
            {"type": "set-run", "event": {"type": "set-run", "updates": {"user_goal": "<requested outcome>"}}},
            {"type": "update-contract", "event": {"type": "update-contract", "updates": {"title": "<title>", "outcome": "<one outcome>", "acceptance_criteria": ["<criterion>"], "boundaries": ["<boundary>"], "inputs": ["<input>"], "expected_result": "<result>"}}},
            {"type": "add-todo", "event": {"type": "add-todo", "title": "<todo>", "acceptance": "<evidence required>"}},
            {"type": "set-run-phase", "event": {"type": "set-run-phase", "phase": "plan"}},
            {"type": "set-task-status", "event": {"type": "set-task-status", "status": "working"}},
            {"type": "set-run-phase", "event": {"type": "set-run-phase", "phase": "execute"}},
        ],
    }


def strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"JSON contains duplicate key: {key}")
        value[key] = item
    return value


def current_coordinator_model(instance_id: str) -> dict[str, str]:
    value = {
        "instance_id": instance_id,
        "provider": os.environ.get("PI_PROVIDER", ""),
        "model_id": os.environ.get("PI_MODEL", ""),
        "thinking_level": os.environ.get("PI_REASONING_LEVEL", ""),
    }
    if (
        any(
            not nonempty(value[key])
            for key in ("instance_id", "provider", "model_id", "thinking_level")
        )
        or value["thinking_level"] not in PI_THINKING_LEVELS
    ):
        fail("coordinator model provenance is unavailable")
    return value


def now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def future(minutes: int = 180) -> str:
    return (
        (datetime.now(timezone.utc) + timedelta(minutes=minutes))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_time(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        fail(f"{label} must be an ISO timestamp")
    if parsed.tzinfo is None:
        fail(f"{label} must include a timezone")
    return parsed


def valid_readiness_deadline(created_at: datetime, deadline_at: datetime) -> bool:
    """Return whether a persisted pane-readiness deadline is safely anchored."""
    overflow_sentinel = created_at == deadline_at == MAX_UTC_TIMESTAMP
    return (
        deadline_at >= created_at
        and deadline_at - created_at <= PANE_READINESS_TIMEOUT
        and (deadline_at != created_at or overflow_sentinel)
    )


def validate_readiness_probe_evidence(
    snapshot: Any,
    classification_payload: Any,
    classification: str,
    pane_id: str,
    created_at: str,
    deadline_at: str,
    allow_legacy_observation: bool = False,
) -> None:
    if not isinstance(classification_payload, dict) or any(
        classification_payload.get(key) != value
        for key, value in {
            "classification": classification,
            "expectedPane": pane_id,
            "createdAt": created_at,
            "deadlineAt": deadline_at,
        }.items()
    ):
        fail("pane readiness classification artifact does not bind its recorded identity")
    if classification == "ambiguous":
        return
    observed_value = classification_payload.get("observedAt")
    if observed_value is None and allow_legacy_observation:
        observed_value = created_at
    observed_at = parse_time(observed_value, "pane readiness observedAt")
    created_time = parse_time(created_at, "pane readiness createdAt")
    deadline_time = parse_time(deadline_at, "pane readiness deadlineAt")
    if observed_at < created_time:
        fail("pane readiness observation predates pane creation")
    if classification in {"ready", "busy"} and observed_at >= deadline_time:
        fail("non-terminal pane readiness classification was observed after its deadline")
    if classification == "expired" and observed_at < deadline_time:
        fail("expired pane readiness classification was observed before its deadline")
    if not isinstance(snapshot, dict) or snapshot.get("id") != "cli:pane:process_info":
        fail("pane readiness snapshot has an invalid Herdr response ID")
    result = snapshot.get("result")
    if not isinstance(result, dict) or result.get("type") != "pane_process_info":
        fail("pane readiness snapshot has an invalid Herdr response type")
    process_info = result.get("process_info")
    if not isinstance(process_info, dict) or process_info.get("pane_id") != pane_id:
        fail("pane readiness snapshot belongs to a different pane")
    shell_pid = process_info.get("shell_pid")
    processes = process_info.get("foreground_processes")
    if type(shell_pid) is not int or shell_pid <= 0 or not isinstance(processes, list) or not processes:
        fail("pane readiness snapshot has invalid shell or process data")
    if any(
        not isinstance(item, dict) or type(item.get("pid")) is not int or item["pid"] <= 0
        for item in processes
    ):
        fail("pane readiness snapshot has an invalid process PID")
    pids = [item["pid"] for item in processes]
    if len(set(pids)) != len(pids) or pids.count(shell_pid) != 1:
        fail("pane readiness snapshot has duplicate PIDs or does not contain its shell exactly once")
    extras = [str(item.get("name") or "unknown") for item in processes if item["pid"] != shell_pid]
    expected = {
        "classification": classification,
        "expectedPane": pane_id,
        "createdAt": created_at,
        "deadlineAt": deadline_at,
        "paneId": pane_id,
        "shellPid": shell_pid,
    }
    if classification == "ready":
        expected["reason"] = "the interactive shell is the sole foreground process"
        if extras:
            fail("a ready pane snapshot still contains foreground helpers")
    elif classification == "busy":
        expected.update({
            "reason": "the shell has additional foreground work",
            "extraProcessCount": len(extras),
            "extraProcessNames": extras,
        })
        if not extras:
            fail("a busy pane snapshot contains only the shell")
    elif classification == "expired":
        expected["reason"] = "the original pane-readiness deadline has elapsed"
    if classification_payload.get("observedAt") is not None:
        expected["observedAt"] = classification_payload["observedAt"]
    elif not allow_legacy_observation:
        fail("pane readiness classification lacks its observation time")
    if classification_payload != expected:
        fail("pane readiness classification does not match the complete process snapshot")


def validate_readiness_probe_transition(previous_snapshot: Any, current_snapshot: Any) -> None:
    previous = previous_snapshot["result"]["process_info"]
    current = current_snapshot["result"]["process_info"]
    if previous["pane_id"] != current["pane_id"] or previous["shell_pid"] != current["shell_pid"]:
        fail("pane or shell identity changed between readiness probes")


def failed_attempt_resources(tasks: dict[str, Any], target: str, attempt: int) -> list[dict[str, Any]]:
    target_intent_ids = {
        intent.get("id")
        for owner in tasks.values()
        for intent in owner.get("runtime_intents", [])
        if intent.get("target_task_id") == target and intent.get("attempt", 1) == attempt
    }
    resources = [
        resource
        for owner in tasks.values()
        for resource in owner.get("runtime_resources", [])
        if resource.get("intent_id") in target_intent_ids
    ]
    parent_tab_ids = {
        resource.get("parent_tab_id")
        for resource in resources
        if nonempty(resource.get("parent_tab_id"))
    }
    for parent_tab_id in parent_tab_ids:
        has_live_peer = any(
            resource.get("parent_tab_id") == parent_tab_id
            and resource.get("intent_id") not in target_intent_ids
            and resource.get("status") == "live"
            for owner in tasks.values()
            for resource in owner.get("runtime_resources", [])
        )
        if not has_live_peer:
            parent_tab = next(
                (
                    resource
                    for owner in tasks.values()
                    for resource in owner.get("runtime_resources", [])
                    if resource.get("kind") == "tab" and resource.get("id") == parent_tab_id
                ),
                None,
            )
            if parent_tab is not None:
                resources.append(parent_tab)
    return resources


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worktree_snapshot(repo_root: Path, base_commit: str) -> dict[str, str]:
    try:
        changed = subprocess.check_output(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--name-only",
                "-z",
                base_commit,
                "--",
            ]
        )
        untracked = subprocess.check_output(
            [
                "git",
                "-C",
                str(repo_root),
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
            ]
        )
    except subprocess.CalledProcessError as error:
        fail(f"could not snapshot the worktree: {error}")
    paths = {
        item.decode("utf-8", "surrogateescape")
        for item in (changed + untracked).split(b"\0")
        if item
    }
    snapshot: dict[str, str] = {}
    for relative in sorted(paths):
        candidate = repo_root / relative
        if candidate.is_symlink():
            snapshot[relative] = (
                f"{candidate.lstat().st_mode:o}:symlink:" + os.readlink(candidate)
            )
        elif candidate.is_file():
            snapshot[relative] = f"{candidate.stat().st_mode:o}:" + file_digest(
                candidate
            )
        else:
            snapshot[relative] = "<deleted>"
    return snapshot


def run_owned_files(state: dict[str, Any]) -> list[str]:
    repo_root = Path(state["run"]["repo_root"])
    current = worktree_snapshot(repo_root, state["run"]["base_commit"])
    baseline = state["run"].get("initial_worktree") or {}
    return sorted(
        path
        for path in set(current) | set(baseline)
        if current.get(path) != baseline.get(path)
    )


def state_directory(state: dict[str, Any]) -> Path:
    return Path(state["run"]["repo_root"]) / "var" / state["feature_name"] / "implement"


def verify_task_output(state: dict[str, Any], runtime: dict[str, Any]) -> None:
    relative = runtime.get("output_path")
    digest = runtime.get("output_digest")
    if (
        not nonempty(relative)
        or not relative.startswith("outputs/")
        or not valid_hash(digest)
    ):
        fail("settled task requires a recorded output path and digest")
    root = state_directory(state).resolve()
    candidate = root / relative
    if (
        candidate.is_symlink()
        or candidate.resolve().parent != (root / "outputs").resolve()
        and not str(candidate.resolve()).startswith(
            str((root / "outputs").resolve()) + os.sep
        )
    ):
        fail("task output must remain in the run outputs folder")
    if not candidate.is_file() or file_digest(candidate) != digest:
        fail("task output is missing or stale")


def review_report_file(state: dict[str, Any], relative: Any, label: str) -> Path:
    if not nonempty(relative):
        fail(f"{label} path is required")
    repo_root = Path(state["run"]["repo_root"]).resolve()
    feature_root = repo_root / "var" / state["feature_name"]
    root = feature_root / "reviews"
    candidate = repo_root / relative
    try:
        root.relative_to(repo_root)
        candidate.relative_to(repo_root)
    except ValueError:
        fail(f"{label} must stay in the run reviews folder")
    for path in (repo_root / "var", feature_root, root):
        if path.is_symlink():
            fail(f"{label} review folder cannot contain symbolic links")
    current = repo_root
    for part in candidate.relative_to(repo_root).parts:
        current = current / part
        if current.is_symlink():
            fail(f"{label} path cannot contain symbolic links")
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        fail(f"{label} must stay in the run reviews folder")
    if not candidate.is_file() or candidate.stat().st_size == 0:
        fail(f"{label} is missing or empty")
    return candidate


def report_value(text: str, label: str) -> str | None:
    matches = re.findall(
        rf"(?im)^\s*{re.escape(label)}:\s*(.*?)\s*$", text
    )
    return matches[-1].strip() if matches else None


def report_footer(text: str, label: str) -> dict[str, str]:
    pattern = re.compile(
        r"(?ms)^\s*Reviewer instance:\s*(.*?)\n"
        r"\s*Model:\s*([^\n]+)\n"
        r"\s*Thinking:\s*([^\n]+)\n"
        r"\s*Finding IDs:\s*([^\n]+)\n"
        r"\s*Verdict:\s*([^\n]+)$"
    )
    matches = list(pattern.finditer(text))
    if not matches:
        fail(f"{label} must end its response with the complete review footer")
    match = matches[-1]
    for line in text[match.end() :].splitlines():
        stripped = line.strip()
        if (
            not stripped
            or set(stripped) == {"─"}
            or stripped.startswith(("~", "↑", "⌥"))
        ):
            continue
        fail(f"{label} contains response text after its final footer")
    return {
        "reviewer_instance": "".join(
            part.strip() for part in match.group(1).splitlines()
        ),
        "model": match.group(2).strip(),
        "thinking": match.group(3).strip(),
        "finding_ids": match.group(4).strip(),
        "verdict": match.group(5).strip(),
    }


def summary_footer(text: str) -> dict[str, str]:
    pattern = re.compile(
        r"(?m)^Finding IDs:\s*([^\n]+)\nVerdict:\s*([^\n]+)$"
    )
    matches = list(pattern.finditer(text))
    if not matches:
        fail("review summary must end with Finding IDs and Verdict lines")
    match = matches[-1]
    if text[match.end() :].strip():
        fail("review summary contains text after its final footer")
    return {
        "finding_ids": match.group(1).strip(),
        "verdict": match.group(2).strip(),
    }


def report_finding_ids(raw: str, label: str) -> set[str]:
    if not nonempty(raw):
        fail(f"{label} must include a Finding IDs line")
    if raw.strip().lower() in {"none", "clean", "n/a"}:
        return set()
    finding_ids = {item.strip() for item in raw.split(",") if item.strip()}
    if not finding_ids:
        fail(f"{label} has an invalid Finding IDs line")
    return finding_ids


def invalidate_review(integration: dict[str, Any]) -> None:
    wave = integration.get("review_wave", 0)
    if isinstance(wave, int) and not isinstance(wave, bool) and wave > 0:
        integration["minimum_review_wave"] = max(
            integration.get("minimum_review_wave", 0), wave + 1
        )
    integration.update(
        {
            "review_verdict": "pending",
            "review_execution": None,
            "review_perspectives": {},
            "combined_report_path": None,
        }
    )


def validate_review_resource_update(
    previous_items: Any, supplied_items: Any, *, cleanup_only: bool
) -> None:
    if not isinstance(previous_items, list) or not isinstance(supplied_items, list):
        fail("review resources must be lists")
    previous = {
        item.get("id"): item
        for item in previous_items
        if isinstance(item, dict) and nonempty(item.get("id"))
    }
    supplied = {
        item.get("id"): item
        for item in supplied_items
        if isinstance(item, dict) and nonempty(item.get("id"))
    }
    if len(supplied) != len(supplied_items) or not set(previous).issubset(supplied):
        fail("review resource updates cannot remove or duplicate recorded tabs")
    if cleanup_only and set(supplied) != set(previous):
        fail("review recovery cannot add new tab records")
    for resource_id, item in supplied.items():
        if item.get("kind") != "tab" or item.get("status") not in {"open", "closed"}:
            fail("review resources require tab kind and open or closed status")
        prior = previous.get(resource_id)
        if prior is None and item.get("status") != "open":
            fail("new review tabs must be recorded open before closure")
        if prior is not None and prior.get("status") == "closed" and item.get("status") != "closed":
            fail("closed review tabs cannot be reopened")


def sibling_file_overlaps(state: dict[str, Any]) -> list[tuple[str, str, str]]:
    owners: dict[tuple[str, str], list[str]] = {}
    root_id = state["run"]["root_task_id"]
    for task_id, task in state["tasks"].items():
        if task_id == root_id or task.get("status") not in {"done", "cancelled"}:
            continue
        parent_id = task.get("parent_id")
        for relative in task.get("result", {}).get("files_changed", []):
            owners.setdefault((parent_id, relative), []).append(task_id)
    overlaps: list[tuple[str, str, str]] = []
    for (_, relative), task_ids in owners.items():
        for left_index, left in enumerate(sorted(set(task_ids))):
            for right in sorted(set(task_ids))[left_index + 1 :]:
                overlaps.append((left, right, relative))
    return overlaps


def readable_evidence_path(state: dict[str, Any], value: str) -> bool:
    requested = Path(value)
    repo_root = Path(state["run"]["repo_root"]).resolve()
    candidates = (
        [requested]
        if requested.is_absolute()
        else [state_directory(state) / requested, repo_root / requested]
    )
    for candidate in candidates:
        try:
            candidate.resolve().relative_to(repo_root)
        except ValueError:
            continue
        if (
            candidate.is_file()
            and not candidate.is_symlink()
            and candidate.stat().st_size > 0
        ):
            return True
    return False


def require_readable_evidence(
    state: dict[str, Any], entries: Any, label: str
) -> None:
    if not isinstance(entries, list) or not entries:
        fail(f"{label} requires readable evidence")
    description_fields = {"description", "evidence", "handoff", "result", "summary"}
    path_prefixes = ("./", "../", "/", "evidence/", "outputs/", "var/")
    for item in entries:
        if nonempty(item):
            no_whitespace = not any(character.isspace() for character in item)
            looks_like_path = item.startswith(path_prefixes) or (
                no_whitespace
                and (bool(Path(item).suffix) or "/" in item or "\\" in item)
            )
            if not looks_like_path or readable_evidence_path(state, item):
                continue
            fail(f"{label} references a missing or empty evidence file")
        if not isinstance(item, dict):
            fail(f"{label} contains an unreadable evidence entry")
        declared_references = [
            item[key] for key in ("artifact", "path") if key in item
        ]
        if declared_references:
            if all(
                nonempty(value) and readable_evidence_path(state, value)
                for value in declared_references
            ):
                continue
            fail(f"{label} references a missing or empty evidence file")
        if any(
            key in description_fields and nonempty(value)
            for key, value in item.items()
        ):
            continue
        fail(f"{label} contains an unreadable evidence entry")


def validate_integration_ready(state: dict[str, Any]) -> None:
    integration = state["integration"]
    test_verdict = integration.get("test_verdict")
    if test_verdict not in {"pass", "skipped"}:
        fail("checks must pass or have a documented skip")
    if test_verdict == "pass":
        require_readable_evidence(
            state, integration.get("test_evidence"), "passing checks"
        )
    if test_verdict == "skipped" and not nonempty(integration.get("skipped_reason")):
        fail("skipped checks require a reason")
    behavior_verdict = integration.get("behavior_verdict")
    if behavior_verdict not in {"pass", "user-pending", "not-applicable"}:
        fail("behavior verification must be settled")
    if behavior_verdict == "pass":
        require_readable_evidence(
            state,
            integration.get("behavior_evidence"),
            "passing behavior verification",
        )
    if behavior_verdict == "user-pending":
        if not nonempty(integration.get("behavior_reason")):
            fail("user-pending behavior requires a reason and readable handoff")
        require_readable_evidence(
            state,
            integration.get("behavior_evidence"),
            "user-pending behavior handoff",
        )
    if behavior_verdict == "not-applicable":
        if (
            not nonempty(integration.get("behavior_reason"))
            or not isinstance(integration.get("behavior_eligibility"), dict)
        ):
            fail("inapplicable behavior verification requires documented eligibility")
        allowed_extensions = {".md", ".rst", ".txt"}
        if not integration.get("changed_files") or any(
            Path(item).suffix.lower() not in allowed_extensions
            for item in integration["changed_files"]
        ):
            fail(
                "inapplicable behavior verification is limited to documentation-only changes"
            )

    changed_files = sorted(integration.get("changed_files", []))
    if run_owned_files(state) != changed_files:
        fail("integration changed files do not match the live run-owned worktree delta")
    root_id = state["run"]["root_task_id"]
    root_files = sorted(state["tasks"][root_id].get("result", {}).get("files_changed", []))
    if root_files != changed_files:
        fail("root result files do not match the integrated changed files")

    collisions = integration.get("collisions", [])
    if any(item.get("status") != "resolved" for item in collisions):
        fail("integration collisions remain unresolved")
    for left, right, relative in sibling_file_overlaps(state):
        if not any(
            {left, right}.issubset(set(item.get("tasks", [])))
            and relative in item.get("files", [])
            for item in collisions
        ):
            fail(
                f"sibling file collision is not recorded: {left}, {right}, {relative}"
            )

    if any(
        item.get("status") == "open"
        for item in integration.get("review_findings", [])
    ):
        fail("review findings remain open")
    if any(
        item.get("status") != "closed"
        for item in integration.get("review_resources", [])
    ):
        fail("review resources remain open")

    requirement = integration.get("review_requirement") or {}
    execution = integration.get("review_execution")
    if requirement.get("required") is False:
        if (
            requirement.get("classification") != "simple"
            or requirement.get("source") != "automatic"
            or execution != "not-required"
            or integration.get("review_verdict") != "not-required"
            or integration.get("review_perspectives")
            or integration.get("combined_report_path")
        ):
            fail("a skipped review must be an evidenced automatic simple change")
        return

    if (
        requirement.get("required") is not True
        or execution != "independent"
        or integration.get("review_verdict") != "pass"
    ):
        fail("required independent review is incomplete")
    wave = integration.get("review_wave")
    if isinstance(wave, bool) or not isinstance(wave, int) or wave < 1:
        fail("independent review requires a positive wave number")
    minimum_wave = integration.get("minimum_review_wave", 0)
    if wave < minimum_wave:
        fail("independent review must use a fresh wave after rework")
    expected = {
        "correctness_safety": f"var/{state['feature_name']}/reviews/wave-{wave}-correctness.md",
        "architecture_integration": f"var/{state['feature_name']}/reviews/wave-{wave}-architecture.md",
        "regression_fix_quality": f"var/{state['feature_name']}/reviews/wave-{wave}-regression.md",
    }
    perspectives = integration.get("review_perspectives") or {}
    if set(perspectives) != set(expected):
        fail("independent review requires correctness, architecture, and regression reports")

    forbidden_instances = {
        value
        for value in [
            state["run"].get("coordinator_instance_id"),
            *state["run"].get("coordinator_instance_history", []),
        ]
        if nonempty(value)
    }
    for task in state["tasks"].values():
        runtime = task.get("runtime") or {}
        if nonempty(runtime.get("agent_instance_id")):
            forbidden_instances.add(runtime["agent_instance_id"])
        for attempt in task.get("runtime_history", []):
            historical = attempt.get("runtime") or {}
            if nonempty(historical.get("agent_instance_id")):
                forbidden_instances.add(historical["agent_instance_id"])
    review_root = (
        Path(state["run"]["repo_root"])
        / "var"
        / state["feature_name"]
        / "reviews"
    )
    legacy_review_root = state_directory(state) / "reviews"
    available_waves = []
    for root in (review_root, legacy_review_root):
        for prior in root.glob("wave-*-*.md"):
            match = re.match(r"wave-(\d+)-", prior.name)
            if match:
                available_waves.append(int(match.group(1)))
            if f"wave-{wave}-" in prior.name:
                continue
            try:
                prior_footer = report_footer(
                    prior.read_text(encoding="utf-8"), "prior review report"
                )
            except SystemExit:
                continue
            forbidden_instances.add(prior_footer["reviewer_instance"])
    if available_waves and wave != max(available_waves):
        fail("independent review must use the newest readable wave")
    for legacy_wave in integration.get("review_waves", []):
        if isinstance(legacy_wave, dict) and legacy_wave.get("wave") != wave:
            forbidden_instances.update(
                item
                for item in legacy_wave.get("reviewer_instance_ids", [])
                if nonempty(item)
            )

    findings = {
        item["id"]: item
        for item in integration.get("review_findings", [])
        if isinstance(item, dict) and nonempty(item.get("id"))
    }
    reviewer_instances = []
    for name, relative in expected.items():
        item = perspectives[name]
        if item.get("status") != "complete" or item.get("output_path") != relative:
            fail(f"{name} review is incomplete")
        for field in (
            "agent_id",
            "agent_instance_id",
            "provider",
            "model_id",
            "thinking_level",
        ):
            if not nonempty(item.get(field)):
                fail(f"{name} review is missing {field}")
        reviewer_instances.append(item["agent_instance_id"])
        text = review_report_file(state, relative, f"{name} report").read_text(
            encoding="utf-8"
        )
        footer = report_footer(text, f"{name} report")
        if footer["reviewer_instance"] != item["agent_instance_id"]:
            fail(f"{name} report reviewer identity does not match integration state")
        if footer["model"] != f"{item['provider']}/{item['model_id']}":
            fail(f"{name} report model does not match integration state")
        if footer["thinking"] != item["thinking_level"]:
            fail(f"{name} report thinking does not match integration state")
        if footer["verdict"].lower() not in {"clean", "pass"}:
            fail(f"{name} report is not clean")
        for finding_id in report_finding_ids(
            footer["finding_ids"], f"{name} report"
        ):
            finding = findings.get(finding_id)
            if finding is None or finding.get("status") == "open":
                fail(f"{name} report finding {finding_id} is not closed in integration state")
    if len(set(reviewer_instances)) != 3:
        fail("independent reviewers must use three distinct Pi sessions")
    if any(instance in forbidden_instances for instance in reviewer_instances):
        fail("final reviewers must be fresh and independent from coordinators and contributors")

    summary = f"var/{state['feature_name']}/reviews/wave-{wave}-summary.md"
    if integration.get("combined_report_path") != summary:
        fail("review summary path does not match the current wave")
    summary_text = review_report_file(state, summary, "review summary").read_text(
        encoding="utf-8"
    )
    footer = summary_footer(summary_text)
    if footer["verdict"].lower() not in {"clean", "pass"}:
        fail("review summary is not clean")
    for finding_id in report_finding_ids(
        footer["finding_ids"], "review summary"
    ):
        finding = findings.get(finding_id)
        if finding is None or finding.get("status") == "open":
            fail(f"review summary finding {finding_id} is not closed")


def valid_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any, label: str, *, nonempty_list: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty_list and not value):
        fail(f"{label} must be {'a non-empty' if nonempty_list else 'a'} list")
    if any(not nonempty(item) for item in value):
        fail(f"{label} must contain only non-empty strings")
    return value


def validate_repo_files(value: Any, label: str) -> list[str]:
    files = string_list(value, label)
    normalized = []
    for item in files:
        candidate = posixpath.normpath(item.replace("\\", "/"))
        if (
            candidate in {".", ".."}
            or candidate.startswith("/")
            or candidate.startswith("../")
        ):
            fail(f"{label} contains a path outside the repository: {item}")
        normalized.append(candidate)
    if len(normalized) != len(set(normalized)):
        fail(f"{label} contains duplicate paths")
    return normalized


def normalize_output_path(state: dict[str, Any], value: Any, label: str) -> str:
    if not nonempty(value):
        fail(f"{label} is required")
    normalized = posixpath.normpath(value.replace("\\", "/"))
    if (
        not normalized.startswith("outputs/")
        or normalized in {"outputs", "outputs/."}
        or normalized.startswith("../")
    ):
        fail(f"{label} must remain inside the run outputs folder")
    root = state_directory(state).resolve() if "run" in state else None
    if root is not None:
        lexical = root / normalized
        current = root
        for part in Path(normalized).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                fail(f"{label} cannot contain symbolic links")
        try:
            lexical.resolve().relative_to((root / "outputs").resolve())
        except ValueError:
            fail(f"{label} escapes the run outputs folder")
    return normalized


def selection_thinking_level(selection: dict[str, Any]) -> str | None:
    return selection.get("thinking_level")


def validate_model_selection(
    selection: Any, task_class: str, *, require_thinking: bool = False
) -> dict[str, Any]:
    required_fields = {
        "provider",
        "model_id",
        "task_class",
        "input_types",
        "thinking_level",
        "reason",
        "availability_evidence",
        "caller",
    }
    if task_class == "review":
        required_fields.add("reviewer_escalation")
    if not isinstance(selection, dict) or set(selection) != required_fields:
        fail("model selection must use exactly the canonical fields")
    for key in (
        "provider",
        "model_id",
        "task_class",
        "reason",
        "availability_evidence",
    ):
        if not nonempty(selection.get(key)):
            fail(f"model selection requires {key}")
    if selection["task_class"] != task_class:
        fail("model selection task_class does not match the task contract")
    thinking_level = selection_thinking_level(selection)
    if require_thinking and not nonempty(selection.get("thinking_level")):
        fail("versioned-catalog model selection requires thinking_level")
    if thinking_level is not None and thinking_level not in PI_THINKING_LEVELS:
        fail("model selection thinking level is unsupported by Pi")
    if require_thinking:
        string_list(
            selection.get("input_types"),
            "versioned-catalog model selection input_types",
            nonempty_list=True,
        )
        caller = selection.get("caller")
        if (
            not isinstance(caller, dict)
            or set(caller) != {"provider", "model_id", "thinking_level"}
            or any(
                not nonempty(caller.get(key))
                for key in ("provider", "model_id", "thinking_level")
            )
            or caller.get("thinking_level") not in PI_THINKING_LEVELS
        ):
            fail(
                "versioned-catalog model selection requires canonical caller provider/model/thinking provenance"
            )
        escalation = selection.get("reviewer_escalation")
        if task_class == "review":
            if (
                not isinstance(escalation, dict)
                or set(escalation) != {"status", "rule", "baselines"}
                or (escalation.get("status"), escalation.get("rule"))
                not in {
                    (
                        "stronger",
                        "no-regression-in-model-or-thinking-and-at-least-one-strict",
                    ),
                    ("peer", "simple-review-fresh-peer"),
                }
            ):
                fail("review model selection uses unsupported reviewer escalation")
            baselines = escalation.get("baselines")
            if (
                not isinstance(baselines, list)
                or not baselines
                or any(
                    not isinstance(item, dict)
                    or set(item) != {"provider", "model_id", "thinking_level"}
                    or any(
                        not nonempty(item.get(key))
                        for key in ("provider", "model_id", "thinking_level")
                    )
                    or item.get("thinking_level") not in PI_THINKING_LEVELS
                    for item in baselines
                )
            ):
                fail(
                    "review model selection requires catalogued caller/contributor baselines"
                )
            if not any(
                all(
                    item.get(key) == caller.get(key)
                    for key in ("provider", "model_id", "thinking_level")
                )
                for item in baselines
            ):
                fail("review escalation baselines must include the recorded caller")
    return selection


def validate_versioned_catalog(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != {
        "schemaVersion",
        "catalogVersion",
        "models",
    }:
        fail("model catalog must use exactly schemaVersion, catalogVersion, and models")
    schema_version = data.get("schemaVersion")
    catalog_version = data.get("catalogVersion")
    models = data.get("models")
    if schema_version != 1:
        fail("model catalog schemaVersion must be 1")
    if (
        not nonempty(catalog_version)
        or re.fullmatch(r"\d{4}-\d{2}-\d{2}", catalog_version) is None
    ):
        fail("model catalog catalogVersion must use YYYY-MM-DD")
    if not isinstance(models, list) or not models:
        fail("model catalog models must be a non-empty list")
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(models):
        label = f"model catalog models[{index}]"
        model_keys = {
            "provider",
            "modelId",
            "family",
            "independenceGroup",
            "capabilities",
            "thinking",
            "routing",
        }
        if (
            not isinstance(item, dict)
            or set(item) != model_keys
            or any(
                not nonempty(item.get(key))
                for key in ("provider", "modelId", "family", "independenceGroup")
            )
        ):
            fail(f"{label} must use exactly the canonical model fields")
        reference = (item["provider"], item["modelId"])
        if reference in seen:
            fail("model catalog contains duplicate provider/model entries")
        seen.add(reference)
        capabilities = item.get("capabilities")
        if not isinstance(capabilities, dict) or set(capabilities) != {
            "inputTypes",
            "taskClasses",
            "taskClassScores",
        }:
            fail(f"{label}.capabilities must use exactly the canonical fields")
        inputs = string_list(
            capabilities.get("inputTypes"),
            f"{label}.capabilities.inputTypes",
            nonempty_list=True,
        )
        classes = string_list(
            capabilities.get("taskClasses"),
            f"{label}.capabilities.taskClasses",
            nonempty_list=True,
        )
        if len(inputs) != len(set(inputs)) or any(
            value not in CATALOG_INPUT_TYPES for value in inputs
        ):
            fail(
                f"{label}.capabilities.inputTypes contains duplicates or unsupported inputs"
            )
        if len(classes) != len(set(classes)) or any(
            value not in TASK_CLASSES for value in classes
        ):
            fail(
                f"{label}.capabilities.taskClasses contains duplicates or unsupported task classes"
            )
        scores = capabilities.get("taskClassScores")
        if (
            not isinstance(scores, dict)
            or set(scores) != set(classes)
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= 5
                for value in scores.values()
            )
        ):
            fail(
                f"{label}.capabilities.taskClassScores must rank every declared task class from 1 to 5"
            )
        thinking = item.get("thinking")
        if not isinstance(thinking, dict) or set(thinking) != {
            "supportedLevels",
            "recommendedLevel",
        }:
            fail(f"{label}.thinking must use exactly the canonical fields")
        levels = string_list(
            thinking.get("supportedLevels"),
            f"{label}.thinking.supportedLevels",
            nonempty_list=True,
        )
        recommended = thinking.get("recommendedLevel")
        if (
            len(levels) != len(set(levels))
            or any(level not in CATALOG_THINKING_LEVELS for level in levels)
            or recommended not in levels
        ):
            fail(f"{label} thinking metadata is invalid")
        routing = item.get("routing")
        allowed_routing_fields = {
            "reviewTier",
            "delegation",
            "reviewComplexities",
            "reviewThinking",
        }
        review_complexities = routing.get("reviewComplexities", []) if isinstance(routing, dict) else []
        minimum_review_thinking = routing.get("reviewThinking", {}) if isinstance(routing, dict) else {}
        if (
            not isinstance(routing, dict)
            or not {"reviewTier"}.issubset(routing)
            or not set(routing).issubset(allowed_routing_fields)
            or routing.get("reviewTier") not in REVIEW_TIERS
            or routing.get("delegation", "baseline-only") not in {
                "routine", "review-or-exceptional-debugging", "exceptional-debugging", "baseline-only"
            }
            or not isinstance(review_complexities, list)
            or len(review_complexities) != len(set(review_complexities))
            or any(value not in REVIEW_COMPLEXITIES for value in review_complexities)
            or not isinstance(minimum_review_thinking, dict)
            or not set(minimum_review_thinking).issubset(set(review_complexities))
            or any(value not in levels for value in minimum_review_thinking.values())
        ):
            fail(
                f"{label}.routing requires valid review, delegation, and review-complexity metadata"
            )
    return {
        "schema_version": schema_version,
        "catalog_version": catalog_version,
        "models": models,
    }


def read_model_catalog(path_value: str, expected_digest: str) -> dict[str, Any]:
    requested = Path(path_value).expanduser()
    if requested != GLOBAL_MODEL_CATALOG:
        fail("model catalog path must be the Pi-global catalog")
    current = Path(requested.anchor)
    for part in requested.parts[1:]:
        current = current / part
        if current.is_symlink():
            fail("model catalog path cannot contain symbolic links")
    if not current.is_file():
        fail("model catalog is missing")
    content = current.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_digest:
        fail("model catalog digest does not match its content")
    try:
        data = json.loads(content, object_pairs_hook=strict_json_object)
    except json.JSONDecodeError as error:
        fail(f"model catalog is invalid JSON: {error}")
    return validate_versioned_catalog(data)


def read_run_artifact(
    state: dict[str, Any], artifact: Any, label: str
) -> tuple[str, str, dict[str, Any]]:
    if not isinstance(artifact, dict):
        fail(f"{label} must include path and digest")
    normalized = normalize_output_path(state, artifact.get("path"), f"{label} path")
    digest = artifact.get("digest")
    candidate = state_directory(state) / normalized
    if (
        not valid_hash(digest)
        or candidate.is_symlink()
        or not candidate.is_file()
        or file_digest(candidate) != digest
    ):
        fail(f"{label} is missing or its digest does not match")
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{label} is not valid JSON: {error}")
    if not isinstance(payload, dict):
        fail(f"{label} must contain a JSON object")
    return normalized, digest, payload


def validate_resolution_artifact(
    state: dict[str, Any], artifact: Any, selection: dict[str, Any]
) -> dict[str, str]:
    path, digest, payload = read_run_artifact(
        state, artifact, "model resolution artifact"
    )
    catalog = state["run"].get("model_catalog") or {}
    payload_catalog = payload.get("catalog") or {}
    if (
        payload.get("launchAllowed") is not True
        or payload.get("stateSelection") != selection
    ):
        fail("model resolution artifact does not match the recorded selection")
    if payload.get("piArgs") != [
        "--provider",
        selection["provider"],
        "--model",
        selection["model_id"],
        "--thinking",
        selection["thinking_level"],
    ]:
        fail("model resolution artifact contains non-canonical Pi arguments")
    if (
        Path(payload_catalog.get("path", "")).expanduser() != GLOBAL_MODEL_CATALOG
        or payload_catalog.get("digest") != catalog.get("digest")
        or payload_catalog.get("schemaVersion") != catalog.get("schema_version")
        or payload_catalog.get("catalogVersion") != catalog.get("catalog_version")
    ):
        fail("model resolution artifact does not match the bound Pi-global catalog")
    request = payload.get("request") or {}
    excluded = request.get("excludedModels", [])
    fallback = request.get("fallbackFrom")
    if (
        not isinstance(excluded, list)
        or len(excluded) != len(set(excluded))
        or (fallback is None and excluded)
        or (fallback is not None and not excluded)
    ):
        fail("model resolution artifact has invalid fallback provenance")
    if fallback is not None:
        if not isinstance(fallback, dict) or set(fallback) != {
            "previousResolution",
            "failureEvidence",
            "cleanupEvidence",
        }:
            fail("model resolution artifact has malformed fallback provenance")
        for value in fallback.values():
            if (
                not isinstance(value, dict)
                or set(value) != {"path", "digest"}
                or not nonempty(value.get("path"))
                or not valid_hash(value.get("digest"))
            ):
                fail("model resolution artifact has incomplete fallback provenance")
    return {"path": path, "digest": digest}


def validate_fallback_evidence(
    state: dict[str, Any], task: dict[str, Any], resolution_artifact: Any
) -> tuple[dict[str, str], dict[str, str]]:
    _, _, payload = read_run_artifact(
        state, resolution_artifact, "fallback model resolution artifact"
    )
    request = payload.get("request") or {}
    fallback = request.get("fallbackFrom")
    if not isinstance(fallback, dict) or set(fallback) != {
        "previousResolution",
        "failureEvidence",
        "cleanupEvidence",
    }:
        fail("fallback resolution must bind prior resolution, failure, and cleanup evidence")
    previous = fallback["previousResolution"]
    active_resolution = task.get("active_resolution") or {}
    expected_previous_path = (state_directory(state) / active_resolution.get("path", "")).resolve()
    if (
        not isinstance(previous, dict)
        or Path(previous.get("path", "")).expanduser().resolve() != expected_previous_path
        or previous.get("digest") != active_resolution.get("digest")
    ):
        fail("fallback resolution does not continue the task's active resolution")
    _, _, previous_payload = read_run_artifact(
        state, active_resolution, "previous model resolution artifact"
    )
    previous_request = previous_payload.get("request") or {}
    zone_keys = {
        "taskClass",
        "inputTypes",
        "minimumQualityRank",
        "thinking",
        "noContributor",
        "strongerThan",
        "strongerThanThinking",
        "selectionMode",
        "userModel",
        "userModelAuthority",
        "exceptionalDebuggingReason",
        "reviewComplexity",
    }
    def routing_zone_value(value: dict[str, Any], key: str) -> Any:
        if key == "reviewComplexity" and value.get("taskClass") == "review":
            return value.get(key, "complicated")
        return value.get(key)

    if (
        any(
            routing_zone_value(request, key)
            != routing_zone_value(previous_request, key)
            for key in zone_keys
        )
        or payload.get("caller") != previous_payload.get("caller")
    ):
        fail("fallback resolution changes the task's routing zone or caller baseline")
    previous_selected = previous_payload.get("selection") or {}
    expected_excluded = list(previous_request.get("excludedModels") or []) + [
        f"{previous_selected.get('provider')}/{previous_selected.get('modelId')}"
    ]
    if request.get("excludedModels") != expected_excluded:
        fail("fallback resolution does not cumulatively exclude exactly the prior selection")

    normalized_refs: list[dict[str, str]] = []
    payloads: list[dict[str, Any]] = []
    for key, label in (
        ("failureEvidence", "fallback failure evidence"),
        ("cleanupEvidence", "fallback cleanup evidence"),
    ):
        artifact = fallback[key]
        try:
            relative = Path(artifact.get("path", "")).expanduser().resolve().relative_to(
                state_directory(state).resolve()
            )
        except (AttributeError, ValueError):
            fail(f"{label} must live under the implementation run folder")
        normalized = {"path": relative.as_posix(), "digest": artifact.get("digest")}
        _, _, artifact_payload = read_run_artifact(state, normalized, label)
        normalized_refs.append(normalized)
        payloads.append(artifact_payload)

    failure, cleanup = payloads
    runtime = task.get("runtime") or {}
    active_model = task.get("active_model") or {}
    if (
        set(failure) != {
            "classification",
            "reasonCode",
            "failedModel",
            "agentSessionId",
            "paneId",
            "usableContribution",
            "sideEffects",
            "launchVerification",
            "runtimeOutput",
        }
        or failure.get("classification") != "model-specific-no-contribution"
        or failure.get("reasonCode") not in {
            "quota",
            "capacity",
            "rate-limit",
            "authentication",
            "availability",
        }
        or failure.get("failedModel")
        != f"{active_model.get('provider')}/{active_model.get('model_id')}"
        or failure.get("usableContribution") is not False
        or failure.get("sideEffects") is not False
        or failure.get("agentSessionId") != runtime.get("agent_instance_id")
        or failure.get("paneId") != runtime.get("pane_id")
    ):
        fail("fallback failure evidence does not prove zero contribution for this runtime")
    if (
        set(cleanup) != {
            "agentSessionId",
            "paneId",
            "agentStopped",
            "paneClosed",
            "remainingActive",
            "closureResponse",
            "absenceResponse",
        }
        or cleanup.get("agentSessionId") != runtime.get("agent_instance_id")
        or cleanup.get("paneId") != runtime.get("pane_id")
        or cleanup.get("agentStopped") is not True
        or cleanup.get("paneClosed") is not True
        or cleanup.get("remainingActive") is not False
    ):
        fail("fallback cleanup evidence does not prove this runtime was removed")

    def normalized_nested(value: Any, label: str) -> dict[str, str]:
        if not isinstance(value, dict) or set(value) != {"path", "digest"}:
            fail(f"{label} must include path and digest")
        try:
            relative = Path(value["path"]).expanduser().resolve().relative_to(
                state_directory(state).resolve()
            )
        except (KeyError, TypeError, ValueError):
            fail(f"{label} must live under the implementation run folder")
        reference = {"path": relative.as_posix(), "digest": value.get("digest")}
        read_run_artifact(state, reference, label)
        return reference

    launch_ref = normalized_nested(
        failure.get("launchVerification"), "fallback launch verification"
    )
    output_ref = normalized_nested(failure.get("runtimeOutput"), "fallback runtime output")
    closure_ref = normalized_nested(cleanup.get("closureResponse"), "fallback closure response")
    _, _, closure = read_run_artifact(state, closure_ref, "fallback closure response")
    if (
        closure.get("id") not in {"cli:pane:close", "cli:tab:close"}
        or (closure.get("result") or {}).get("type") != "ok"
    ):
        fail("fallback closure response is not a successful Herdr close")
    absence_ref = normalized_nested(cleanup.get("absenceResponse"), "fallback pane absence response")
    _, _, absence = read_run_artifact(state, absence_ref, "fallback pane absence response")
    if (
        absence.get("id") != "cli:pane:get"
        or (absence.get("error") or {}).get("code") != "pane_not_found"
        or (absence.get("error") or {}).get("message")
        != f"pane {runtime.get('pane_id')} not found"
    ):
        fail("fallback cleanup does not prove the exact failed pane is absent")
    if launch_ref != runtime.get("launch_verification") or (
        output_ref.get("path") != runtime.get("output_path")
        or output_ref.get("digest") != runtime.get("output_digest")
    ):
        fail("fallback evidence is not bound to this task's launch and output")
    target = task.get("id")
    target_intent_ids = {
        intent.get("id")
        for owner in state.get("tasks", {}).values()
        for intent in owner.get("runtime_intents", [])
        if intent.get("target_task_id") == target
        and intent.get("attempt", 1) == task.get("attempts")
    }
    linked_resources = [
        resource
        for owner in state.get("tasks", {}).values()
        for resource in owner.get("runtime_resources", [])
        if resource.get("intent_id") in target_intent_ids
    ]
    if not linked_resources or any(resource.get("status") != "closed" for resource in linked_resources):
        fail("fallback requires all resources from this attempt to be closed")
    if not any(
        resource.get("closure_artifact") == closure_ref["path"]
        and resource.get("closure_digest") == closure_ref["digest"]
        for resource in linked_resources
    ):
        fail("fallback closure evidence is not bound to a closed runtime resource")
    return normalized_refs[0], normalized_refs[1]


def validate_launch_verification_artifact(
    state: dict[str, Any], task: dict[str, Any], artifact: Any
) -> dict[str, str]:
    path, digest, payload = read_run_artifact(
        state, artifact, "launch verification artifact"
    )
    runtime = task.get("runtime") or {}
    active_model = task.get("active_model") or {}
    expected = payload.get("expected") or {}
    evidence = payload.get("evidence") or {}
    catalog_evidence = evidence.get("catalog") or {}
    resolution_evidence = evidence.get("resolutionArtifact") or {}
    start_evidence = evidence.get("startResponseArtifact") or {}
    intent_id = runtime.get("launch_intent_id")
    intent = next(
        (
            item
            for owner in state["tasks"].values()
            for item in owner.get("runtime_intents", [])
            if item.get("id") == intent_id
        ),
        None,
    )
    if payload.get("verified") is not True:
        fail("launch verification artifact does not contain a verified verdict")
    if expected != {
        "provider": active_model.get("provider"),
        "model": active_model.get("model_id"),
        "thinking": active_model.get("thinking_level"),
    }:
        fail("launch verification does not match the active model")
    if catalog_evidence.get("digest") != (state["run"].get("model_catalog") or {}).get(
        "digest"
    ):
        fail("launch verification does not match the bound catalog digest")
    if resolution_evidence.get("digest") != (task.get("active_resolution") or {}).get(
        "digest"
    ):
        fail(
            "launch verification does not match the active preserved resolution digest"
        )
    if not isinstance(intent, dict):
        fail("launch verification does not identify a bound start response")
    start_path = state_directory(state) / intent.get("output_path", "")
    if (
        start_path.is_symlink()
        or not start_path.is_file()
        or file_digest(start_path) != intent.get("output_digest")
    ):
        fail("bound start response changed after launch")
    try:
        start_payload = json.loads(start_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"bound start response is invalid JSON: {error}")
    _, _, active_resolution = read_run_artifact(
        state, task.get("active_resolution"), "active model resolution artifact"
    )
    start_result = start_payload.get("result") or {}
    start_agent = start_result.get("agent") or {}
    start_session = (start_agent.get("agent_session") or {}).get("value")
    if (
        start_result.get("argv") != ["pi", *(active_resolution.get("piArgs") or [])]
        or start_agent.get("name") != runtime.get("agent_id")
        or start_agent.get("pane_id") != runtime.get("pane_id")
        or start_agent.get("tab_id") != runtime.get("tab_id")
        or start_session != runtime.get("agent_instance_id")
    ):
        fail("bound Herdr start identity or location does not match the runtime")
    evidence_path = Path(start_evidence.get("path", ""))
    if not evidence_path.is_absolute():
        evidence_path = Path(state["run"]["repo_root"]) / evidence_path
    if evidence_path.absolute() != start_path.absolute() or start_evidence.get(
        "digest"
    ) != intent.get("output_digest"):
        fail(
            "launch verification does not match the bound start response path and digest"
        )
    if not nonempty(evidence.get("sessionIdentity")) or evidence.get(
        "sessionIdentity"
    ) != runtime.get("agent_instance_id"):
        fail("launch verification session identity does not match the runtime")
    if (
        active_resolution.get("policyVersion") == 5
        and evidence.get("paneIdentity") != runtime.get("pane_id")
    ):
        fail("launch verification pane identity does not match the runtime")
    return {"path": path, "digest": digest}


def argv_value(argv: Any, flag: str) -> str:
    if not isinstance(argv, list):
        fail("start response argv must be a list")
    positions = [index for index, value in enumerate(argv) if value == flag]
    if len(positions) != 1 or positions[0] + 1 >= len(argv):
        fail(f"start response must contain exactly one {flag}")
    return argv[positions[0] + 1]


def require_live_catalog(state: dict[str, Any]) -> None:
    catalog = state["run"].get("model_catalog")
    if not isinstance(catalog, dict):
        fail("a model catalog is required before launch")
    live = read_model_catalog(catalog["path"], catalog["digest"])
    if (
        live["models"] != catalog.get("models")
        or live["schema_version"] != catalog.get("schema_version")
        or live["catalog_version"] != catalog.get("catalog_version")
    ):
        fail("live model catalog differs from the bound snapshot")


def extract_json_path(value: Any, path: str) -> Any:
    if not nonempty(path):
        fail("runtime intent response_id_path is required")
    current = value
    for part in path.strip(".").split("."):
        if not isinstance(current, dict) or part not in current:
            fail(f"runtime response is missing ID path: {path}")
        current = current[part]
    return current


def load(path: Path) -> dict[str, Any]:
    try:
        with path.open() as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        fail(f"could not read {path}: {error}")
    if not isinstance(value, dict):
        fail("state root must be an object")
    return value


def save_atomic(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=".state-", suffix=".json", dir=path.parent, text=True
    )
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


class LockedState:
    def __init__(self, path: Path):
        self.path = path
        self.lock_path = path.with_name(".state.lock")
        self.handle = None

    def __enter__(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.lock_path.open("a+")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return load(self.path)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.handle:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


def task_template(
    task_id: str, parent_id: str | None, root_id: str, depth: int, event: dict[str, Any]
) -> dict[str, Any]:
    task_class = event.get("task_class", "implementation")
    if task_class not in TASK_CLASSES:
        fail(f"unsupported task_class: {task_class!r}")
    allow_subagents = event.get("allow_subagents", False)
    if not isinstance(allow_subagents, bool):
        fail("allow_subagents must be true or false")
    if task_class == "review":
        allow_subagents = False
    criteria = string_list(
        event.get("acceptance_criteria"), "acceptance_criteria", nonempty_list=True
    )
    dependencies = string_list(event.get("dependencies", []), "dependencies")
    return {
        "id": task_id,
        "parent_id": parent_id,
        "root_id": root_id,
        "depth": depth,
        "title": event.get("title"),
        "outcome": event.get("outcome"),
        "acceptance_criteria": criteria,
        "boundaries": string_list(event.get("boundaries", []), "boundaries"),
        "inputs": string_list(event.get("inputs", []), "inputs"),
        "expected_result": event.get("expected_result"),
        "task_class": task_class,
        "allow_subagents": allow_subagents,
        "status": "planning",
        "phase": "plan",
        "dependencies": dependencies,
        "children": [],
        "todos": [],
        "model_selection": None,
        "model_resolution": None,
        "active_resolution": None,
        "active_model": None,
        "attempts": 0,
        "runtime": {
            "agent_id": None,
            "agent_instance_id": None,
            "pane_id": None,
            "productive_prompt": False,
            "usable_contribution": False,
            "status": "not-started",
        },
        "runtime_history": [],
        "runtime_intents": [],
        "runtime_resources": [],
        "result": {
            "summary": None,
            "files_changed": [],
            "checks": [],
            "evidence": [],
            "blockers": [],
            "cancellation": None,
        },
        "created_at": now(),
        "updated_at": now(),
    }


def descendants(state: dict[str, Any], task_id: str) -> list[str]:
    found: list[str] = []
    queue = list(state["tasks"][task_id]["children"])
    while queue:
        current = queue.pop(0)
        found.append(current)
        queue.extend(state["tasks"][current]["children"])
    return found


def actor_can_manage(state: dict[str, Any], actor: str, target: str) -> bool:
    return (
        actor == target
        or actor == state["tasks"][target]["parent_id"]
        or actor == state["run"]["root_task_id"]
    )


def validate(state: dict[str, Any], state_path: Path | None = None) -> None:
    if state.get("version") != 4:
        fail(f"state version must be 4, found {state.get('version')!r}")
    if not nonempty(state.get("feature_name")) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", state["feature_name"]
    ):
        fail("feature_name must be lowercase kebab-case")
    if not isinstance(state.get("revision"), int) or state["revision"] < 0:
        fail("revision must be a non-negative integer")
    run = state.get("run")
    tasks = state.get("tasks")
    integration = state.get("integration")
    if (
        not isinstance(run, dict)
        or not isinstance(tasks, dict)
        or not tasks
        or not isinstance(integration, dict)
    ):
        fail("run, integration, and a non-empty tasks object are required")
    root_id = run.get("root_task_id")
    if root_id not in tasks:
        fail("root_task_id does not exist")
    repo_root_value = run.get("repo_root")
    if not nonempty(repo_root_value):
        fail("run.repo_root is required")
    repo_root = Path(repo_root_value).resolve()
    if state_path is not None:
        absolute_state = Path(os.path.abspath(state_path))
        if absolute_state.is_symlink():
            fail("state file cannot be a symbolic link")
        resolved_state = absolute_state.resolve()
        expected_state = (
            repo_root
            / "var"
            / state.get("feature_name", "")
            / "implement"
            / "state.json"
        )
        if resolved_state != expected_state.resolve():
            fail("state file is not at the canonical feature implement location")
        try:
            resolved_state.relative_to(repo_root)
        except ValueError:
            fail("state file escapes the repository root")
        current = absolute_state.parent
        while current.resolve() != repo_root:
            if current.is_symlink():
                fail("state path cannot contain symbolic-link directories")
            if current.parent == current:
                fail("state path does not descend from the repository root")
            current = current.parent
    if (
        not nonempty(run.get("coordinator_instance_id"))
        or not isinstance(run.get("coordinator_instance_history"), list)
        or any(not nonempty(item) for item in run["coordinator_instance_history"])
    ):
        fail("run coordinator instance and history are invalid")
    coordinator_model = run.get("coordinator_model")
    coordinator_model_history = run.get("coordinator_model_history")
    required_model_fields = {"instance_id", "provider", "model_id", "thinking_level"}
    if (
        not isinstance(coordinator_model, dict)
        or set(coordinator_model) != required_model_fields
        or coordinator_model.get("instance_id") != run["coordinator_instance_id"]
        or any(
            not nonempty(coordinator_model.get(key)) for key in required_model_fields
        )
        or coordinator_model.get("thinking_level") not in PI_THINKING_LEVELS
        or not isinstance(coordinator_model_history, list)
        or any(
            not isinstance(item, dict)
            or set(item) != required_model_fields
            or any(not nonempty(item.get(key)) for key in required_model_fields)
            or item.get("thinking_level") not in PI_THINKING_LEVELS
            for item in coordinator_model_history
        )
        or [item["instance_id"] for item in coordinator_model_history]
        != run["coordinator_instance_history"]
    ):
        fail("run coordinator model provenance is invalid")
    if not isinstance(run.get("reconciliation_required"), bool):
        fail("run.reconciliation_required must be true or false")
    initial_worktree = run.get("initial_worktree")
    if not isinstance(initial_worktree, dict) or any(
        not nonempty(key) or not nonempty(value)
        for key, value in initial_worktree.items()
    ):
        fail("run.initial_worktree must be a path-to-digest object")
    lease = run.get("coordinator_lease")
    if (
        not isinstance(lease, dict)
        or not nonempty(lease.get("id"))
        or not nonempty(lease.get("expires_at"))
    ):
        fail("run.coordinator_lease requires id and expires_at")
    parse_time(lease["expires_at"], "coordinator lease expiry")
    limits = run.get("limits") or {}
    for key, hard_limit in HARD_LIMITS.items():
        value = limits.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > hard_limit
        ):
            fail(f"run.limits.{key} must be between 0 and {hard_limit}")
    if len(tasks) > limits["max_total_tasks"]:
        fail("task count exceeds max_total_tasks")
    if run.get("status") not in RUN_STATUSES or run.get("phase") not in RUN_PHASES:
        fail("run status or phase is invalid")
    if run["status"] == "complete" and run["phase"] != "complete":
        fail("a complete run must be in the complete phase")
    if run["status"] == "blocked" and run["phase"] != "blocked":
        fail("a blocked run must be in the blocked phase")
    if run["status"] == "running" and run["phase"] in {"complete", "blocked"}:
        fail("a running run cannot use complete or blocked phase")
    catalog = run.get("model_catalog")
    catalog_models: set[tuple[str, str]] | None = None
    catalog_bound = False
    catalog_models_by_ref: dict[tuple[str, str], dict[str, Any]] = {}
    if catalog is not None:
        if (
            not isinstance(catalog, dict)
            or not nonempty(catalog.get("path"))
            or not valid_hash(catalog.get("digest"))
        ):
            fail("run.model_catalog requires a catalog path and SHA-256 digest")
        catalog_data = catalog.get("models")
        if not isinstance(catalog_data, list) or any(
            not isinstance(item, dict) for item in catalog_data
        ):
            fail("run.model_catalog requires an immutable models snapshot")
        schema_version = catalog.get("schema_version")
        catalog_version = catalog.get("catalog_version")
        catalog_bound = True
        validated_catalog = validate_versioned_catalog(
            {
                "schemaVersion": schema_version,
                "catalogVersion": catalog_version,
                "models": catalog_data,
            }
        )
        if validated_catalog["models"] != catalog_data:
            fail("versioned model catalog snapshot is invalid")
        catalog_models_by_ref = {
            (item.get("provider"), item.get("modelId")): item
            for item in catalog_data
            if nonempty(item.get("provider")) and nonempty(item.get("modelId"))
        }
        catalog_models = set(catalog_models_by_ref)
        if not catalog_models:
            fail("model catalog snapshot contains no routable models")

    seen_todos: set[str] = set()
    seen_resources: set[str] = set()
    seen_agent_instances: set[str] = set()
    agent_intent_targets: set[tuple[str, int]] = set()
    for task_id, task in tasks.items():
        if not TASK_ID_RE.fullmatch(task_id) or task.get("id") != task_id:
            fail(f"invalid task ID or key: {task_id}")
        parent_id = task.get("parent_id")
        depth = task.get("depth")
        if task_id == root_id:
            if parent_id is not None or depth != 0 or task.get("root_id") != root_id:
                fail("root task lineage is invalid")
        else:
            if parent_id not in tasks or task_id not in tasks[parent_id].get(
                "children", []
            ):
                fail(f"task {task_id} has an invalid parent relationship")
            if depth != tasks[parent_id]["depth"] + 1 or task.get("root_id") != root_id:
                fail(f"task {task_id} depth or root lineage is invalid")
        if not isinstance(depth, int) or depth > limits["max_depth"]:
            fail(f"task {task_id} exceeds max_depth")
        if depth == limits["max_depth"] and task.get("allow_subagents"):
            fail(f"task {task_id} cannot allow subagents at maximum depth")
        if task.get("status") not in TASK_STATUSES:
            fail(f"task {task_id} has invalid status")
        attempts = task.get("attempts")
        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 0:
            fail(f"task {task_id} attempts must be a non-negative integer")
        if task.get("phase") != TASK_PHASES[task["status"]]:
            fail(f"task {task_id} has an invalid status/phase pair")
        if task.get("task_class") not in TASK_CLASSES:
            fail(f"task {task_id} has invalid task_class")
        if task.get("task_class") == "review" and task.get("allow_subagents"):
            fail(f"review task {task_id} cannot allow subagents")
        if (
            not nonempty(task.get("title"))
            or not nonempty(task.get("outcome"))
            or not nonempty(task.get("expected_result"))
        ):
            fail(f"task {task_id} requires a title, outcome, and expected result")
        string_list(
            task.get("acceptance_criteria"),
            f"task {task_id} acceptance_criteria",
            nonempty_list=True,
        )
        string_list(task.get("boundaries"), f"task {task_id} boundaries")
        string_list(task.get("inputs"), f"task {task_id} inputs")
        children = task.get("children")
        if not isinstance(children, list) or len(children) != len(set(children)):
            fail(f"task {task_id} children must be a unique list")
        if len(children) > limits["max_children_per_task"]:
            fail(f"task {task_id} exceeds max_children_per_task")
        if any(
            child not in tasks or tasks[child].get("parent_id") != task_id
            for child in children
        ):
            fail(f"task {task_id} contains an invalid child reference")
        if children and not task.get("allow_subagents"):
            fail(f"task {task_id} has children without delegation permission")
        dependencies = string_list(
            task.get("dependencies", []), f"task {task_id} dependencies"
        )
        if task_id in dependencies or any(item not in tasks for item in dependencies):
            fail(f"task {task_id} has an invalid dependency")
        todos = task.get("todos")
        if not isinstance(todos, list):
            fail(f"task {task_id} todos must be a list")
        for todo in todos:
            todo_id = todo.get("id") if isinstance(todo, dict) else None
            if not TODO_ID_RE.fullmatch(todo_id or "") or todo_id in seen_todos:
                fail(f"task {task_id} has an invalid or duplicate todo ID")
            seen_todos.add(todo_id)
            if (
                todo.get("status") not in TODO_STATUSES
                or not nonempty(todo.get("title"))
                or not isinstance(todo.get("required"), bool)
            ):
                fail(f"todo {todo_id} is invalid")
            if todo.get("status") == "done" and not nonempty(todo.get("evidence")):
                fail(f"todo {todo_id} needs evidence before completion")
        if (
            task.get("status") in {"working", "waiting", "integrating", "done"}
            and not todos
        ):
            fail(f"task {task_id} started without todos")
        runtime = task.get("runtime")
        if (
            not isinstance(runtime, dict)
            or runtime.get("status") not in RUNTIME_STATUSES
            or not isinstance(runtime.get("usable_contribution", False), bool)
        ):
            fail(f"task {task_id} has invalid runtime state")
        if (
            task_id != root_id
            and attempts == 0
            and runtime.get("status") != "not-started"
        ):
            fail(f"task {task_id} has runtime activity before its only launch attempt")
        if (
            task_id != root_id
            and attempts > 0
            and task.get("status") in {"launching", "working", "waiting", "integrating", "done"}
            and runtime.get("status") == "not-started"
        ):
            fail(f"task {task_id} has no runtime evidence for its active attempt")
        if (
            task_id != root_id
            and attempts == 0
            and task.get("status")
            in {"launching", "working", "waiting", "integrating", "done"}
        ):
            fail(f"task {task_id} started before its only launch attempt")
        if runtime.get("deadline_at") is not None:
            parse_time(runtime["deadline_at"], f"task {task_id} runtime deadline")
        runtime_instance = runtime.get("agent_instance_id")
        if nonempty(runtime_instance):
            if runtime_instance in seen_agent_instances:
                fail(f"task {task_id} reuses an agent session identity")
            seen_agent_instances.add(runtime_instance)
        if (
            catalog_bound
            and runtime.get("status") in {"starting", "working", "blocked", "settled"}
            and not nonempty(runtime.get("launched_thinking_level"))
        ):
            fail(f"task {task_id} runtime lacks launched thinking provenance")
        if runtime.get("status") in {"working", "settled"}:
            if validate_launch_verification_artifact(
                state, task, runtime.get("launch_verification")
            ) != runtime.get("launch_verification"):
                fail(f"task {task_id} launch verification artifact is not normalized")
        runtime_history = task.get("runtime_history")
        if not isinstance(runtime_history, list) or len(runtime_history) != max(0, attempts - 1):
            fail(f"task {task_id} runtime_history must record every replaced attempt")
        for expected_attempt, item in enumerate(runtime_history, start=1):
            if (
                not isinstance(item, dict)
                or set(item) != {
                    "attempt",
                    "model_selection",
                    "model_resolution",
                    "runtime",
                    "failure_evidence",
                    "cleanup_evidence",
                }
                or item.get("attempt") != expected_attempt
            ):
                fail(f"task {task_id} has invalid fallback history")
            historical_runtime = item.get("runtime") or {}
            historical_instance = historical_runtime.get("agent_instance_id")
            if not nonempty(historical_instance) or historical_instance in seen_agent_instances:
                fail(f"task {task_id} fallback history reuses or omits an agent session")
            seen_agent_instances.add(historical_instance)
            historical_selection = validate_model_selection(
                item.get("model_selection"), task["task_class"], require_thinking=catalog_bound
            )
            if validate_resolution_artifact(
                state, item.get("model_resolution"), historical_selection
            ) != item.get("model_resolution"):
                fail(f"task {task_id} historical model resolution is not normalized")
            _, _, historical_failure = read_run_artifact(
                state, item.get("failure_evidence"), "fallback failure evidence"
            )
            _, _, historical_cleanup = read_run_artifact(
                state, item.get("cleanup_evidence"), "fallback cleanup evidence"
            )
            historical_intents = {
                intent.get("id")
                for owner in tasks.values()
                for intent in owner.get("runtime_intents", [])
                if intent.get("target_task_id") == task_id
                and intent.get("attempt", 1) == expected_attempt
            }
            historical_resources = [
                resource
                for owner in tasks.values()
                for resource in owner.get("runtime_resources", [])
                if resource.get("intent_id") in historical_intents
            ]
            if not historical_resources or any(
                resource.get("status") != "closed" for resource in historical_resources
            ):
                fail(f"task {task_id} historical fallback resources are not closed")
            historical_model = item.get("model_selection") or {}
            if (
                set(historical_failure) != {
                    "classification",
                    "reasonCode",
                    "failedModel",
                    "agentSessionId",
                    "paneId",
                    "usableContribution",
                    "sideEffects",
                    "launchVerification",
                    "runtimeOutput",
                }
                or historical_failure.get("classification")
                != "model-specific-no-contribution"
                or historical_failure.get("reasonCode")
                not in {"quota", "capacity", "rate-limit", "authentication", "availability"}
                or historical_failure.get("failedModel")
                != f"{historical_model.get('provider')}/{historical_model.get('model_id')}"
                or historical_failure.get("agentSessionId")
                != historical_runtime.get("agent_instance_id")
                or historical_failure.get("paneId") != historical_runtime.get("pane_id")
                or historical_failure.get("usableContribution") is not False
                or historical_failure.get("sideEffects") is not False
            ):
                fail(f"task {task_id} historical failure evidence is invalid")
            if (
                set(historical_cleanup) != {
                    "agentSessionId",
                    "paneId",
                    "agentStopped",
                    "paneClosed",
                    "remainingActive",
                    "closureResponse",
                    "absenceResponse",
                }
                or historical_cleanup.get("agentSessionId")
                != historical_runtime.get("agent_instance_id")
                or historical_cleanup.get("paneId") != historical_runtime.get("pane_id")
                or historical_cleanup.get("agentStopped") is not True
                or historical_cleanup.get("paneClosed") is not True
                or historical_cleanup.get("remainingActive") is not False
            ):
                fail(f"task {task_id} historical cleanup evidence is invalid")
            historical_launch = historical_failure.get("launchVerification") or {}
            historical_output = historical_failure.get("runtimeOutput") or {}
            historical_closure = historical_cleanup.get("closureResponse") or {}
            historical_absence = historical_cleanup.get("absenceResponse") or {}
            try:
                history_root = state_directory(state).resolve()
                historical_launch_path = Path(historical_launch.get("path", "")).expanduser().resolve().relative_to(history_root).as_posix()
                historical_output_path = Path(historical_output.get("path", "")).expanduser().resolve().relative_to(history_root).as_posix()
                historical_closure_path = Path(historical_closure.get("path", "")).expanduser().resolve().relative_to(history_root).as_posix()
                historical_absence_path = Path(historical_absence.get("path", "")).expanduser().resolve().relative_to(history_root).as_posix()
            except (TypeError, ValueError):
                fail(f"task {task_id} historical nested evidence is outside the run")
            historical_launch_ref = {
                "path": historical_launch_path,
                "digest": historical_launch.get("digest"),
            }
            _, _, historical_launch_payload = read_run_artifact(
                state,
                historical_launch_ref,
                "historical fallback launch verification",
            )
            historical_task = copy.deepcopy(task)
            historical_task["runtime"] = historical_runtime
            historical_task["active_resolution"] = item.get("model_resolution")
            historical_task["active_model"] = {
                "provider": historical_model.get("provider"),
                "model_id": historical_model.get("model_id"),
                "thinking_level": historical_model.get("thinking_level"),
                "source": "primary" if expected_attempt == 1 else "fallback",
            }
            validate_launch_verification_artifact(
                state, historical_task, historical_launch_ref
            )
            read_run_artifact(
                state,
                {"path": historical_output_path, "digest": historical_output.get("digest")},
                "historical fallback runtime output",
            )
            _, _, historical_closure_payload = read_run_artifact(
                state,
                {"path": historical_closure_path, "digest": historical_closure.get("digest")},
                "historical fallback closure response",
            )
            _, _, historical_absence_payload = read_run_artifact(
                state,
                {"path": historical_absence_path, "digest": historical_absence.get("digest")},
                "historical fallback pane absence",
            )
            if (
                historical_launch_payload.get("verified") is not True
                or historical_launch_payload.get("expected")
                != {
                    "provider": historical_model.get("provider"),
                    "model": historical_model.get("model_id"),
                    "thinking": historical_model.get("thinking_level"),
                }
                or historical_closure_payload.get("id")
                not in {"cli:pane:close", "cli:tab:close"}
                or (historical_closure_payload.get("result") or {}).get("type") != "ok"
                or historical_absence_payload.get("id") != "cli:pane:get"
                or (historical_absence_payload.get("error") or {}).get("code") != "pane_not_found"
                or (historical_absence_payload.get("error") or {}).get("message")
                != f"pane {historical_runtime.get('pane_id')} not found"
            ):
                fail(f"task {task_id} historical launch or absence proof is invalid")
            if not any(
                resource.get("closure_artifact") == historical_closure_path
                and resource.get("closure_digest") == historical_closure.get("digest")
                for resource in historical_resources
            ):
                fail(f"task {task_id} historical closure evidence no longer matches its resource")
        model = task.get("model_selection")
        if model is not None:
            validate_model_selection(
                model, task["task_class"], require_thinking=catalog_bound
            )
            if validate_resolution_artifact(
                state, task.get("model_resolution"), model
            ) != task.get("model_resolution"):
                fail(f"task {task_id} model resolution artifact is not normalized")
            recorded_review_complexity = None
            if task["task_class"] == "review":
                _, _, task_resolution = read_run_artifact(
                    state, task.get("model_resolution"), "task model resolution"
                )
                recorded_review_complexity = (
                    task_resolution.get("request") or {}
                ).get("reviewComplexity", "complicated")
                if recorded_review_complexity not in {"simple", "complicated"}:
                    fail(f"task {task_id} review complexity is invalid")
            active_model = task.get("active_model")
            if (
                not isinstance(active_model, dict)
                or not nonempty(active_model.get("provider"))
                or not nonempty(active_model.get("model_id"))
            ):
                fail(f"task {task_id} has invalid active_model")
            if catalog_bound and not nonempty(active_model.get("thinking_level")):
                fail(f"task {task_id} active_model lacks thinking provenance")
            expected_source = "fallback" if runtime_history else "primary"
            if active_model.get("source") != expected_source or task.get(
                "active_resolution"
            ) != task.get("model_resolution"):
                fail(f"task {task_id} active model source or resolution is invalid")
            if (active_model["provider"], active_model["model_id"]) != (
                model["provider"],
                model["model_id"],
            ):
                fail(f"task {task_id} active_model does not match its model selection")
            if catalog_models is None:
                fail(
                    f"task {task_id} has a model selection without a validated catalog"
                )
            choice = (model["provider"], model["model_id"])
            if choice not in catalog_models:
                fail(f"task {task_id} selects a model outside the recorded catalog")
            if catalog_bound:
                level = selection_thinking_level(model)
                required_inputs = set(model["input_types"])
                catalog_choice = catalog_models_by_ref[choice]
                capabilities = catalog_choice.get("capabilities") or {}
                if task["task_class"] not in capabilities.get(
                    "taskClasses", []
                ) or not required_inputs.issubset(
                    set(capabilities.get("inputTypes", []))
                ):
                    fail(
                        f"task {task_id} selects a model without the required task class or input capabilities"
                    )
                supported = (catalog_choice.get("thinking") or {}).get(
                    "supportedLevels", []
                )
                if level not in set(supported):
                    fail(
                        f"task {task_id} selects unsupported thinking for {choice[0]}/{choice[1]}"
                    )
                caller = model["caller"]
                caller_ref = (caller["provider"], caller["model_id"])
                if caller_ref not in catalog_models_by_ref:
                    fail(f"task {task_id} caller is outside the recorded catalog")
                caller_supported = {
                    ("off" if item == "none" else item)
                    for item in (
                        catalog_models_by_ref[caller_ref].get("thinking") or {}
                    ).get("supportedLevels", [])
                }
                if caller["thinking_level"] not in caller_supported:
                    fail(f"task {task_id} caller thinking is unsupported")
                if task["task_class"] == "review":
                    escalation = model["reviewer_escalation"]
                    baselines = escalation["baselines"]
                    baseline_quality = 0
                    baseline_thinking = 0
                    for baseline in baselines:
                        baseline_ref = (baseline["provider"], baseline["model_id"])
                        if baseline_ref not in catalog_models_by_ref:
                            fail(
                                f"task {task_id} review baseline is outside the recorded catalog"
                            )
                        baseline_entry = catalog_models_by_ref[baseline_ref]
                        baseline_supported = {
                            ("off" if item == "none" else item)
                            for item in (baseline_entry.get("thinking") or {}).get(
                                "supportedLevels", []
                            )
                        }
                        if baseline["thinking_level"] not in baseline_supported:
                            fail(
                                f"task {task_id} review baseline thinking is unsupported"
                            )
                        baseline_quality = max(
                            baseline_quality,
                            REVIEW_TIER_RANK[baseline_entry["routing"]["reviewTier"]],
                        )
                        baseline_thinking = max(
                            baseline_thinking,
                            PI_THINKING_RANK[baseline["thinking_level"]],
                        )
                    selected_entry = catalog_models_by_ref[
                        (model["provider"], model["model_id"])
                    ]
                    expected_review_complexity = recorded_review_complexity
                    expected_escalation = (
                        "peer"
                        if expected_review_complexity == "simple"
                        else "stronger"
                    )
                    if escalation.get("status") != expected_escalation:
                        fail(
                            f"task {task_id} review escalation does not match its recorded complexity"
                        )
                    selected_routing = selected_entry["routing"]
                    review_complexities = selected_routing.get("reviewComplexities")
                    review_thinking = selected_routing.get("reviewThinking")
                    if review_complexities is not None and (
                        expected_review_complexity not in review_complexities
                        or (review_thinking or {}).get(expected_review_complexity)
                        != model["thinking_level"]
                    ):
                        fail(
                            f"task {task_id} reviewer violates its catalog review routing"
                        )
                    selected_quality = REVIEW_TIER_RANK[
                        selected_routing["reviewTier"]
                    ]
                    selected_thinking = PI_THINKING_RANK[model["thinking_level"]]
                    non_regressive = (
                        selected_quality >= baseline_quality
                        and selected_thinking >= baseline_thinking
                    )
                    strictly_higher = (
                        selected_quality > baseline_quality
                        or selected_thinking > baseline_thinking
                    )
                    if not non_regressive or (
                        expected_review_complexity == "complicated"
                        and not strictly_higher
                    ):
                        fail(
                            f"task {task_id} reviewer does not satisfy its recorded escalation"
                        )
        active_task_states = {"launching", "working", "waiting", "integrating"}
        active_runtime_states = {
            "starting",
            "working",
            "blocked",
            "cancellation-requested",
        }
        cancelling_with_runtime = (
            task.get("status") == "cancelling"
            and runtime.get("status") != "not-started"
        )
        requires_slot = (
            task.get("status") in active_task_states
            or cancelling_with_runtime
            or (
                task.get("status") == "blocked"
                and runtime.get("status") in active_runtime_states
            )
        )
        if (
            task_id != root_id
            and requires_slot
            and task_id not in run.get("active_agent_slots", [])
        ):
            fail(f"active task {task_id} lacks a reserved root-wide slot")
        if requires_slot and any(
            tasks[dependency]["status"] != "done"
            for dependency in task.get("dependencies", [])
        ):
            fail(f"task {task_id} started before its dependencies completed")
        if runtime.get("status") in active_runtime_states and task.get(
            "status"
        ) not in active_task_states | {"blocked", "cancelling"}:
            fail(f"task {task_id} runtime is active while task state is not")
        if (
            task_id != root_id
            and task.get("status")
            in {"launching", "working", "waiting", "integrating", "done"}
            and model is None
        ):
            fail(f"task {task_id} started without a recorded model selection")
        if (
            task_id != root_id
            and task.get("status") in {"working", "waiting", "integrating", "done"}
            and not nonempty(runtime.get("agent_instance_id"))
        ):
            fail(f"task {task_id} started without immutable agent-instance provenance")
        task_result = task.get("result")
        if not isinstance(task_result, dict):
            fail(f"task {task_id} result must be an object")
        validate_repo_files(
            task_result.get("files_changed", []), f"task {task_id} files_changed"
        )
        for field in ("checks", "evidence", "blockers"):
            if not isinstance(task_result.get(field), list):
                fail(f"task {task_id} result.{field} must be a list")
        cancellation = task_result.get("cancellation")
        if cancellation is not None and (
            not isinstance(cancellation, dict)
            or not nonempty(cancellation.get("reason"))
            or not nonempty(cancellation.get("parent_disposition"))
        ):
            fail(f"task {task_id} cancellation requires reason and parent disposition")
        intents = task.get("runtime_intents")
        if not isinstance(intents, list):
            fail(f"task {task_id} runtime_intents must be a list")
        intent_ids = set()
        for intent in intents:
            intent_id = intent.get("id") if isinstance(intent, dict) else None
            if (
                not nonempty(intent_id)
                or intent_id in intent_ids
                or intent.get("status") not in {"planned", "bound", "failed"}
                or not nonempty(intent.get("output_path"))
                or not intent["output_path"].startswith("outputs/")
                or intent.get("target_task_id") not in tasks
                or not nonempty(intent.get("response_id_path"))
            ):
                fail(f"task {task_id} has an invalid runtime intent")
            if intent.get("status") == "bound" and (
                not nonempty(intent.get("resource_id"))
                or not valid_hash(intent.get("output_digest"))
            ):
                fail(
                    f"bound runtime intent {intent_id} lacks resource and response digest"
                )
            if intent.get("kind") == "agent":
                target_task_id = intent.get("target_task_id")
                intent_attempt = intent.get("attempt", 1)
                intent_key = (target_task_id, intent_attempt)
                if (
                    isinstance(intent_attempt, bool)
                    or not isinstance(intent_attempt, int)
                    or intent_attempt < 1
                    or intent_attempt > tasks[target_task_id]["attempts"]
                    or intent_key in agent_intent_targets
                ):
                    fail(f"task {target_task_id} has an invalid duplicate agent attempt intent")
                readiness = intent.get("readiness")
                if readiness is not None:
                    if (
                        not isinstance(readiness, dict)
                        or not nonempty(readiness.get("pane_intent_id"))
                        or not nonempty(readiness.get("pane_id"))
                        or not nonempty(readiness.get("created_at"))
                        or not nonempty(readiness.get("deadline_at"))
                        or not isinstance(readiness.get("probes"), list)
                        or not readiness["probes"]
                        or readiness.get("busy_start_count", 0) not in {0, 1}
                    ):
                        fail(f"agent intent {intent_id} has invalid readiness state")
                    created_at = parse_time(readiness["created_at"], "pane readiness created_at")
                    deadline_at = parse_time(readiness["deadline_at"], "pane readiness deadline_at")
                    overflow_sentinel = created_at == deadline_at == MAX_UTC_TIMESTAMP
                    if not valid_readiness_deadline(created_at, deadline_at):
                        fail(f"agent intent {intent_id} has an invalid readiness deadline")
                    overflow_probe = False
                    terminal_probe_seen = False
                    previous_snapshot_payload = None
                    previous_observed_at = None
                    for probe in readiness["probes"]:
                        if not isinstance(probe, dict) or probe.get("classification") not in {"ready", "busy", "expired", "ambiguous"}:
                            fail(f"agent intent {intent_id} has an invalid readiness probe")
                        if terminal_probe_seen:
                            fail(f"agent intent {intent_id} has readiness evidence after a terminal probe")
                        _, _, snapshot_payload = read_run_artifact(
                            state, probe.get("snapshot"), "pane readiness snapshot"
                        )
                        _, _, class_payload = read_run_artifact(
                            state, probe.get("classification_artifact"), "pane readiness classification"
                        )
                        validate_readiness_probe_evidence(
                            snapshot_payload,
                            class_payload,
                            probe["classification"],
                            readiness["pane_id"],
                            readiness["created_at"],
                            readiness["deadline_at"],
                            allow_legacy_observation=readiness.get("busy_start_count", 0) == 1,
                        )
                        if previous_snapshot_payload is not None and probe["classification"] != "ambiguous":
                            validate_readiness_probe_transition(previous_snapshot_payload, snapshot_payload)
                        observed_at = parse_time(
                            class_payload.get("observedAt") or readiness["created_at"],
                            "readiness classification observedAt",
                        )
                        if previous_observed_at is not None and observed_at < previous_observed_at:
                            fail(f"agent intent {intent_id} has non-monotonic readiness observations")
                        previous_observed_at = observed_at
                        probe_recorded_at = parse_time(
                            probe.get("recorded_at"), "readiness probe recorded_at"
                        )
                        if probe_recorded_at < created_at:
                            fail(f"agent intent {intent_id} records readiness before pane creation")
                        if probe["classification"] == "expired" and probe_recorded_at < deadline_at:
                            fail(f"agent intent {intent_id} records expiration before its deadline")
                        previous_snapshot_payload = snapshot_payload
                        if probe.get("classification") in {"ready", "expired", "ambiguous"}:
                            terminal_probe_seen = True
                        if (
                            probe.get("classification") == "ambiguous"
                            and class_payload.get("reason") == READINESS_OVERFLOW_REASON
                            and class_payload.get("createdAt") == readiness["created_at"]
                            and class_payload.get("deadlineAt") == readiness["deadline_at"]
                        ):
                            overflow_probe = True
                    pane_intent = next(
                        (candidate for candidate in intents if candidate.get("id") == readiness["pane_intent_id"]),
                        None,
                    )
                    if (
                        pane_intent is None
                        or pane_intent.get("kind") != "pane"
                        or pane_intent.get("target_task_id") != target_task_id
                        or pane_intent.get("status") != "bound"
                        or pane_intent.get("resource_id") != readiness["pane_id"]
                    ):
                        fail(f"agent intent {intent_id} readiness is not bound to its target pane intent")
                    if nonempty(tasks[target_task_id]["runtime"].get("pane_id")) and (
                        tasks[target_task_id]["runtime"]["pane_id"] != readiness["pane_id"]
                    ):
                        fail(f"agent intent {intent_id} readiness does not match the task runtime pane")
                    if overflow_sentinel and (len(readiness["probes"]) != 1 or not overflow_probe):
                        fail(f"agent intent {intent_id} lacks a terminal overflow ambiguity proof")
                    busy_artifact = readiness.get("busy_start_artifact")
                    if readiness.get("busy_start_count", 0) == 1:
                        _, _, busy_payload = read_run_artifact(state, busy_artifact, "legacy pre-launch busy response")
                        if (busy_payload.get("error") or {}).get("code") != "agent_pane_busy":
                            fail(f"agent intent {intent_id} has invalid legacy busy-start evidence")
                    elif busy_artifact is not None:
                        fail(f"agent intent {intent_id} has unexpected busy-start evidence")
                if intent.get("status") == "bound" and (
                    not isinstance(readiness, dict)
                    or readiness["probes"][-1].get("classification") != "ready"
                ):
                    fail(f"bound agent intent {intent_id} lacks a final ready pane proof")
                agent_intent_targets.add(intent_key)
            intent_ids.add(intent_id)
        resources = task.get("runtime_resources")
        if not isinstance(resources, list):
            fail(f"task {task_id} runtime_resources must be a list")
        for resource in resources:
            resource_id = resource.get("id") if isinstance(resource, dict) else None
            if not nonempty(resource_id) or resource_id in seen_resources:
                fail(f"task {task_id} has an invalid or duplicate runtime resource ID")
            seen_resources.add(resource_id)
            if resource.get("status") not in RESOURCE_STATUSES:
                fail(f"runtime resource {resource_id} has an invalid status")
            if resource.get("status") == "preserved" and not nonempty(
                resource.get("reason")
            ):
                fail(
                    f"preserved runtime resource {resource_id} requires a blocker reason"
                )
            if resource.get("status") == "closed" and (
                not nonempty(resource.get("closure_artifact"))
                or not valid_hash(resource.get("closure_digest"))
            ):
                fail(f"closed runtime resource {resource_id} lacks closure evidence")
        if task.get("status") in SETTLED:
            if any(intent.get("status") == "planned" for intent in intents):
                fail(f"settled task {task_id} has unresolved runtime intents")
            if any(resource.get("status") == "live" for resource in resources):
                fail(f"settled task {task_id} has live runtime resources")
            if task_id in run.get("active_agent_slots", []):
                fail(f"settled task {task_id} still owns an active agent slot")
        if task.get("status") == "cancelled":
            if runtime.get("status") not in {
                "not-started",
                "stopped",
                "settled",
                "cancelled",
            }:
                fail(f"cancelled task {task_id} lacks confirmed runtime shutdown")
            if not isinstance(task_result.get("cancellation"), dict):
                fail(f"cancelled task {task_id} lacks cancellation disposition")
        if task.get("status") == "done":
            if any(todo.get("status") not in SETTLED for todo in todos):
                fail(f"task {task_id} completed with open todos")
            if any(tasks[child]["status"] not in SETTLED for child in children):
                fail(f"task {task_id} completed with unsettled children")
            if not nonempty((task.get("result") or {}).get("summary")):
                fail(f"task {task_id} completed without a result summary")

    all_intents = {
        intent["id"]: intent
        for task in tasks.values()
        for intent in task.get("runtime_intents", [])
        if isinstance(intent, dict) and nonempty(intent.get("id"))
    }
    all_resources = {
        resource["id"]: resource
        for task in tasks.values()
        for resource in task.get("runtime_resources", [])
        if isinstance(resource, dict) and nonempty(resource.get("id"))
    }
    for resource in all_resources.values():
        parent_tab_id = resource.get("parent_tab_id")
        if parent_tab_id is not None and (
            parent_tab_id not in all_resources
            or all_resources[parent_tab_id].get("kind") != "tab"
        ):
            fail(f"runtime resource {resource['id']} has an invalid parent tab")
        if resource.get("kind") == "agent" and nonempty(parent_tab_id):
            agent_intent = all_intents.get(resource.get("intent_id"))
            readiness = agent_intent.get("readiness") if isinstance(agent_intent, dict) else None
            ready_pane = all_resources.get(readiness.get("pane_id")) if isinstance(readiness, dict) else None
            if ready_pane is None or ready_pane.get("parent_tab_id") != parent_tab_id:
                fail(f"agent resource {resource['id']} does not share its ready pane's parent tab")
        if resource.get("reason") == "cascade-deleted-with-owned-tab" and (
            not nonempty(parent_tab_id)
            or all_resources[parent_tab_id].get("status") != "closed"
            or all_resources[parent_tab_id].get("closure_digest") != resource.get("closure_digest")
        ):
            fail(f"runtime resource {resource['id']} lacks matching parent-tab cascade evidence")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            fail("task lineage and dependencies contain a cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for related in [
            *tasks[task_id].get("dependencies", []),
            *tasks[task_id].get("children", []),
        ]:
            visit(related)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id)

    task_numbers = [int(TASK_ID_RE.fullmatch(task_id).group(1)) for task_id in tasks]
    todo_numbers = [
        int(TODO_ID_RE.fullmatch(todo_id).group(1)) for todo_id in seen_todos
    ]
    if not isinstance(state.get("next_task_sequence"), int) or state[
        "next_task_sequence"
    ] <= max(task_numbers):
        fail("next_task_sequence must be greater than every allocated task ID")
    if not isinstance(state.get("next_todo_sequence"), int) or state[
        "next_todo_sequence"
    ] <= max(todo_numbers, default=0):
        fail("next_todo_sequence must be greater than every allocated todo ID")

    slots = run.get("active_agent_slots")
    if not isinstance(slots, list) or len(slots) != len(set(slots)):
        fail("active_agent_slots must be a unique list")
    if len(slots) > limits["max_active_agents"]:
        fail("active agent count exceeds max_active_agents")
    for task_id in slots:
        if task_id not in tasks or tasks[task_id]["runtime"].get("status") not in {
            "reserved",
            "starting",
            "working",
            "blocked",
            "cancellation-requested",
            "settled",
            "stopped",
        }:
            fail(f"active slot for {task_id} is inconsistent")
    if integration.get("test_verdict") not in {
        "pending",
        "pass",
        "skipped",
        "fail",
        "blocked",
    }:
        fail("integration.test_verdict is invalid")
    if integration.get("behavior_verdict") not in {
        "pending",
        "pass",
        "user-pending",
        "not-applicable",
        "fail",
        "blocked",
    }:
        fail("integration.behavior_verdict is invalid")
    eligibility = integration.get("behavior_eligibility")
    if eligibility is not None and (
        not isinstance(eligibility, dict)
        or eligibility.get("classification") != "documentation-only"
        or not nonempty(eligibility.get("evidence"))
    ):
        fail("behavior eligibility must document a documentation-only classification")
    if integration.get("review_verdict") not in {"pending", "pass", "not-required", "fail", "blocked"}:
        fail("integration.review_verdict is invalid")
    if integration.get("review_execution") not in {None, "independent", "not-required"}:
        fail("integration.review_execution must be independent or not-required")
    review_requirement = integration.get("review_requirement")
    if review_requirement is not None and (
        not isinstance(review_requirement, dict)
        or review_requirement.get("classification") not in {"simple", "complicated", "feature"}
        or review_requirement.get("source") not in {"automatic", "user-request"}
        or review_requirement.get("required")
        != (
            review_requirement.get("classification") != "simple"
            or review_requirement.get("source") == "user-request"
        )
        or not nonempty(review_requirement.get("reason"))
    ):
        fail("integration.review_requirement is invalid")
    if not isinstance(integration.get("review_perspectives"), dict) or any(
        not isinstance(item, dict) for item in integration["review_perspectives"].values()
    ):
        fail("integration.review_perspectives must be an object of objects")
    minimum_review_wave = integration.get("minimum_review_wave", 0)
    if (
        isinstance(minimum_review_wave, bool)
        or not isinstance(minimum_review_wave, int)
        or minimum_review_wave < 0
    ):
        fail("integration.minimum_review_wave must be a non-negative integer")
    review_resources = integration.get("review_resources", [])
    if not isinstance(review_resources, list):
        fail("integration.review_resources must be a list")
    review_resource_ids = set()
    for resource in review_resources:
        if (
            not isinstance(resource, dict)
            or resource.get("kind") != "tab"
            or not nonempty(resource.get("id"))
            or resource["id"] in review_resource_ids
            or resource.get("status") not in {"open", "closed"}
        ):
            fail("review resources require unique tab IDs and open or closed status")
        review_resource_ids.add(resource["id"])
    changed_files = integration.get("changed_files")
    collisions = integration.get("collisions")
    validate_repo_files(changed_files, "integration.changed_files")
    if not isinstance(collisions, list):
        fail("integration.collisions must be a list")
    for collision in collisions:
        if not isinstance(collision, dict) or collision.get("status") not in {"open", "resolved"}:
            fail("each integration collision needs open or resolved status")
        if not isinstance(collision.get("tasks"), list) or not isinstance(collision.get("files"), list):
            fail("collision entries require task and file lists")
        if collision.get("status") == "resolved" and (
            not nonempty(collision.get("resolution"))
            or not isinstance(collision.get("rerun_evidence"), list)
            or not collision["rerun_evidence"]
        ):
            fail("resolved collisions require a resolution and rerun evidence")
    if not isinstance(integration.get("test_evidence"), list):
        fail("integration.test_evidence must be a list")
    if not isinstance(integration.get("behavior_evidence"), list):
        fail("integration.behavior_evidence must be a list")
    review_findings = integration.get("review_findings")
    if not isinstance(review_findings, list):
        fail("integration.review_findings must be a list")
    finding_ids = set()
    for finding in review_findings:
        finding_id = finding.get("id") if isinstance(finding, dict) else None
        if (
            not nonempty(finding_id)
            or finding_id in finding_ids
            or finding.get("severity") not in {"P0", "P1", "P2", "P3"}
            or finding.get("status") not in {"open", "resolved", "rejected"}
        ):
            fail("review findings require unique IDs, severity, and valid status")
        finding_ids.add(finding_id)
        if finding.get("status") in {"resolved", "rejected"} and not nonempty(finding.get("resolution")):
            fail(f"review finding {finding_id} requires a resolution")
    if run.get("status") == "complete":
        if tasks[root_id]["status"] != "done":
            fail("a complete run requires a done root task")
        if (
            not (
                integration.get("review_verdict") == "pass"
                and integration.get("review_execution") == "independent"
                or integration.get("review_verdict") == "not-required"
                and integration.get("review_execution") == "not-required"
            )
            or integration.get("test_verdict") not in {"pass", "skipped"}
            or integration.get("behavior_verdict")
            not in {"pass", "user-pending", "not-applicable"}
        ):
            fail(
                "a complete run requires checks, a settled behavior handoff, and a settled review decision"
            )
        if slots or any(
            task["status"] not in SETTLED
            for task_id, task in tasks.items()
            if task_id != root_id
        ):
            fail("a complete run cannot have active or unsettled descendants")
        if any(
            resource.get("status") != "closed"
            for task in tasks.values()
            for resource in task["runtime_resources"]
        ):
            fail("a complete run requires every runtime resource to be closed")


def apply_event(
    state: dict[str, Any],
    state_path: Path,
    actor: str,
    lease_id: str | None,
    event: dict[str, Any],
) -> dict[str, Any]:
    validate(state, state_path)
    tasks = state["tasks"]
    if not isinstance(actor, str) or actor not in tasks:
        fail(f"unknown actor task: {actor!r}")
    event_type = event.get("type")
    if not nonempty(event_type):
        fail("event type must be a non-empty string")
    if event_type in DEPRECATED_EVENT_TYPES:
        fail(f"deprecated event type: {event_type!r}; {DEPRECATED_EVENT_TYPES[event_type]}.")
    if event_type not in SUPPORTED_EVENT_TYPES:
        matches = difflib.get_close_matches(event_type, SUPPORTED_EVENT_TYPES, n=1, cutoff=0.45)
        suggestion = f" Did you mean {matches[0]!r}?" if matches else ""
        fail(f"unsupported event type: {event_type!r}.{suggestion} Run the documented 'events' command for supported names and bootstrap examples.")
    root_id = state["run"]["root_task_id"]
    caller_session = os.environ.get("PI_SESSION_FILE")
    if actor == root_id:
        lease = state["run"]["coordinator_lease"]
        if (
            not nonempty(caller_session)
            or caller_session != state["run"]["coordinator_instance_id"]
            or not nonempty(lease_id)
            or lease_id != lease["id"]
            or parse_time(lease["expires_at"], "coordinator lease expiry")
            <= datetime.now(timezone.utc)
        ):
            fail("root operation requires the recorded coordinator session and an unexpired matching lease")
        lease["expires_at"] = future()
    elif (
        not nonempty(caller_session)
        or caller_session != tasks[actor]["runtime"].get("agent_instance_id")
    ):
        fail("descendant operation requires the task's recorded Pi session")
    if state["run"]["status"] in {"complete", "cancelled"}:
        fail("terminal runs cannot be mutated")
    recovery_events = {
        "record-runtime",
        "record-launch-verification",
        "bind-runtime-intent",
        "record-pane-readiness",
        "fail-runtime-intent",
        "settle-runtime-resource",
        "release-slot",
        "cancel-subtree",
        "finalize-cancellation",
        "cancel-run",
        "record-result",
        "fail-launch",
        "finish-reconciliation",
        "set-run-phase",
        "update-integration",
    }
    if (
        state["run"].get("reconciliation_required")
        and event_type not in recovery_events
    ):
        fail("runtime reconciliation must finish before normal work continues")
    if state["run"]["status"] == "blocked" and event_type not in recovery_events:
        fail(
            "blocked runs allow only recovery, cleanup, cancellation, and explicit unblocking"
        )
    if actor != root_id and tasks[actor]["status"] in SETTLED:
        fail("settled tasks cannot mutate state")
    limits = state["run"]["limits"]
    bound_catalog = state["run"].get("model_catalog") or {}
    catalog_bound = bound_catalog.get("schema_version") is not None
    result: dict[str, Any] = {"event": event_type}

    if event_type == "set-run":
        if actor != root_id:
            fail("only the root task may configure the run")
        allowed = {"user_goal", "stop_reason", "model_catalog"}
        updates = event.get("updates")
        if not isinstance(updates, dict) or set(updates) - allowed:
            fail("set-run may update only the goal, stop reason, and model catalog")
        updates = copy.deepcopy(updates)
        if "model_catalog" in updates:
            supplied = updates["model_catalog"]
            if (
                not isinstance(supplied, dict)
                or not nonempty(supplied.get("path"))
                or not valid_hash(supplied.get("digest"))
            ):
                fail("model catalog update requires path and SHA-256 digest")
            parsed_catalog = read_model_catalog(supplied["path"], supplied["digest"])
            supplied.update(parsed_catalog)
        if (
            "user_goal" in updates
            and state["run"].get("user_goal") not in {None, updates["user_goal"]}
            and state["run"]["phase"] not in {"bootstrap", "plan"}
        ):
            fail("the user goal is frozen after planning")
        if (
            "model_catalog" in updates
            and state["run"].get("model_catalog") is not None
            and state["run"]["model_catalog"] != updates["model_catalog"]
            and len(tasks) > 1
        ):
            fail("the model catalog is frozen after the first child is created")
        state["run"].update(updates)

    elif event_type == "set-run-phase":
        if actor != root_id:
            fail("only the root task may advance the run phase")
        current = state["run"]["phase"]
        target = event.get("phase")
        if target not in RUN_TRANSITIONS[current]:
            fail(f"invalid run phase transition: {current} -> {target}")
        if target == "execute" and (
            not nonempty(state["run"].get("user_goal"))
            or not tasks[root_id].get("todos")
        ):
            fail("execution requires a recorded user goal and root todos")
        if target == "execute":
            invalidate_review(state["integration"])
        state["run"]["phase"] = target
        state["run"]["status"] = "blocked" if target == "blocked" else "running"
        state["run"]["stop_reason"] = (
            event.get("reason") if target == "blocked" else None
        )

    elif event_type == "finish-reconciliation":
        if actor != root_id or not state["run"].get("reconciliation_required"):
            fail("only the root may finish an active reconciliation")
        evidence = event.get("evidence")
        if not nonempty(evidence):
            fail("runtime reconciliation requires evidence")
        recoverable_targets = set()
        for task in tasks.values():
            for intent in task.get("runtime_intents", []):
                if intent.get("status") != "planned":
                    continue
                readiness = intent.get("readiness")
                if intent.get("status") == "planned":
                    fail("planned runtime intents remain unreconciled")
                recoverable_targets.add(intent.get("target_task_id"))
        for task_id in state["run"]["active_agent_slots"]:
            if (
                tasks[task_id]["runtime"].get("status") in {"not-started", "reserved"}
                and task_id not in recoverable_targets
            ):
                fail(f"active task {task_id} has not been reconciled")
        if any(
            item.get("status") == "open"
            for item in state["integration"].get("review_resources", [])
        ):
            fail("review tabs must be closed before reconciliation finishes")
        state["run"]["reconciliation_required"] = False
        state["run"]["reconciliation_evidence"] = evidence

    elif event_type == "update-contract":
        if actor != root_id:
            fail("descendant contracts are parent-owned and immutable")
        task = tasks[actor]
        if task["status"] != "planning" or state["run"]["phase"] not in {
            "bootstrap",
            "plan",
        }:
            fail("the root contract cannot change after planning")
        allowed = {
            "title",
            "outcome",
            "acceptance_criteria",
            "boundaries",
            "inputs",
            "expected_result",
        }
        updates = event.get("updates")
        if not isinstance(updates, dict) or set(updates) - allowed:
            fail("update-contract contains unsupported root fields")
        task.update(updates)

    elif event_type == "replan-child":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target == actor
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail("only the direct parent or recorded root recovery may replan a child")
        task = tasks[target]
        updates = event.get("updates")
        if not isinstance(updates, dict):
            fail("replan-child updates must be an object")
        if task["attempts"] == 0 and task["status"] in {"planning", "queued"}:
            allowed = {
                "title",
                "outcome",
                "acceptance_criteria",
                "boundaries",
                "inputs",
                "expected_result",
                "dependencies",
                "allow_subagents",
            }
        elif task["status"] == "blocked":
            allowed = {"dependencies"}
        else:
            fail(
                "a child can be replanned only before launch or while explicitly blocked"
            )
        if set(updates) - allowed:
            fail("replan-child contains unsupported fields for the task state")
        if updates.get("allow_subagents") is True and not task.get("allow_subagents"):
            fail("replanning cannot widen delegation permission")
        task.update(updates)

    elif event_type == "add-todo":
        task = tasks[actor]
        if task["status"] in SETTLED:
            fail("cannot add a todo to a settled task")
        todo_id = f"todo-{state['next_todo_sequence']:04d}"
        state["next_todo_sequence"] += 1
        title = event.get("title")
        if not nonempty(title):
            fail("todo title is required")
        task["todos"].append(
            {
                "id": todo_id,
                "title": title,
                "acceptance": event.get("acceptance"),
                "required": event.get("required", True),
                "status": "pending",
                "evidence": None,
                "updated_at": now(),
            }
        )
        result["todo_id"] = todo_id

    elif event_type == "set-todo":
        task = tasks[actor]
        todo_id = event.get("todo_id")
        todo = next((item for item in task["todos"] if item["id"] == todo_id), None)
        if todo is None:
            fail(f"unknown todo for {actor}: {todo_id}")
        status = event.get("status")
        if todo["status"] in SETTLED and status != todo["status"]:
            fail("a settled todo cannot be reopened; create a new todo")
        if status not in TODO_STATUSES:
            fail("invalid todo status")
        evidence = event.get("evidence")
        if status == "done" and not nonempty(evidence):
            fail("done todos require evidence")
        todo.update({"status": status, "evidence": evidence, "updated_at": now()})

    elif event_type == "add-child":
        parent = tasks[actor]
        if parent["status"] not in {
            "working",
            "waiting",
            "integrating",
        } or not parent.get("todos"):
            fail("a parent must be actively working with todos before adding children")
        if not parent.get("allow_subagents"):
            fail(f"task {actor} is not allowed to add children")
        if len(parent["children"]) >= limits["max_children_per_task"]:
            fail("parent has reached max_children_per_task")
        if len(tasks) >= limits["max_total_tasks"]:
            fail("run has reached max_total_tasks")
        depth = parent["depth"] + 1
        if depth > limits["max_depth"]:
            fail("child would exceed max_depth")
        task_id = f"task-{state['next_task_sequence']:04d}"
        state["next_task_sequence"] += 1
        require_live_catalog(state)
        child_event = copy.deepcopy(event)
        if depth == limits["max_depth"] or child_event.get("task_class") == "review":
            child_event["allow_subagents"] = False
        child = task_template(task_id, actor, root_id, depth, child_event)
        for dependency in child["dependencies"]:
            if dependency not in tasks:
                fail(f"unknown child dependency: {dependency}")
        selection = validate_model_selection(
            event.get("model_selection"),
            child["task_class"],
            require_thinking=catalog_bound,
        )
        child["model_selection"] = selection
        child["model_resolution"] = validate_resolution_artifact(
            state, event.get("resolution_artifact"), selection
        )
        child["active_resolution"] = copy.deepcopy(child["model_resolution"])
        child["active_model"] = {
            "provider": selection["provider"],
            "model_id": selection["model_id"],
            "thinking_level": selection_thinking_level(selection),
            "source": "primary",
        }
        reserve = event.get("reserve_slot", True)
        if not isinstance(reserve, bool):
            fail("reserve_slot must be true or false")
        if reserve:
            if any(
                tasks[dependency]["status"] != "done"
                for dependency in child["dependencies"]
            ):
                fail("cannot reserve a child slot before its dependencies finish")
            if len(state["run"]["active_agent_slots"]) >= limits["max_active_agents"]:
                fail("no root-wide agent slot is available for the new child")
            child["attempts"] = 1
            child["status"] = "launching"
            child["phase"] = "launch"
            child["runtime"].update(
                {"status": "reserved", "reserved_by": actor, "reserved_at": now()}
            )
            state["run"]["active_agent_slots"].append(task_id)
        else:
            child["status"] = "queued"
        tasks[task_id] = child
        parent["children"].append(task_id)
        result["task_id"] = task_id
        result["slot_reserved"] = reserve

    elif event_type == "record-model":
        target = event.get("task_id", actor)
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target == actor
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail("only the direct parent or recorded root recovery may choose a model")
        task = tasks[target]
        if (
            task.get("model_selection") is not None
            or task.get("model_resolution") is not None
        ):
            fail("model selection can be recorded only once")
        if task["attempts"] != 0 or task["status"] not in {"planning", "queued"}:
            fail("model selection is immutable after the first slot reservation")
        selection = validate_model_selection(
            event.get("selection"), task["task_class"], require_thinking=catalog_bound
        )
        task["model_selection"] = selection
        task["model_resolution"] = validate_resolution_artifact(
            state, event.get("resolution_artifact"), selection
        )
        task["active_resolution"] = copy.deepcopy(task["model_resolution"])
        task["active_model"] = {
            "provider": selection["provider"],
            "model_id": selection["model_id"],
            "thinking_level": selection_thinking_level(selection),
            "source": "primary",
        }

    elif event_type == "reserve-slot":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target == actor
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail("only the direct parent or recorded root recovery may reserve a slot")
        if target in state["run"]["active_agent_slots"]:
            fail("task already owns an active agent slot")
        if len(state["run"]["active_agent_slots"]) >= limits["max_active_agents"]:
            fail("no root-wide agent slot is available")
        require_live_catalog(state)
        task = tasks[target]
        if task["status"] not in {"planning", "queued"}:
            fail("only a planned or queued task may reserve a slot")
        if any(
            tasks[dependency]["status"] != "done" for dependency in task["dependencies"]
        ):
            fail("cannot reserve a task slot before its dependencies finish")
        if task["runtime"].get("productive_prompt"):
            fail("productive work already reached this task")
        task["attempts"] += 1
        task["status"] = "launching"
        task["phase"] = TASK_PHASES["launching"]
        task["runtime"].update(
            {"status": "reserved", "reserved_by": actor, "reserved_at": now()}
        )
        state["run"]["active_agent_slots"].append(target)

    elif event_type == "record-runtime":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target == actor
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail(
                "only the direct parent or recorded root recovery may update task runtime"
            )
        if tasks[target]["status"] in SETTLED:
            fail("settled task runtime provenance is immutable")
        allowed = {
            "agent_id",
            "agent_instance_id",
            "launch_intent_id",
            "pane_id",
            "tab_id",
            "status",
            "output_path",
            "output_digest",
            "deadline_at",
            "launched_provider",
            "launched_model_id",
            "launched_thinking_level",
        }
        updates = event.get("updates")
        if not isinstance(updates, dict) or set(updates) - allowed:
            fail("record-runtime contains unsupported fields")
        runtime = tasks[target]["runtime"]
        if (
            runtime.get("agent_instance_id")
            and "agent_instance_id" in updates
            and updates["agent_instance_id"] != runtime["agent_instance_id"]
        ):
            fail("agent_instance_id is immutable for an attempt")
        for field in (
            "launched_provider",
            "launched_model_id",
            "launched_thinking_level",
            "deadline_at",
            "launch_intent_id",
        ):
            if (
                runtime.get(field)
                and field in updates
                and updates[field] != runtime[field]
            ):
                fail(f"{field} is immutable for an attempt")
        if "status" in updates:
            if updates["status"] not in RUNTIME_STATUSES:
                fail("record-runtime has an invalid runtime status")
            current_runtime_status = runtime.get("status")
            if (
                updates["status"] != current_runtime_status
                and updates["status"] not in RUNTIME_TRANSITIONS[current_runtime_status]
            ):
                fail(
                    f"invalid runtime transition: {current_runtime_status} -> {updates['status']}"
                )
        updates = copy.deepcopy(updates)
        if "output_path" in updates:
            updates["output_path"] = normalize_output_path(
                state, updates["output_path"], "runtime output_path"
            )
        candidate = {**runtime, **updates}
        if updates.get("status") == "starting":
            require_live_catalog(state)
        if candidate.get("status") in {"starting", "working", "blocked", "settled"}:
            active_model = tasks[target].get("active_model") or {}
            launch_intent_id = candidate.get("launch_intent_id")
            launch_intent = next(
                (
                    item
                    for owner in tasks.values()
                    for item in owner.get("runtime_intents", [])
                    if item.get("id") == launch_intent_id
                ),
                None,
            )
            current_use = {"task_id": target, "attempt": tasks[target]["attempts"]}
            if (
                not isinstance(launch_intent, dict)
                or launch_intent.get("status") != "bound"
                or launch_intent.get("kind") != "agent"
                or launch_intent.get("target_task_id") != target
                or launch_intent.get("used_by_attempt")
                not in {None, json.dumps(current_use, sort_keys=True)}
            ):
                fail(
                    "runtime start requires an unused bound agent intent for this task attempt"
                )
            launch_intent["used_by_attempt"] = json.dumps(current_use, sort_keys=True)
            deadline = parse_time(candidate.get("deadline_at"), "runtime deadline")
            current_time = datetime.now(timezone.utc)
            if runtime.get("status") in {"not-started", "reserved"} and (
                deadline <= current_time or deadline > current_time + timedelta(hours=3)
            ):
                fail(
                    "runtime deadline must be future and no more than three hours away"
                )
            if candidate.get("status") == "settled" and deadline <= current_time:
                fail(
                    "overdue runtime cannot settle successfully; use timeout cancellation"
                )
            if candidate.get("launched_provider") != active_model.get(
                "provider"
            ) or candidate.get("launched_model_id") != active_model.get("model_id"):
                fail(
                    "launched runtime model does not match the recorded model selection"
                )
            if catalog_bound and candidate.get(
                "launched_thinking_level"
            ) != active_model.get("thinking_level"):
                fail(
                    "launched runtime thinking level does not match the recorded model selection"
                )
        runtime.update(updates)

    elif event_type == "record-launch-verification":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target == actor
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail(
                "only the direct parent or recorded root recovery may verify a task launch"
            )
        task = tasks[target]
        runtime = task["runtime"]
        if (
            task["status"] in SETTLED
            or runtime.get("status") != "starting"
            or runtime.get("productive_prompt")
        ):
            fail(
                "launch verification must occur while an unprompted runtime is starting"
            )
        if runtime.get("launch_verification") is not None:
            fail("launch verification is immutable for an attempt")
        runtime["launch_verification"] = validate_launch_verification_artifact(
            state,
            task,
            event.get("artifact"),
        )
        runtime["launch_verified_at"] = now()

    elif event_type == "record-productive-prompt":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target == actor
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail("only the direct parent or recorded root recovery may record a prompt")
        runtime = tasks[target]["runtime"]
        if runtime.get("status") != "working" or runtime.get("productive_prompt"):
            fail("productive prompt requires a working runtime and is write-once")
        if runtime.get("launch_verification") is None:
            fail("productive prompt requires a verified model-routed launch")
        if not nonempty(event.get("evidence")):
            fail("productive prompt requires dispatch evidence")
        runtime.update(
            {
                "productive_prompt": True,
                "prompt_evidence": event["evidence"],
                "prompted_at": now(),
            }
        )

    elif event_type == "record-usable-contribution":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail("only the direct parent or recorded root recovery may record contribution")
        runtime = tasks[target]["runtime"]
        if runtime.get("status") not in {"working", "blocked", "settled", "stopped"}:
            fail("usable contribution requires a started runtime")
        if runtime.get("usable_contribution"):
            fail("usable contribution evidence is write-once")
        if not nonempty(event.get("evidence")):
            fail("usable contribution requires evidence")
        runtime["usable_contribution"] = True
        runtime["contribution_evidence"] = event["evidence"]
        runtime["contributed_at"] = now()

    elif event_type == "release-slot":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail(
                "only the direct parent or recorded root recovery may release this task slot"
            )
        runtime_status = tasks[target]["runtime"].get("status")
        if runtime_status not in {"settled", "stopped", "cancelled"}:
            fail("record confirmed runtime settlement before releasing a slot")
        if target in state["run"]["active_agent_slots"]:
            state["run"]["active_agent_slots"].remove(target)
        tasks[target]["runtime"]["released_at"] = now()

    elif event_type == "fail-launch":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail(
                "only the direct parent or recorded root recovery may fail a child launch"
            )
        task = tasks[target]
        if (
            task["status"] not in {"launching", "blocked"}
            or task["runtime"].get("status") not in {"stopped", "settled"}
        ):
            fail("failed attempt requires confirmed stopped runtime state")
        linked_resources = failed_attempt_resources(tasks, target, task.get("attempts"))
        if linked_resources and any(resource.get("status") != "closed" for resource in linked_resources):
            fail("close every failed-attempt runtime resource before releasing its slot")
        if target in state["run"]["active_agent_slots"]:
            state["run"]["active_agent_slots"].remove(target)
        task["status"] = "blocked"
        task["phase"] = TASK_PHASES["blocked"]
        task["runtime"]["released_at"] = now()
        task["result"]["blockers"] = [
            event.get("reason") or "Agent launch failed before productive work."
        ]

    elif event_type == "prepare-fallback":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail("only the direct parent or recorded root recovery may prepare fallback")
        task = tasks[target]
        if (
            task["status"] != "blocked"
            or task["attempts"] < 1
            or task["runtime"].get("status") not in {"stopped", "settled"}
            or task["runtime"].get("usable_contribution", False)
        ):
            fail("fallback requires a stopped blocked task without usable contribution")
        result_state = task.get("result") or {}
        if (
            result_state.get("summary") is not None
            or result_state.get("files_changed")
            or result_state.get("checks")
            or result_state.get("evidence")
        ):
            fail("fallback cannot replace a task that recorded a usable contribution")
        if any(
            resource.get("status") != "closed"
            for resource in failed_attempt_resources(tasks, target, task.get("attempts"))
        ):
            fail("fallback requires every runtime resource for the failed attempt to be closed")
        selection = validate_model_selection(
            event.get("selection"), task["task_class"], require_thinking=catalog_bound
        )
        resolution = validate_resolution_artifact(
            state, event.get("resolution_artifact"), selection
        )
        failure_ref, cleanup_ref = validate_fallback_evidence(
            state, task, resolution
        )
        task["runtime_history"].append(
            {
                "attempt": task["attempts"],
                "model_selection": copy.deepcopy(task["model_selection"]),
                "model_resolution": copy.deepcopy(task["model_resolution"]),
                "runtime": copy.deepcopy(task["runtime"]),
                "failure_evidence": failure_ref,
                "cleanup_evidence": cleanup_ref,
            }
        )
        task["model_selection"] = selection
        task["model_resolution"] = resolution
        task["active_resolution"] = copy.deepcopy(resolution)
        task["active_model"] = {
            "provider": selection["provider"],
            "model_id": selection["model_id"],
            "thinking_level": selection_thinking_level(selection),
            "source": "fallback",
        }
        if target in state["run"]["active_agent_slots"]:
            fail("failed task still owns an active agent slot")
        if len(state["run"]["active_agent_slots"]) >= limits["max_active_agents"]:
            fail("no root-wide agent slot is available for fallback")
        task["attempts"] += 1
        task["runtime"] = {
            "agent_id": None,
            "agent_instance_id": None,
            "pane_id": None,
            "productive_prompt": False,
            "usable_contribution": False,
            "status": "reserved",
            "reserved_by": actor,
            "reserved_at": now(),
        }
        task["status"] = "launching"
        task["phase"] = TASK_PHASES["launching"]
        task["result"]["blockers"] = []
        state["run"]["active_agent_slots"].append(target)

    elif event_type == "add-runtime-intent":
        intent = event.get("intent")
        target_task_id = (
            intent.get("target_task_id") if isinstance(intent, dict) else None
        )
        if (
            not isinstance(intent, dict)
            or not nonempty(intent.get("id"))
            or intent.get("kind") not in {"tab", "pane", "agent"}
            or not nonempty(intent.get("name"))
            or not nonempty(intent.get("response_id_path"))
            or not isinstance(target_task_id, str)
            or target_task_id not in tasks
        ):
            fail(
                "runtime intent requires id, kind, unique name, output_path, and target task"
            )
        if not tasks[actor].get("allow_subagents"):
            fail("leaf tasks cannot create runtime intents")
        if intent["kind"] == "tab":
            if target_task_id != actor:
                fail("a tab intent belongs to the delegating task")
        elif tasks[target_task_id].get("parent_id") != actor:
            fail("pane and agent intents must target a direct child")
        intent = copy.deepcopy(intent)
        intent["output_path"] = normalize_output_path(
            state, intent.get("output_path"), "runtime intent output_path"
        )
        existing_intents = [
            item for task in tasks.values() for item in task.get("runtime_intents", [])
        ]
        if any(intent["id"] == item.get("id") for item in existing_intents):
            fail("runtime intent ID must be unique")
        if any(intent["name"] == item.get("name") for item in existing_intents):
            fail("runtime intent name must be unique")
        if any(
            intent["output_path"] == item.get("output_path")
            for item in existing_intents
        ):
            fail("runtime intent output_path must be unique")
        attempt = tasks[target_task_id]["attempts"]
        if intent["kind"] == "agent" and any(
            item.get("kind") == "agent"
            and item.get("target_task_id") == target_task_id
            and item.get("attempt") == attempt
            for item in existing_intents
        ):
            fail("each task attempt may have exactly one agent launch intent")
        tasks[actor]["runtime_intents"].append(
            {**intent, "attempt": attempt, "status": "planned", "created_at": now()}
        )

    elif event_type == "record-pane-readiness":
        target = event.get("task_id", actor)
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or (target != actor and not root_recovery)
        ):
            fail("only the intent owner or recorded root recovery may record readiness")
        owner = tasks[target]
        agent_intent = next(
            (item for item in owner["runtime_intents"] if item.get("id") == event.get("intent_id")),
            None,
        )
        pane_intent = next(
            (item for item in owner["runtime_intents"] if item.get("id") == event.get("pane_intent_id")),
            None,
        )
        if (
            agent_intent is None
            or agent_intent.get("kind") != "agent"
            or agent_intent.get("status") != "planned"
            or pane_intent is None
            or pane_intent.get("kind") != "pane"
            or pane_intent.get("status") != "bound"
            or pane_intent.get("resource_id") != event.get("pane_id")
            or pane_intent.get("target_task_id") != agent_intent.get("target_task_id")
        ):
            fail("readiness requires a planned agent intent and its exact bound pane intent")
        created_at = parse_time(pane_intent.get("created_at"), "pane intent created_at")
        deadline_value = event.get("deadline_at")
        deadline_at = parse_time(deadline_value, "pane readiness deadline_at")
        overflow_sentinel = created_at == deadline_at == MAX_UTC_TIMESTAMP
        if not valid_readiness_deadline(created_at, deadline_at):
            fail("pane readiness deadline must stay within 300 seconds of the pre-create intent")
        snapshot_path, snapshot_digest, snapshot_payload = read_run_artifact(
            state, event.get("snapshot_artifact"), "pane readiness snapshot"
        )
        class_path, class_digest, class_payload = read_run_artifact(
            state, event.get("classification_artifact"), "pane readiness classification"
        )
        classification = event.get("classification")
        if overflow_sentinel and (
            classification != "ambiguous"
            or class_payload.get("reason") != READINESS_OVERFLOW_REASON
        ):
            fail("maximum timestamp readiness requires a terminal overflow ambiguity proof")
        if (
            classification not in {"ready", "busy", "expired", "ambiguous"}
            or class_payload.get("classification") != classification
            or class_payload.get("expectedPane") != event.get("pane_id")
            or class_payload.get("createdAt") != pane_intent.get("created_at")
            or class_payload.get("deadlineAt") != deadline_value
            or extract_json_path(snapshot_payload, "result.process_info.pane_id") != event.get("pane_id")
        ):
            fail("pane readiness evidence does not bind the intent, pane, deadline, and classification")
        validate_readiness_probe_evidence(
            snapshot_payload,
            class_payload,
            classification,
            event["pane_id"],
            pane_intent["created_at"],
            deadline_value,
        )
        readiness = agent_intent.get("readiness")
        if readiness is None:
            readiness = {
                "pane_intent_id": pane_intent["id"],
                "pane_id": event["pane_id"],
                "created_at": pane_intent["created_at"],
                "deadline_at": deadline_value,
                "busy_start_count": 0,
                "busy_start_artifact": None,
                "probes": [],
            }
            agent_intent["readiness"] = readiness
        elif (
            readiness.get("pane_intent_id") != pane_intent["id"]
            or readiness.get("pane_id") != event["pane_id"]
            or readiness.get("created_at") != pane_intent["created_at"]
            or readiness.get("deadline_at") != deadline_value
        ):
            fail("pane readiness identity or original deadline changed")
        previous = readiness["probes"][-1] if readiness["probes"] else None
        if previous and previous.get("classification") in {"ready", "expired", "ambiguous"}:
            fail("pane readiness cannot be rechecked after a terminal proof")
        if previous and classification != "ambiguous":
            _, _, previous_snapshot_payload = read_run_artifact(
                state, previous["snapshot"], "previous pane readiness snapshot"
            )
            _, _, previous_class_payload = read_run_artifact(
                state, previous["classification_artifact"], "previous pane readiness classification"
            )
            if parse_time(class_payload.get("observedAt"), "readiness classification observedAt") < parse_time(
                previous_class_payload.get("observedAt"), "previous readiness classification observedAt"
            ):
                fail("pane readiness observation time moved backward")
            validate_readiness_probe_transition(previous_snapshot_payload, snapshot_payload)
        current_time = datetime.now(timezone.utc)
        if current_time < created_at:
            fail("pane readiness cannot be recorded before pane creation")
        if event.get("busy_start_artifact") is not None:
            fail("an agent_pane_busy response cannot reopen completed readiness")
        readiness["probes"].append(
            {
                "classification": classification,
                "snapshot": {"path": snapshot_path, "digest": snapshot_digest},
                "classification_artifact": {"path": class_path, "digest": class_digest},
                "recorded_at": now(),
            }
        )
        if len(readiness["probes"]) > 32:
            fail("pane readiness exceeded the bounded probe limit")

    elif event_type == "bind-runtime-intent":
        target = event.get("task_id", actor)
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or (target != actor and not root_recovery)
        ):
            fail("only the intent owner or recorded root recovery may bind it")
        intent = next(
            (
                item
                for item in tasks[target]["runtime_intents"]
                if item.get("id") == event.get("intent_id")
            ),
            None,
        )
        resource = event.get("resource")
        if intent is None or intent.get("status") != "planned":
            fail("runtime intent is missing or already settled")
        if (
            not isinstance(resource, dict)
            or resource.get("kind") != intent.get("kind")
            or not nonempty(resource.get("id"))
        ):
            fail("bound resource does not match the intent")
        output_digest = event.get("output_digest")
        normalized_output = normalize_output_path(
            state, intent["output_path"], "runtime response output_path"
        )
        output_path = state_directory(state) / normalized_output
        if (
            not valid_hash(output_digest)
            or output_path.is_symlink()
            or not output_path.is_file()
            or file_digest(output_path) != output_digest
        ):
            fail("runtime response artifact is missing or its digest does not match")
        try:
            response = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            fail(f"runtime response artifact is not valid JSON: {error}")
        if extract_json_path(response, intent["response_id_path"]) != resource["id"]:
            fail("bound resource ID does not match the recorded runtime response")
        if any(
            resource["id"] == item.get("id")
            for task in tasks.values()
            for item in task.get("runtime_resources", [])
        ):
            fail("runtime resource ID must be unique across the run")
        resource = copy.deepcopy(resource)
        if intent.get("kind") in {"pane", "agent"}:
            if intent["kind"] == "agent":
                parent_tab_id = extract_json_path(response, "result.agent.tab_id")
            elif response.get("id") == "cli:tab:create":
                parent_tab_id = extract_json_path(response, "result.root_pane.tab_id")
            else:
                parent_tab_id = extract_json_path(response, "result.pane.tab_id")
            if not nonempty(parent_tab_id) or not any(
                item.get("kind") == "tab" and item.get("id") == parent_tab_id and item.get("status") == "live"
                for task in tasks.values()
                for item in task.get("runtime_resources", [])
            ):
                fail("pane and agent resources require an exact owned parent tab")
            resource["parent_tab_id"] = parent_tab_id
        if intent.get("kind") == "agent":
            readiness = intent.get("readiness")
            ready_pane_resource = next(
                (
                    item
                    for task in tasks.values()
                    for item in task.get("runtime_resources", [])
                    if item.get("kind") == "pane" and item.get("id") == (readiness or {}).get("pane_id")
                ),
                None,
            )
            if (
                not isinstance(readiness, dict)
                or readiness["probes"][-1].get("classification") != "ready"
                or extract_json_path(response, "result.agent.pane_id") != readiness.get("pane_id")
                or ready_pane_resource is None
                or ready_pane_resource.get("status") != "live"
                or ready_pane_resource.get("parent_tab_id") != resource.get("parent_tab_id")
                or readiness.get("busy_start_count", 0) != 0
            ):
                fail("agent launch binding requires a current ready pane and its exact live parent tab")
        intent.update(
            {
                "status": "bound",
                "bound_at": now(),
                "resource_id": resource["id"],
                "output_digest": output_digest,
            }
        )
        tasks[target]["runtime_resources"].append(
            {
                **resource,
                "status": "live",
                "created_at": now(),
                "intent_id": intent["id"],
            }
        )

    elif event_type == "fail-runtime-intent":
        target = event.get("task_id", actor)
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or (target != actor and not root_recovery)
        ):
            fail("only the intent owner or recorded root recovery may fail it")
        intent = next(
            (
                item
                for item in tasks[target]["runtime_intents"]
                if item.get("id") == event.get("intent_id")
            ),
            None,
        )
        if (
            intent is None
            or intent.get("status") != "planned"
            or not nonempty(event.get("reason"))
        ):
            fail("planned runtime intent and failure reason are required")
        intent.update(
            {"status": "failed", "failed_at": now(), "reason": event["reason"]}
        )

    elif event_type == "add-runtime-resource":
        fail("record and bind a runtime intent instead of adding a resource directly")

    elif event_type == "settle-runtime-resource":
        target = event.get("task_id", actor)
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        cancellation_recovery = tasks.get(target, {}).get(
            "status"
        ) == "cancelling" and (
            tasks[target].get("parent_id") == actor or actor == root_id
        )
        if (
            not isinstance(target, str)
            or target not in tasks
            or (target != actor and not root_recovery and not cancellation_recovery)
        ):
            fail("only the resource owner or recorded recovery may settle it")
        if tasks[target]["status"] in SETTLED:
            fail("settled task resources are immutable")
        resource_id = event.get("resource_id")
        resource = next(
            (
                item
                for item in tasks[target]["runtime_resources"]
                if item.get("id") == resource_id
            ),
            None,
        )
        if resource is None:
            fail("unknown run-owned runtime resource")
        if resource.get("status") != "live":
            fail("settled runtime resources are immutable")
        status = event.get("status", "closed")
        reason = event.get("reason")
        if status not in {"closed", "preserved"}:
            fail("resource settlement status must be closed or preserved")
        if status == "preserved" and not nonempty(reason):
            fail("preserved resources require a blocker reason")
        closure_artifact = event.get("closure_artifact")
        closure_digest = event.get("closure_digest")
        if status == "closed":
            normalized = normalize_output_path(
                state, closure_artifact, "resource closure artifact"
            )
            candidate = state_directory(state) / normalized
            if (
                not valid_hash(closure_digest)
                or candidate.is_symlink()
                or not candidate.is_file()
                or file_digest(candidate) != closure_digest
            ):
                fail("closed resources require a verified closure response artifact")
            try:
                closure_response = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                fail(f"resource closure response is invalid JSON: {error}")
            expected_close = (
                "cli:tab:close" if resource.get("kind") == "tab" else "cli:pane:close"
            )
            cascade_close = False
            if (
                resource.get("kind") in {"pane", "agent"}
                and closure_response.get("id") == "cli:tab:close"
                and reason == "cascade-deleted-with-owned-tab"
                and nonempty(resource.get("parent_tab_id"))
            ):
                parent_tab = next(
                    (
                        item
                        for task in tasks.values()
                        for item in task.get("runtime_resources", [])
                        if item.get("kind") == "tab" and item.get("id") == resource["parent_tab_id"]
                    ),
                    None,
                )
                cascade_close = bool(
                    parent_tab
                    and parent_tab.get("status") == "closed"
                    and parent_tab.get("closure_digest") == closure_digest
                )
            if (
                (closure_response.get("id") != expected_close and not cascade_close)
                or (closure_response.get("result") or {}).get("type") != "ok"
            ):
                fail("resource closure artifact is not a successful matching Herdr close")
            closure_artifact = normalized
        resource.update(
            {
                "status": status,
                "settled_at": now(),
                "reason": reason,
                "closure_artifact": closure_artifact,
                "closure_digest": closure_digest,
            }
        )

    elif event_type == "record-result":
        if tasks[actor]["status"] in SETTLED:
            fail("cannot change the result of a settled task")
        value = event.get("result")
        if not isinstance(value, dict):
            fail("result must be an object")
        allowed = {
            "summary",
            "files_changed",
            "checks",
            "evidence",
            "blockers",
            "cancellation",
        }
        if set(value) - allowed:
            fail("record-result contains unsupported fields")
        for key in ("files_changed", "checks", "evidence", "blockers"):
            if key in value and not isinstance(value[key], list):
                fail(f"result.{key} must be a list")
        value = copy.deepcopy(value)
        if "files_changed" in value:
            value["files_changed"] = validate_repo_files(
                value["files_changed"], "result.files_changed"
            )
        if actor == root_id and any(
            value.get(key) for key in ("files_changed", "checks", "evidence")
        ):
            invalidate_review(state["integration"])
        tasks[actor]["result"].update(value)
        if any(
            value.get(key)
            for key in ("summary", "files_changed", "checks", "evidence")
        ):
            tasks[actor]["runtime"]["usable_contribution"] = True

    elif event_type == "accept-task":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail(
                "only the direct parent or recorded root recovery may accept this task"
            )
        task = tasks[target]
        if task["status"] not in {"working", "waiting", "integrating"}:
            fail("task is not in a successful state for parent acceptance")
        runtime_status = task["runtime"].get("status")
        if (
            runtime_status != "settled"
            or not task["runtime"].get("productive_prompt")
            or not task["runtime"].get("usable_contribution", False)
            or not nonempty(task["runtime"].get("agent_instance_id"))
            or not nonempty(task["runtime"].get("launch_intent_id"))
            or not nonempty(task["runtime"].get("launched_provider"))
            or not nonempty(task["runtime"].get("launched_model_id"))
        ):
            fail(
                "acceptance requires a productive settled runtime with launch provenance"
            )
        if catalog_bound and not nonempty(
            task["runtime"].get("launched_thinking_level")
        ):
            fail("acceptance requires launched thinking provenance")
        verify_task_output(state, task["runtime"])
        if not nonempty(event.get("verification_evidence")):
            fail("parent acceptance requires runtime verification evidence")
        if any(
            (todo["required"] and todo["status"] != "done")
            or (not todo["required"] and todo["status"] not in SETTLED)
            for todo in task["todos"]
        ):
            fail("cannot accept a task with incomplete required todos")
        if any(tasks[child]["status"] not in SETTLED for child in task["children"]):
            fail("cannot accept a task with unsettled children")
        if not nonempty(task["result"].get("summary")) or task["result"].get(
            "blockers"
        ):
            fail("cannot accept a task without a successful blocker-free result")
        if any(item.get("status") != "closed" for item in task["runtime_resources"]):
            fail("cannot accept a task until every runtime resource is closed")
        task["runtime"]["acceptance_evidence"] = event["verification_evidence"]
        task["runtime"]["released_at"] = now()
        if target in state["run"]["active_agent_slots"]:
            state["run"]["active_agent_slots"].remove(target)
        task["status"] = "done"
        task["phase"] = TASK_PHASES["done"]

    elif event_type == "set-task-status":
        status = event.get("status")
        if status not in TASK_STATUSES or status in {"done", "cancelled", "cancelling"}:
            fail("use acceptance or cancellation events for settled states")
        task = tasks[actor]
        current = task["status"]
        if (
            actor != root_id
            and status == "working"
            and (
                task["runtime"].get("status") != "working"
                or not task["runtime"].get("productive_prompt")
            )
        ):
            fail("child task cannot work before a recorded productive prompt")
        if status == current:
            result["unchanged"] = True
        elif status not in TASK_TRANSITIONS[current]:
            fail(f"invalid task transition: {current} -> {status}")
        task["status"] = status
        task["phase"] = TASK_PHASES[status]

    elif event_type == "cancel-subtree":
        target = event.get("task_id")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target in {root_id, actor}
            or (tasks[target].get("parent_id") != actor and actor != root_id)
        ):
            fail("only the direct parent or root recovery may cancel a subtree")
        reason = event.get("reason")
        disposition = event.get("parent_disposition")
        if not nonempty(reason) or not nonempty(disposition):
            fail("cancellation requires a reason and parent disposition")
        for task_id in reversed([target, *descendants(state, target)]):
            task = tasks[task_id]
            if task["status"] in SETTLED:
                continue
            if (
                "cancelling" not in TASK_TRANSITIONS[task["status"]]
                and task["status"] != "cancelling"
            ):
                fail(f"task {task_id} cannot enter cancellation from {task['status']}")
            task["status"] = "cancelling"
            task["phase"] = TASK_PHASES["cancelling"]
            task["result"]["cancellation"] = {
                "reason": reason,
                "parent_disposition": disposition,
                "requested_at": now(),
            }
            if task["runtime"]["status"] not in {
                "not-started",
                "settled",
                "stopped",
                "cancelled",
            }:
                current_runtime = task["runtime"]["status"]
                if "cancellation-requested" not in RUNTIME_TRANSITIONS[current_runtime]:
                    fail(f"runtime cannot request cancellation from {current_runtime}")
                task["runtime"]["status"] = "cancellation-requested"

    elif event_type == "finalize-cancellation":
        target = event.get("task_id")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target == actor
            or (tasks[target].get("parent_id") != actor and actor != root_id)
        ):
            fail("only the direct parent or root recovery may finalize cancellation")
        task = tasks[target]
        if task["status"] != "cancelling":
            fail("task is not awaiting cancellation finalization")
        if any(tasks[child]["status"] not in SETTLED for child in task["children"]):
            fail("cancel descendants before finalizing their parent")
        if task["runtime"]["status"] not in {
            "not-started",
            "settled",
            "stopped",
            "cancelled",
        }:
            fail("runtime shutdown is not confirmed")
        if any(item.get("status") != "closed" for item in task["runtime_resources"]):
            fail("runtime resources must be closed before cancellation finalization")
        if target in state["run"]["active_agent_slots"]:
            state["run"]["active_agent_slots"].remove(target)
        if (
            "cancelled" not in RUNTIME_TRANSITIONS[task["runtime"]["status"]]
            and task["runtime"]["status"] != "cancelled"
        ):
            fail("runtime cannot finalize cancellation from its current state")
        task["status"] = "cancelled"
        task["phase"] = TASK_PHASES["cancelled"]
        task["runtime"]["status"] = "cancelled"

    elif event_type == "cancel-run":
        if actor != root_id:
            fail("only the root task may cancel the run")
        reason = event.get("reason")
        if not nonempty(reason):
            fail("run cancellation requires a reason")
        if any(
            task_id != root_id and task["status"] not in SETTLED
            for task_id, task in tasks.items()
        ):
            fail("settle every descendant before cancelling the run")
        if (
            state["run"]["active_agent_slots"]
            or any(
                item.get("status") != "closed"
                for task in tasks.values()
                for item in task["runtime_resources"]
            )
            or any(
                item.get("status") == "open"
                for item in state["integration"].get("review_resources", [])
            )
        ):
            fail("settle slots and close resources before cancelling the run")
        tasks[root_id]["status"] = "cancelled"
        tasks[root_id]["phase"] = TASK_PHASES["cancelled"]
        tasks[root_id]["result"]["cancellation"] = {
            "reason": reason,
            "parent_disposition": "The root run was intentionally cancelled.",
            "requested_at": now(),
        }
        state["run"]["status"] = "cancelled"
        state["run"]["phase"] = "blocked"
        state["run"]["stop_reason"] = reason

    elif event_type == "update-integration":
        if actor != root_id:
            fail("only the root task may update integration state")
        updates = event.get("updates")
        cleanup_only = (
            state["run"].get("reconciliation_required")
            or state["run"]["status"] == "blocked"
        )
        if cleanup_only and (
            not isinstance(updates, dict) or set(updates) != {"review_resources"}
        ):
            fail("recovery may update only review resource cleanup status")
        allowed = {
            "test_verdict",
            "skipped_reason",
            "test_evidence",
            "behavior_verdict",
            "behavior_reason",
            "behavior_eligibility",
            "behavior_evidence",
            "changed_files",
            "collisions",
            "review_verdict",
            "review_execution",
            "review_requirement",
            "review_wave",
            "review_perspectives",
            "review_resources",
            "review_findings",
            "combined_report_path",
            "finished_at",
        }
        if not isinstance(updates, dict) or set(updates) - allowed:
            fail("update-integration contains unsupported fields")
        updates = copy.deepcopy(updates)
        if "review_wave" in updates:
            supplied_wave = updates["review_wave"]
            if (
                isinstance(supplied_wave, bool)
                or not isinstance(supplied_wave, int)
                or supplied_wave < state["integration"].get("review_wave", 0)
            ):
                fail("review wave numbers cannot decrease")
        if "review_resources" in updates:
            validate_review_resource_update(
                state["integration"].get("review_resources", []),
                updates["review_resources"],
                cleanup_only=cleanup_only,
            )
        if "changed_files" in updates:
            updates["changed_files"] = validate_repo_files(
                updates["changed_files"], "integration.changed_files"
            )
        substantive = {
            "test_verdict",
            "skipped_reason",
            "test_evidence",
            "behavior_verdict",
            "behavior_reason",
            "behavior_eligibility",
            "behavior_evidence",
            "changed_files",
            "collisions",
        }
        review_update = {
            "review_verdict",
            "review_execution",
            "review_requirement",
            "review_wave",
            "review_perspectives",
            "review_resources",
            "combined_report_path",
        }
        recorded_review = state["integration"].get("review_wave", 0) > 0
        if recorded_review and set(updates) & substantive and set(updates) & review_update:
            fail("record rework evidence before recording a fresh review")
        if recorded_review and set(updates) & substantive:
            invalidate_review(state["integration"])
        state["integration"].update(updates)

    elif event_type == "complete-run":
        if actor != root_id:
            fail("only the root task may complete the run")
        task = tasks[root_id]
        if state["run"]["phase"] != "review":
            fail("the run must be in review before completion")
        if any(
            (todo["required"] and todo["status"] != "done")
            or (not todo["required"] and todo["status"] not in SETTLED)
            for todo in task["todos"]
        ):
            fail("root required todos are not done")
        if any(tasks[child]["status"] not in SETTLED for child in task["children"]):
            fail("root descendants are not settled")
        if not nonempty(task["result"].get("summary")) or task["result"].get("blockers"):
            fail("root result is missing or still blocked")
        if state["run"]["active_agent_slots"] or any(
            item.get("status") != "closed"
            for value in tasks.values()
            for item in value["runtime_resources"]
        ):
            fail("runtime slots remain or a runtime resource is not closed")
        validate_integration_ready(state)
        task["status"] = "done"
        task["phase"] = TASK_PHASES["done"]
        state["run"]["status"] = "complete"
        state["run"]["phase"] = "complete"
        state["integration"]["finished_at"] = now()

    else:
        fail(f"unsupported event type: {event_type!r}")

    tasks[actor]["updated_at"] = now()
    state["revision"] += 1
    state["updated_at"] = now()
    validate(state, state_path)
    return result


def initial_state(
    feature: str,
    lease_id: str,
    coordinator_instance_id: str,
    base_commit: str,
    repo_root: str,
) -> dict[str, Any]:
    root_event = {
        "title": "Coordinate the requested implementation",
        "outcome": "The requested behavior is implemented, integrated, verified, and reviewed with the execution mode recorded honestly.",
        "acceptance_criteria": [
            "All required todos and descendant tasks settle with current evidence."
        ],
        "expected_result": "An integrated change with current checks, behavior evidence, and review evidence.",
        "task_class": "coordination",
        "allow_subagents": True,
    }
    root = task_template("task-0001", None, "task-0001", 0, root_event)
    root_path = Path(repo_root).resolve()
    timestamp = now()
    return {
        "version": 4,
        "feature_name": feature,
        "revision": 0,
        "next_task_sequence": 2,
        "next_todo_sequence": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
        "run": {
            "status": "running",
            "phase": "bootstrap",
            "repo_root": str(root_path),
            "coordinator_instance_id": coordinator_instance_id,
            "coordinator_session_bound": True,
            "coordinator_instance_history": [],
            "coordinator_model": current_coordinator_model(coordinator_instance_id),
            "coordinator_model_history": [],
            "coordinator_lease": {"id": lease_id, "expires_at": future()},
            "reconciliation_required": False,
            "reconciliation_evidence": None,
            "user_goal": None,
            "root_task_id": "task-0001",
            "base_commit": base_commit,
            "initial_worktree": worktree_snapshot(root_path, base_commit),
            "limits": copy.deepcopy(HARD_LIMITS),
            "active_agent_slots": [],
            "model_catalog": None,
            "stop_reason": None,
        },
        "tasks": {"task-0001": root},
        "integration": {
            "test_verdict": "pending",
            "skipped_reason": None,
            "test_evidence": [],
            "behavior_verdict": "pending",
            "behavior_reason": None,
            "behavior_eligibility": None,
            "behavior_evidence": [],
            "changed_files": [],
            "collisions": [],
            "review_verdict": "pending",
            "review_execution": None,
            "review_requirement": None,
            "review_wave": 0,
            "minimum_review_wave": 0,
            "review_perspectives": {},
            "review_resources": [],
            "review_findings": [],
            "combined_report_path": None,
            "finished_at": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "events",
        help="list supported event names and root bootstrap examples without changing state",
    )

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("path", type=Path)
    init_parser.add_argument("--feature", required=True)
    init_parser.add_argument(
        "--lease-id", default=os.environ.get("IMPLEMENT_COORDINATOR_LEASE_ID")
    )
    init_parser.add_argument("--coordinator-instance-id", required=True)
    init_parser.add_argument("--base-commit", required=True)
    init_parser.add_argument("--repo-root", required=True)
    init_parser.add_argument("--canonical-path", required=True)

    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument("path", type=Path)
    resume_parser.add_argument("--feature", required=True)
    resume_parser.add_argument(
        "--lease-id", default=os.environ.get("IMPLEMENT_COORDINATOR_LEASE_ID")
    )
    resume_parser.add_argument(
        "--coordinator-instance-id", default=os.environ.get("PI_SESSION_FILE")
    )

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("path", type=Path)
    apply_parser.add_argument("--actor", required=True)
    apply_parser.add_argument(
        "--lease-id", default=os.environ.get("IMPLEMENT_COORDINATOR_LEASE_ID")
    )
    event_group = apply_parser.add_mutually_exclusive_group(required=True)
    event_group.add_argument("--event-json")
    event_group.add_argument("--event-file", type=Path)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("path", type=Path)

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("path", type=Path)
    show_parser.add_argument("--task")

    args = parser.parse_args()
    if args.command == "events":
        print(json.dumps(event_catalog(), indent=2, sort_keys=True))
        return

    path = Path(os.path.abspath(args.path))

    if args.command == "init":
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.feature or ""):
            fail("feature name must be lowercase kebab-case")
        if not nonempty(args.lease_id):
            fail("init requires coordinator lease environment")
        expected_canonical = (
            Path(args.repo_root).resolve()
            / "var"
            / args.feature
            / "implement"
            / "state.json"
        )
        if Path(args.canonical_path).resolve() != expected_canonical:
            fail("init canonical path does not match the feature state location")
        if path.exists():
            fail(f"state already exists: {path}")
        state = initial_state(
            args.feature,
            args.lease_id,
            args.coordinator_instance_id,
            args.base_commit,
            args.repo_root,
        )
        validate(state)
        save_atomic(path, state)
        print(json.dumps({"state": str(path), "root_task_id": "task-0001"}))
        return

    if args.command == "resume":
        caller_session = os.environ.get("PI_SESSION_FILE")
        if not nonempty(args.lease_id) or not nonempty(args.coordinator_instance_id):
            fail("resume requires coordinator lease and Pi session identity")
        if not nonempty(caller_session) or args.coordinator_instance_id != caller_session:
            fail("resume identity must match the calling Pi session")
        with LockedState(path) as state:
            validate(state, path)
            if state.get("feature_name") != args.feature:
                fail("feature name does not match")
            lease = state["run"]["coordinator_lease"]
            lease_expired = parse_time(
                lease["expires_at"], "coordinator lease expiry"
            ) <= datetime.now(timezone.utc)
            takeover = args.lease_id != lease["id"]
            if takeover and not lease_expired:
                fail("another coordinator lease is still active")
            if lease_expired and not takeover:
                fail("expired lease takeover requires a fresh coordinator lease ID")
            live_resources = [
                item["id"]
                for task in state["tasks"].values()
                for item in task["runtime_resources"]
                if item.get("status") == "live"
            ]
            planned_intents = [
                item["id"]
                for task in state["tasks"].values()
                for item in task.get("runtime_intents", [])
                if item.get("status") == "planned"
            ]
            open_review_resources = [
                item["id"]
                for item in state["integration"].get("review_resources", [])
                if item.get("status") == "open"
            ]
            reconciliation_required = bool(
                state["run"]["active_agent_slots"]
                or live_resources
                or planned_intents
                or open_review_resources
            )
            stored_instance = state["run"]["coordinator_instance_id"]
            legacy_session_binding = (
                not takeover
                and args.coordinator_instance_id != stored_instance
                and state["run"].get("coordinator_session_bound") is not True
            )
            if (
                not takeover
                and args.coordinator_instance_id != stored_instance
                and not legacy_session_binding
            ):
                fail("the active coordinator lease belongs to a different Pi session")
            if takeover or legacy_session_binding:
                state["run"].setdefault("coordinator_instance_history", []).append(
                    stored_instance
                )
                state["run"].setdefault("coordinator_model_history", []).append(
                    copy.deepcopy(state["run"]["coordinator_model"])
                )
                state["run"]["coordinator_instance_id"] = args.coordinator_instance_id
                state["run"]["coordinator_model"] = current_coordinator_model(
                    args.coordinator_instance_id
                )
            state["run"]["coordinator_session_bound"] = True
            state["run"]["reconciliation_required"] = reconciliation_required
            state["run"]["reconciliation_evidence"] = (
                None
                if reconciliation_required
                else "No live runtime state required reconciliation."
            )
            lease.update({"id": args.lease_id, "expires_at": future()})
            state["revision"] += 1
            state["updated_at"] = now()
            validate(state, path)
            save_atomic(path, state)
        print(
            json.dumps(
                {
                    "state": str(path),
                    "revision": state["revision"],
                    "status": state["run"]["status"],
                    "lease_id": args.lease_id,
                    "runtime_reconciliation_required": reconciliation_required,
                }
            )
        )
        return

    if args.command == "validate":
        state = load(path)
        validate(state, path)
        print(
            f"PASS: recursive implement state version 4 is valid at revision {state['revision']}"
        )
        return

    if args.command == "show":
        state = load(path)
        validate(state, path)
        value = state["tasks"].get(args.task) if args.task else state
        if value is None:
            fail(f"unknown task: {args.task}")
        print(json.dumps(value, indent=2, sort_keys=True))
        return

    if args.event_file:
        event = load(args.event_file)
    else:
        try:
            event = json.loads(args.event_json)
        except json.JSONDecodeError as error:
            fail(f"invalid event JSON: {error}")
    if not isinstance(event, dict):
        fail("event must be an object")
    with LockedState(path) as state:
        result = apply_event(state, path, args.actor, args.lease_id, event)
        save_atomic(path, state)
    print(json.dumps({**result, "revision": state["revision"]}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (TypeError, ValueError, KeyError, IndexError) as error:
        fail(f"malformed state or event: {error}")
