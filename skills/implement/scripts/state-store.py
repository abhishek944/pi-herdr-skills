#!/usr/bin/env python3
"""Atomic single-file state store for recursive implement runs."""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import posixpath
import re
import secrets
import subprocess
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
REVIEW_TIER_RANK = {"basic": 1, "standard": 2, "strong": 3}
REVIEW_TIERS = set(REVIEW_TIER_RANK)
RESOURCE_STATUSES = {"live", "closed", "preserved"}
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
    "max_retries_per_task": 0,
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


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


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


def verify_artifact_digests(state: dict[str, Any], digests: Any) -> None:
    if not isinstance(digests, dict) or not digests:
        fail("certification requires artifact digests")
    root = state_directory(state).resolve()
    identities = set()
    for relative, expected in digests.items():
        if not nonempty(relative) or not valid_hash(expected):
            fail("certification artifact digests are invalid")
        lexical = root / relative
        current = root
        for part in Path(relative).parts:
            current = current / part
            if current.is_symlink():
                fail("certification artifact paths cannot contain symbolic links")
        candidate = lexical.resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            fail("certification artifact escapes the run folder")
        if not candidate.is_file() or file_digest(candidate) != expected:
            fail(f"certification artifact is missing or stale: {relative}")
        identity = (candidate.stat().st_dev, candidate.stat().st_ino)
        if identity in identities:
            fail("certification artifacts must be distinct files")
        identities.add(identity)


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


def validate_final_contract(
    state: dict[str, Any], fingerprint: str, artifact_digests: dict[str, str]
) -> None:
    integration = state["integration"]
    for field in (
        "review_target_fingerprint",
        "review_wave_fingerprint",
        "test_target_fingerprint",
        "behavior_target_fingerprint",
        "evidence_target_fingerprint",
    ):
        if integration.get(field) != fingerprint:
            fail(f"{field} does not match the live fingerprint")
    if integration.get("test_verdict") == "skipped" and not nonempty(
        integration.get("skipped_reason")
    ):
        fail("skipped tests require a reason")
    if integration.get("test_verdict") == "pass":
        test_evidence = integration.get("test_evidence", [])
        if not test_evidence or any(
            not posixpath.normpath(item.get("artifact", "")).startswith("evidence/")
            or item.get("fingerprint") != fingerprint
            for item in test_evidence
        ):
            fail("passing tests require current digest-bound evidence-folder artifacts")
    if integration.get("behavior_verdict") == "not-applicable":
        if not nonempty(integration.get("behavior_reason")) or not isinstance(
            integration.get("behavior_eligibility"), dict
        ):
            fail("not-applicable behavior verification requires documented eligibility")
        allowed_extensions = {".md", ".txt", ".rst"}
        if not integration.get("changed_files") or any(
            Path(item).suffix.lower() not in allowed_extensions
            for item in integration["changed_files"]
        ):
            fail(
                "not-applicable behavior verification is limited to documentation-only changes"
            )
    if integration.get("behavior_verdict") == "user-pending":
        handoffs = [
            item
            for item in integration.get("behavior_evidence", [])
            if item.get("case_type") == "user-handoff"
        ]
        if (
            not nonempty(integration.get("behavior_reason"))
            or len(handoffs) != 1
            or handoffs[0].get("fingerprint") != fingerprint
        ):
            fail(
                "user-pending behavior verification requires one current manual-test handoff and a reason"
            )
    wave = integration.get("review_wave")
    if isinstance(wave, bool) or not isinstance(wave, int) or wave < 1:
        fail("review wave must be a positive integer")
    waves = integration.get("review_waves", [])
    if not waves or wave != waves[-1].get("wave"):
        fail("review_wave must be the newest appended wave")
    wave_record = next((item for item in waves if item.get("wave") == wave), None)
    if (
        not isinstance(wave_record, dict)
        or wave_record.get("fingerprint") != fingerprint
        or wave_record.get("status") != "complete"
    ):
        fail("current review wave is missing or stale")
    wave_started = parse_time(wave_record.get("started_at"), "review wave started_at")
    findings = integration.get("review_findings", [])
    structured_ids = {item["id"] for item in findings}
    report_ids = set()
    root = state_directory(state)
    perspectives = integration.get("review_perspectives", {})
    expected_review_paths = {
        "correctness_safety": f"reviews/wave-{wave}-correctness.md",
        "architecture_integration": f"reviews/wave-{wave}-architecture.md",
        "regression_fix_quality": f"reviews/wave-{wave}-regression.md",
    }
    for name in (
        "correctness_safety",
        "architecture_integration",
        "regression_fix_quality",
    ):
        item = perspectives.get(name) or {}
        if (
            item.get("status") != "complete"
            or not nonempty(item.get("agent_id"))
            or not nonempty(item.get("agent_instance_id"))
        ):
            fail(f"{name} reviewer provenance is incomplete")
        if parse_time(item.get("started_at"), f"{name} started_at") < wave_started:
            fail(f"{name} predates the current review wave")
        parse_time(item.get("deadline_at"), f"{name} deadline_at")
        relative = item.get("output_path")
        if relative != expected_review_paths[name]:
            fail(f"{name} report is outside its expected current-wave location")
        if relative not in artifact_digests:
            fail(f"{name} report digest is missing")
        text = (root / relative).read_text(encoding="utf-8")
        for marker in (
            f"Fingerprint: {fingerprint}",
            f"Review wave: {wave}",
            f"Reviewer: {item['agent_id']}",
        ):
            if marker not in text:
                fail(f"{name} report is missing marker: {marker}")
        line = next(
            (value for value in text.splitlines() if value.startswith("Finding IDs: ")),
            None,
        )
        if line is None:
            fail(f"{name} report is missing Finding IDs")
        raw = line.split(":", 1)[1].strip()
        if raw.lower() != "none":
            report_ids.update(
                value.strip() for value in raw.split(",") if value.strip()
            )
    if report_ids != structured_ids or any(
        item.get("status") == "open" for item in findings
    ):
        fail(
            "review report findings and structured findings do not match or remain open"
        )
    combined = integration.get("combined_report_path")
    if combined != f"reviews/wave-{wave}-combined.md":
        fail("combined review report is outside its expected current-wave location")
    if combined not in artifact_digests:
        fail("combined review report digest is missing")
    combined_text = (root / combined).read_text(encoding="utf-8")
    if (
        f"Fingerprint: {fingerprint}" not in combined_text
        or f"Review wave: {wave}" not in combined_text
    ):
        fail("combined review report markers are stale")
    expected_evidence = f"var/{state['feature_name']}/implement/evidence-index.md"
    if (
        integration.get("evidence_index") != expected_evidence
        or "evidence-index.md" not in artifact_digests
    ):
        fail("evidence index is missing or outside the run")


def live_review_fingerprint(state: dict[str, Any]) -> str:
    scope = state["integration"].get("review_scope") or {}
    script = (
        Path(__file__).resolve().parents[2]
        / "agent-review"
        / "scripts"
        / "review-fingerprint.sh"
    )
    command = [
        "bash",
        str(script),
        "--base",
        str(scope.get("base_sha")),
        "--target",
        str(scope.get("target_ref")),
        "--format",
        "json",
    ]
    for item in scope.get("paths") or []:
        command.extend(["--scope", item])
    try:
        return json.loads(
            subprocess.check_output(command, cwd=state["run"]["repo_root"], text=True)
        )["fingerprint"]
    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        KeyError,
        OSError,
    ) as error:
        fail(f"could not calculate live review fingerprint: {error}")


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
                or escalation.get("status") != "stronger"
            ):
                fail(
                    "review model selection requires canonical stronger reviewer_escalation"
                )
            if (
                escalation.get("rule")
                != "no-regression-in-model-or-thinking-and-at-least-one-strict"
            ):
                fail("review model selection uses an unsupported escalation rule")
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
        if (
            not isinstance(routing, dict)
            or set(routing) != {"reviewTier"}
            or routing.get("reviewTier") not in REVIEW_TIERS
        ):
            fail(
                f"{label}.routing must contain only a basic, standard, or strong reviewTier"
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
    return {"path": path, "digest": digest}


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
    return {"path": path, "digest": digest}


def argv_value(argv: Any, flag: str) -> str:
    if not isinstance(argv, list):
        fail("start response argv must be a list")
    positions = [index for index, value in enumerate(argv) if value == flag]
    if len(positions) != 1 or positions[0] + 1 >= len(argv):
        fail(f"start response must contain exactly one {flag}")
    return argv[positions[0] + 1]


def validate_review_perspective_proof(
    state: dict[str, Any], perspective: dict[str, Any]
) -> None:
    selection_artifact = perspective.get("resolution_artifact")
    _, selection_digest, resolution = read_run_artifact(
        state, selection_artifact, "review resolution artifact"
    )
    selection = validate_model_selection(
        resolution.get("stateSelection"), "review", require_thinking=True
    )
    if (
        validate_resolution_artifact(state, selection_artifact, selection)
        != selection_artifact
    ):
        fail("review resolution artifact is not normalized")
    expected = {
        "provider": selection["provider"],
        "model": selection["model_id"],
        "thinking": selection["thinking_level"],
    }
    if expected != {
        "provider": perspective.get("provider"),
        "model": perspective.get("model_id"),
        "thinking": perspective.get("thinking_level"),
    }:
        fail("review perspective model does not match its resolution")

    start_artifact = perspective.get("start_response_artifact")
    _, start_digest, start = read_run_artifact(
        state, start_artifact, "review start response artifact"
    )
    start_result = start.get("result") or {}
    start_agent = start_result.get("agent") or {}
    start_session = (start_agent.get("agent_session") or {}).get("value")
    argv = start_result.get("argv")
    if (
        start.get("id") != "cli:agent:start"
        or argv != ["pi", *(resolution.get("piArgs") or [])]
        or start_result.get("type") != "agent_started"
        or not isinstance(argv, list)
        or not argv
        or argv[0] != "pi"
        or start_agent.get("agent") != "pi"
        or start_agent.get("agent_status") != "idle"
        or start_agent.get("interactive_ready") is not True
        or start_agent.get("name") != perspective.get("agent_id")
        or start_session != perspective.get("agent_instance_id")
        or argv_value(argv, "--provider") != expected["provider"]
        or argv_value(argv, "--model") != expected["model"]
        or argv_value(argv, "--thinking") != expected["thinking"]
    ):
        fail(
            "review perspective start response does not prove the resolved Herdr Pi agent"
        )

    verification_artifact = perspective.get("verification_artifact")
    _, _, verification = read_run_artifact(
        state, verification_artifact, "review launch verification artifact"
    )
    verification_evidence = verification.get("evidence") or {}
    if (
        verification.get("verified") is not True
        or verification.get("expected") != expected
        or (verification_evidence.get("catalog") or {}).get("digest")
        != (state["run"].get("model_catalog") or {}).get("digest")
        or (verification_evidence.get("resolutionArtifact") or {}).get("digest")
        != selection_digest
        or (verification_evidence.get("startResponseArtifact") or {}).get("digest")
        != start_digest
        or verification_evidence.get("sessionIdentity")
        != perspective.get("agent_instance_id")
    ):
        fail(
            "review perspective launch verification does not match its preserved proof"
        )

    catalog_models = {
        (item["provider"], item["modelId"]): item
        for item in (state["run"].get("model_catalog") or {}).get("models", [])
    }
    selected_entry = catalog_models.get((selection["provider"], selection["model_id"]))
    if not isinstance(selected_entry, dict):
        fail("review perspective selected model is outside the bound catalog")
    baselines = selection["reviewer_escalation"]["baselines"]
    baseline_quality = 0
    baseline_thinking = 0
    for baseline in baselines:
        entry = catalog_models.get((baseline["provider"], baseline["model_id"]))
        if not isinstance(entry, dict):
            fail("review perspective baseline is outside the bound catalog")
        baseline_quality = max(
            baseline_quality, REVIEW_TIER_RANK[entry["routing"]["reviewTier"]]
        )
        baseline_thinking = max(
            baseline_thinking, PI_THINKING_RANK[baseline["thinking_level"]]
        )
    selected_quality = REVIEW_TIER_RANK[selected_entry["routing"]["reviewTier"]]
    selected_thinking = PI_THINKING_RANK[selection["thinking_level"]]
    if (
        selected_quality < baseline_quality
        or selected_thinking < baseline_thinking
        or (
            selected_quality == baseline_quality
            and selected_thinking == baseline_thinking
        )
    ):
        fail("review perspective is not strictly stronger than its baselines")

    contributors = [
        state["run"]["coordinator_model"],
        *state["run"].get("coordinator_model_history", []),
        *[
            task["model_selection"]
            for task in state["tasks"].values()
            if task.get("model_selection")
            and (
                task["runtime"].get("productive_prompt")
                or task["result"].get("files_changed")
            )
        ],
    ]
    for contributor in contributors:
        if not any(
            baseline["provider"] == contributor["provider"]
            and baseline["model_id"] == contributor["model_id"]
            and baseline["thinking_level"] == contributor["thinking_level"]
            for baseline in baselines
        ):
            fail("review perspective baselines omit an implementation contributor")


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
        "capability_hash": event.get("capability_hash"),
        "capability_hash_history": [],
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
    agent_intent_targets: set[str] = set()
    for task_id, task in tasks.items():
        if not TASK_ID_RE.fullmatch(task_id) or task.get("id") != task_id:
            fail(f"invalid task ID or key: {task_id}")
        if not valid_hash(task.get("capability_hash")):
            fail(f"task {task_id} has an invalid capability hash")
        if not isinstance(task.get("capability_hash_history"), list) or any(
            not valid_hash(item) for item in task["capability_hash_history"]
        ):
            fail(f"task {task_id} has invalid capability history")
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
        if (
            isinstance(attempts, bool)
            or not isinstance(attempts, int)
            or attempts not in {0, 1}
        ):
            fail(f"task {task_id} attempts must be 0 or 1")
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
            and attempts == 1
            and runtime.get("status") == "not-started"
        ):
            fail(f"task {task_id} consumed its launch attempt without runtime evidence")
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
        if task.get("runtime_history") != []:
            fail(
                f"task {task_id} runtime_history must remain empty because retries are disabled"
            )
        model = task.get("model_selection")
        if model is not None:
            validate_model_selection(
                model, task["task_class"], require_thinking=catalog_bound
            )
            if validate_resolution_artifact(
                state, task.get("model_resolution"), model
            ) != task.get("model_resolution"):
                fail(f"task {task_id} model resolution artifact is not normalized")
            active_model = task.get("active_model")
            if (
                not isinstance(active_model, dict)
                or not nonempty(active_model.get("provider"))
                or not nonempty(active_model.get("model_id"))
            ):
                fail(f"task {task_id} has invalid active_model")
            if catalog_bound and not nonempty(active_model.get("thinking_level")):
                fail(f"task {task_id} active_model lacks thinking provenance")
            if active_model.get("source") != "primary" or task.get(
                "active_resolution"
            ) != task.get("model_resolution"):
                fail(f"task {task_id} must use its original model resolution")
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
                    selected_quality = REVIEW_TIER_RANK[
                        selected_entry["routing"]["reviewTier"]
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
                    if not non_regressive or not strictly_higher:
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
                if target_task_id in agent_intent_targets:
                    fail(f"task {target_task_id} has more than one agent launch intent")
                agent_intent_targets.add(target_task_id)
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
    if integration.get("review_verdict") not in {"pending", "pass", "fail", "blocked"}:
        fail("integration.review_verdict is invalid")
    if integration.get("review_execution") not in {None, "independent"}:
        fail("integration.review_execution must be independent")
    if integration.get("review_scope") is not None and not isinstance(
        integration.get("review_scope"), dict
    ):
        fail("integration.review_scope must be an object")
    if not isinstance(integration.get("review_waves"), list) or any(
        not isinstance(item, dict) for item in integration["review_waves"]
    ):
        fail("integration.review_waves must be a list of objects")
    wave_numbers = [item.get("wave") for item in integration["review_waves"]]
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 1
        for item in wave_numbers
    ) or wave_numbers != sorted(set(wave_numbers)):
        fail("integration review waves must be unique and increasing")
    if not isinstance(integration.get("review_perspectives"), dict) or any(
        not isinstance(item, dict)
        for item in integration["review_perspectives"].values()
    ):
        fail("integration.review_perspectives must be an object of objects")
    changed_files = integration.get("changed_files")
    collisions = integration.get("collisions")
    validate_repo_files(changed_files, "integration.changed_files")
    if not isinstance(collisions, list):
        fail("integration.collisions must be a list")
    for collision in collisions:
        if not isinstance(collision, dict) or collision.get("status") not in {
            "open",
            "resolved",
        }:
            fail("each integration collision needs open or resolved status")
        if not isinstance(collision.get("tasks"), list) or not isinstance(
            collision.get("files"), list
        ):
            fail("collision entries require task and file lists")
        if collision.get("status") == "resolved" and (
            not nonempty(collision.get("resolution"))
            or not isinstance(collision.get("rerun_evidence"), list)
            or not collision["rerun_evidence"]
        ):
            fail("resolved collisions require a resolution and rerun evidence")
    test_evidence = integration.get("test_evidence")
    if not isinstance(test_evidence, list):
        fail("integration.test_evidence must be a list")
    for item in test_evidence:
        if (
            not isinstance(item, dict)
            or not nonempty(item.get("artifact"))
            or not nonempty(item.get("fingerprint"))
            or not nonempty(item.get("summary"))
        ):
            fail("test evidence entries require artifact, fingerprint, and summary")
    behavior_evidence = integration.get("behavior_evidence")
    if not isinstance(behavior_evidence, list):
        fail("integration.behavior_evidence must be a list")
    for item in behavior_evidence:
        if (
            not isinstance(item, dict)
            or item.get("case_type") not in {"happy", "error", "edge", "user-handoff"}
            or not nonempty(item.get("artifact"))
            or not nonempty(item.get("fingerprint"))
        ):
            fail(
                "behavior evidence entries require case_type, artifact, and fingerprint"
            )
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
        if finding.get("status") in {"resolved", "rejected"} and not nonempty(
            finding.get("resolution")
        ):
            fail(f"review finding {finding_id} requires a resolution")
    certification = integration.get("certification")
    if certification is not None:
        if (
            not isinstance(certification, dict)
            or not nonempty(certification.get("fingerprint"))
            or not isinstance(certification.get("revision"), int)
        ):
            fail("integration certification is invalid")
    if run.get("status") == "complete":
        if tasks[root_id]["status"] != "done":
            fail("a complete run requires a done root task")
        if (
            integration.get("review_verdict") != "pass"
            or integration.get("test_verdict") not in {"pass", "skipped"}
            or integration.get("behavior_verdict")
            not in {"pass", "user-pending", "not-applicable"}
        ):
            fail(
                "a complete run requires checks, a settled behavior handoff, and a passing review"
            )
        if (
            not isinstance(integration.get("certification"), dict)
            or integration["certification"].get("revision") != state["revision"] - 1
        ):
            fail("a complete run requires a current final integration certification")
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
    capability: str,
    lease_id: str | None,
    event: dict[str, Any],
) -> dict[str, Any]:
    validate(state, state_path)
    tasks = state["tasks"]
    if not isinstance(actor, str) or actor not in tasks:
        fail(f"unknown actor task: {actor!r}")
    if not nonempty(capability) or not secrets.compare_digest(
        tasks[actor]["capability_hash"], token_hash(capability)
    ):
        fail("task capability does not match the actor")
    event_type = event.get("type")
    if not nonempty(event_type):
        fail("event type must be a non-empty string")
    root_id = state["run"]["root_task_id"]
    if actor == root_id:
        lease = state["run"]["coordinator_lease"]
        if (
            not nonempty(lease_id)
            or lease_id != lease["id"]
            or parse_time(lease["expires_at"], "coordinator lease expiry")
            <= datetime.now(timezone.utc)
        ):
            fail("root operation requires an unexpired matching coordinator lease")
        lease["expires_at"] = future()
    if state["run"]["status"] in {"complete", "cancelled"}:
        fail("terminal runs cannot be mutated")
    recovery_events = {
        "record-runtime",
        "record-launch-verification",
        "bind-runtime-intent",
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
        fail("settled task capabilities cannot mutate state")
    limits = state["run"]["limits"]
    bound_catalog = state["run"].get("model_catalog") or {}
    catalog_bound = bound_catalog.get("schema_version") is not None
    result: dict[str, Any] = {"event": event_type}
    if event_type not in {"certify-integration", "complete-run"}:
        state["integration"]["certification"] = None

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
        if any(
            intent.get("status") == "planned"
            for task in tasks.values()
            for intent in task.get("runtime_intents", [])
        ):
            fail("planned runtime intents remain unreconciled")
        for task_id in state["run"]["active_agent_slots"]:
            if tasks[task_id]["runtime"].get("status") in {"not-started", "reserved"}:
                fail(f"active task {task_id} has not been reconciled")
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
        child_capability = secrets.token_urlsafe(32)
        child_event = copy.deepcopy(event)
        child_event["capability_hash"] = token_hash(child_capability)
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
        result["task_capability"] = child_capability
        result["slot_reserved"] = reserve

    elif event_type == "rotate-child-capability":
        target = event.get("task_id")
        root_recovery = actor == root_id and state["run"].get("reconciliation_required")
        if (
            not isinstance(target, str)
            or target not in tasks
            or target == actor
            or (tasks[target].get("parent_id") != actor and not root_recovery)
        ):
            fail(
                "only the direct parent or recorded root recovery may rotate a child capability"
            )
        task = tasks[target]
        if (
            target in state["run"]["active_agent_slots"]
            or task["status"] not in {"planning", "queued", "blocked"}
            or task["runtime"].get("productive_prompt")
            or task["runtime"].get("status")
            not in {"not-started", "stopped", "settled", "cancelled"}
        ):
            fail("capability rotation requires an inactive, unproductive task")
        new_capability = secrets.token_urlsafe(32)
        task["capability_hash_history"].append(task["capability_hash"])
        task["capability_hash"] = token_hash(new_capability)
        result["task_capability"] = new_capability

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
        if task["attempts"] != 0:
            fail("task launch attempts cannot be retried")
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
            or task["runtime"].get("productive_prompt")
            or task["runtime"].get("status") not in {"stopped", "settled"}
        ):
            fail("failed launch requires confirmed stopped, unproductive runtime state")
        if any(item.get("status") == "live" for item in task["runtime_resources"]):
            fail("settle failed-launch resources first")
        if target in state["run"]["active_agent_slots"]:
            state["run"]["active_agent_slots"].remove(target)
        task["status"] = "blocked"
        task["phase"] = TASK_PHASES["blocked"]
        task["runtime"]["released_at"] = now()
        task["result"]["blockers"] = [
            event.get("reason") or "Agent launch failed before productive work."
        ]

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
        if intent["kind"] == "agent" and any(
            item.get("kind") == "agent" and item.get("target_task_id") == target_task_id
            for item in existing_intents
        ):
            fail("each task may have exactly one agent launch intent")
        tasks[actor]["runtime_intents"].append(
            {**intent, "status": "planned", "created_at": now()}
        )

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
        tasks[actor]["result"].update(value)

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
        if state["run"]["active_agent_slots"] or any(
            item.get("status") != "closed"
            for task in tasks.values()
            for item in task["runtime_resources"]
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
        allowed = {
            "test_verdict",
            "skipped_reason",
            "test_target_fingerprint",
            "test_evidence",
            "behavior_verdict",
            "behavior_reason",
            "behavior_eligibility",
            "behavior_target_fingerprint",
            "behavior_evidence",
            "evidence_target_fingerprint",
            "evidence_index",
            "changed_files",
            "collisions",
            "review_verdict",
            "review_execution",
            "review_wave",
            "review_scope",
            "review_target_fingerprint",
            "review_wave_fingerprint",
            "review_waves",
            "review_perspectives",
            "review_findings",
            "combined_report_path",
            "finished_at",
        }
        if not isinstance(updates, dict) or set(updates) - allowed:
            fail("update-integration contains unsupported fields")
        updates = copy.deepcopy(updates)
        if "review_waves" in updates:
            previous = state["integration"].get("review_waves", [])
            proposed = updates["review_waves"]
            if (
                not isinstance(proposed, list)
                or proposed[: len(previous)] != previous
                or len(proposed) < len(previous)
            ):
                fail("review wave history is append-only")
        if "changed_files" in updates:
            updates["changed_files"] = validate_repo_files(
                updates["changed_files"], "integration.changed_files"
            )
        state["integration"].update(updates)

    elif event_type == "certify-integration":
        if actor != root_id:
            fail("only the root task may certify integration")
        integration = state["integration"]
        if event.get("validated_revision") != state["revision"]:
            fail("state changed after final validation")
        fingerprint = event.get("fingerprint")
        if (
            not nonempty(fingerprint)
            or fingerprint != integration.get("review_target_fingerprint")
            or live_review_fingerprint(state) != fingerprint
        ):
            fail("certification fingerprint does not match the live review state")
        if (integration.get("review_scope") or {}).get("base_sha") != state["run"][
            "base_commit"
        ]:
            fail("certification review base does not match the run base")
        if run_owned_files(state) != sorted(integration.get("changed_files", [])):
            fail(
                "certification changed files do not match the run-owned worktree delta"
            )
        review_paths = (integration.get("review_scope") or {}).get("paths") or []
        normalized_scope = [
            posixpath.normpath(item.replace("\\", "/"))
            for item in review_paths
            if isinstance(item, str)
        ]
        if any(
            not any(
                scope == "."
                or changed == scope
                or changed.startswith(scope.rstrip("/") + "/")
                for scope in normalized_scope
            )
            for changed in integration.get("changed_files", [])
        ):
            fail(
                "certification review scope does not cover every run-owned changed file"
            )
        artifact_digests = event.get("artifact_digests")
        verify_artifact_digests(state, artifact_digests)
        validate_final_contract(state, fingerprint, artifact_digests)
        if integration.get("review_execution") != "independent":
            fail("certification requires independent review")
        required_reviews = {
            "correctness_safety",
            "architecture_integration",
            "regression_fix_quality",
        }
        perspectives = integration.get("review_perspectives") or {}
        if set(perspectives) != required_reviews or any(
            item.get("status") != "complete"
            or item.get("output_path") not in artifact_digests
            for item in perspectives.values()
        ):
            fail("certification requires three complete reviewer outputs")
        for perspective in perspectives.values():
            validate_review_perspective_proof(state, perspective)
        reviewer_instances = [
            item.get("agent_instance_id") for item in perspectives.values()
        ]
        waves = integration.get("review_waves") or []
        current_wave = next(
            (
                item
                for item in waves
                if item.get("wave") == integration.get("review_wave")
            ),
            None,
        )
        if not isinstance(current_wave, dict) or set(
            current_wave.get("reviewer_instance_ids") or []
        ) != set(reviewer_instances):
            fail("current review wave does not bind reviewer instances")
        prior_reviewer_instances = {
            instance
            for item in waves
            if item.get("wave") != integration.get("review_wave")
            for instance in (item.get("reviewer_instance_ids") or [])
        }
        contributor_instances = {
            state["run"]["coordinator_instance_id"],
            *state["run"].get("coordinator_instance_history", []),
            *[
                task["runtime"].get("agent_instance_id")
                for task in tasks.values()
                if task["runtime"].get("agent_instance_id")
                and (
                    task["runtime"].get("productive_prompt")
                    or task["result"].get("files_changed")
                )
            ],
        }
        if integration.get("review_execution") == "independent" and (
            len(set(reviewer_instances)) != 3
            or any(
                instance in contributor_instances
                or instance in prior_reviewer_instances
                for instance in reviewer_instances
            )
        ):
            fail(
                "independent review instances are not fresh or distinct from contributors"
            )
        required_artifacts = {
            integration.get("combined_report_path"),
            os.path.relpath(
                Path(state["run"]["repo_root"]) / integration.get("evidence_index", ""),
                state_directory(state),
            ),
        }
        for perspective in perspectives.values():
            required_artifacts.update(
                (perspective.get(field) or {}).get("path")
                for field in (
                    "resolution_artifact",
                    "start_response_artifact",
                    "verification_artifact",
                )
            )
        required_artifacts.update(
            item.get("artifact") for item in integration.get("test_evidence", [])
        )
        required_artifacts.update(
            item.get("artifact") for item in integration.get("behavior_evidence", [])
        )
        required_artifacts.update(
            task["runtime"].get("output_path")
            for task in tasks.values()
            if task["runtime"].get("productive_prompt")
        )
        required_artifacts.update(
            intent.get("output_path")
            for task in tasks.values()
            for intent in task.get("runtime_intents", [])
            if intent.get("status") == "bound"
        )
        required_artifacts.update(
            resource.get("closure_artifact")
            for task in tasks.values()
            for resource in task.get("runtime_resources", [])
            if resource.get("status") == "closed"
        )
        if any(item not in artifact_digests for item in required_artifacts if item):
            fail("certification is missing required report or evidence digests")
        if (
            integration.get("review_verdict") != "pass"
            or integration.get("test_verdict") not in {"pass", "skipped"}
            or integration.get("behavior_verdict")
            not in {"pass", "user-pending", "not-applicable"}
        ):
            fail(
                "integration cannot be certified before checks, behavior handoff, and review settle"
            )
        if any(
            item.get("status") == "open"
            for item in integration.get("review_findings", [])
        ):
            fail("review findings remain open")
        if integration.get("behavior_verdict") == "pass":
            evidence = integration.get("behavior_evidence", [])
            artifact_paths = [item.get("artifact") for item in evidence]
            if (
                {item.get("case_type") for item in evidence}
                != {"happy", "error", "edge"}
                or len(set(artifact_paths)) != 3
                or any(
                    not isinstance(path, str)
                    or not posixpath.normpath(path).startswith("evidence/")
                    for path in artifact_paths
                )
                or any(item.get("fingerprint") != fingerprint for item in evidence)
            ):
                fail(
                    "behavior pass requires current distinct evidence-folder happy, error, and edge artifacts"
                )
        if integration.get("behavior_verdict") == "user-pending":
            evidence = integration.get("behavior_evidence", [])
            if (
                len(evidence) != 1
                or evidence[0].get("case_type") != "user-handoff"
                or evidence[0].get("fingerprint") != fingerprint
                or not posixpath.normpath(evidence[0].get("artifact", "")).startswith(
                    "evidence/"
                )
                or not nonempty(integration.get("behavior_reason"))
            ):
                fail(
                    "user-pending behavior verification requires one current evidence-folder manual-test handoff and a reason"
                )
        if any(
            item.get("status") != "resolved"
            for item in integration.get("collisions", [])
        ):
            fail("integration collisions remain unresolved")
        state["integration"]["certification"] = {
            "fingerprint": fingerprint,
            "review_wave": state["integration"].get("review_wave"),
            "revision": state["revision"] + 1,
            "artifact_digests": artifact_digests,
            "changed_files": sorted(integration.get("changed_files", [])),
            "certified_at": now(),
        }

    elif event_type == "complete-run":
        if actor != root_id:
            fail("only the root task may complete the run")
        task = tasks[root_id]
        certification = state["integration"].get("certification") or {}
        if certification.get("revision") != state["revision"]:
            fail("final integration certification is missing or stale")
        if live_review_fingerprint(state) != certification.get("fingerprint"):
            fail("live change moved after certification")
        if run_owned_files(state) != certification.get("changed_files"):
            fail("run-owned worktree delta moved after certification")
        verify_artifact_digests(state, certification.get("artifact_digests"))
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
        if not nonempty(task["result"].get("summary")) or task["result"].get(
            "blockers"
        ):
            fail("root result is missing or still blocked")
        if state["run"]["active_agent_slots"] or any(
            item.get("status") != "closed"
            for value in tasks.values()
            for item in value["runtime_resources"]
        ):
            fail("runtime slots remain or a runtime resource is not closed")
        if live_review_fingerprint(state) != certification.get(
            "fingerprint"
        ) or run_owned_files(state) != certification.get("changed_files"):
            fail("worktree changed during final completion checks")
        verify_artifact_digests(state, certification.get("artifact_digests"))
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
    owner_token: str,
    lease_id: str,
    coordinator_instance_id: str,
    base_commit: str,
    repo_root: str,
) -> dict[str, Any]:
    root_event = {
        "capability_hash": token_hash(owner_token),
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
            "test_target_fingerprint": None,
            "test_evidence": [],
            "behavior_verdict": "pending",
            "behavior_reason": None,
            "behavior_eligibility": None,
            "behavior_target_fingerprint": None,
            "behavior_evidence": [],
            "evidence_target_fingerprint": None,
            "evidence_index": None,
            "changed_files": [],
            "collisions": [],
            "review_verdict": "pending",
            "review_execution": None,
            "review_wave": 0,
            "review_scope": None,
            "review_target_fingerprint": None,
            "review_wave_fingerprint": None,
            "review_waves": [],
            "review_perspectives": {},
            "review_findings": [],
            "combined_report_path": None,
            "certification": None,
            "finished_at": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("path", type=Path)
    init_parser.add_argument("--feature", required=True)
    init_parser.add_argument(
        "--owner-token", default=os.environ.get("IMPLEMENT_TASK_CAPABILITY")
    )
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
        "--owner-token", default=os.environ.get("IMPLEMENT_TASK_CAPABILITY")
    )
    resume_parser.add_argument(
        "--lease-id", default=os.environ.get("IMPLEMENT_COORDINATOR_LEASE_ID")
    )

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("path", type=Path)
    apply_parser.add_argument("--actor", required=True)
    apply_parser.add_argument(
        "--capability", default=os.environ.get("IMPLEMENT_TASK_CAPABILITY")
    )
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
    path = Path(os.path.abspath(args.path))

    if args.command == "init":
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.feature or ""):
            fail("feature name must be lowercase kebab-case")
        if not nonempty(args.owner_token) or not nonempty(args.lease_id):
            fail("init requires task capability and coordinator lease environment")
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
            args.owner_token,
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
        if not nonempty(args.owner_token) or not nonempty(args.lease_id):
            fail("resume requires task capability and coordinator lease environment")
        with LockedState(path) as state:
            validate(state, path)
            root_id = state["run"]["root_task_id"]
            if state.get("feature_name") != args.feature or not secrets.compare_digest(
                state["tasks"][root_id]["capability_hash"], token_hash(args.owner_token)
            ):
                fail("feature name or owner token does not match")
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
            reconciliation_required = bool(
                state["run"]["active_agent_slots"] or live_resources or planned_intents
            )
            if takeover:
                state["run"]["coordinator_instance_history"].append(
                    state["run"]["coordinator_instance_id"]
                )
                state["run"]["coordinator_model_history"].append(
                    copy.deepcopy(state["run"]["coordinator_model"])
                )
                state["run"]["coordinator_instance_id"] = str(secrets.token_hex(16))
                state["run"]["coordinator_model"] = current_coordinator_model(
                    state["run"]["coordinator_instance_id"]
                )
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
        result = apply_event(
            state, path, args.actor, args.capability, args.lease_id, event
        )
        save_atomic(path, state)
    print(json.dumps({**result, "revision": state["revision"]}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (TypeError, ValueError, KeyError, IndexError) as error:
        fail(f"malformed state or event: {error}")
