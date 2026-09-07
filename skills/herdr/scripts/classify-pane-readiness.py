#!/usr/bin/env python3
"""Fail-closed classification for saved `herdr pane process-info` responses."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

EXIT_CODES = {"ready": 0, "busy": 10, "expired": 20, "ambiguous": 30}
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d+))?"
    r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)


def parse_time(value: str) -> datetime:
    match = RFC3339.fullmatch(value)
    if not match:
        raise ValueError("timestamp must use RFC 3339 date-time syntax")
    fraction = match.group(1)
    if fraction and len(fraction) > 6:
        raise ValueError("timestamp fractional seconds must not exceed six digits")
    if value.endswith("-00:00"):
        raise ValueError("timestamp must use a known UTC offset")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def ambiguous(reason: str) -> tuple[str, str, dict[str, Any]]:
    return "ambiguous", reason, {}


def positive_integer(value: Any) -> bool:
    return type(value) is int and value > 0


def process_snapshot(payload: Any, expected_pane: str) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(expected_pane, str) or not expected_pane.strip():
        return None, "expected pane ID is missing or empty"
    if not isinstance(payload, dict) or payload.get("id") != "cli:pane:process_info":
        return None, "the Herdr response ID is missing or unsupported"
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("type") != "pane_process_info":
        return None, "the Herdr response type is missing or unsupported"
    process_info = result.get("process_info")
    if not isinstance(process_info, dict) or process_info.get("pane_id") != expected_pane:
        return None, "process_info is missing or belongs to a different pane"
    shell_pid = process_info.get("shell_pid")
    processes = process_info.get("foreground_processes")
    if not positive_integer(shell_pid):
        return None, "shell_pid is missing or invalid"
    if not isinstance(processes, list) or not processes:
        return None, "foreground_processes is missing, malformed, or empty"
    if any(not isinstance(item, dict) or not positive_integer(item.get("pid")) for item in processes):
        return None, "foreground_processes contains an invalid PID entry"
    pids = [item["pid"] for item in processes]
    if len(set(pids)) != len(pids):
        return None, "foreground_processes contains duplicate PIDs"
    if pids.count(shell_pid) != 1:
        return None, "the interactive shell is not present exactly once"
    return {"paneId": expected_pane, "shellPid": shell_pid, "processes": processes}, None


def validate_previous_classification(
    payload: Any,
    expected_pane: str,
    created_at: str,
    deadline_at: str,
    previous_snapshot: dict[str, Any],
) -> None:
    processes = previous_snapshot["processes"]
    shell_pid = previous_snapshot["shellPid"]
    extras = [str(item.get("name") or "unknown") for item in processes if item["pid"] != shell_pid]
    if (
        not isinstance(payload, dict)
        or not positive_integer(payload.get("shellPid"))
        or type(payload.get("extraProcessCount")) is not int
        or not isinstance(payload.get("extraProcessNames"), list)
        or any(not isinstance(name, str) for name in payload.get("extraProcessNames", []))
        or not isinstance(payload.get("observedAt"), str)
    ):
        raise ValueError("previous classification has an invalid busy-result schema")
    expected = {
        "classification": "busy",
        "reason": "the shell has additional foreground work",
        "expectedPane": expected_pane,
        "createdAt": created_at,
        "deadlineAt": deadline_at,
        "observedAt": payload["observedAt"],
        "paneId": expected_pane,
        "shellPid": shell_pid,
        "extraProcessCount": len(extras),
        "extraProcessNames": extras,
    }
    if payload != expected:
        raise ValueError("previous classification does not bind the complete busy process evidence")


def classify(
    payload: Any,
    expected_pane: str,
    created_at: datetime,
    deadline: datetime,
    now: datetime,
    previous_payload: Any | None = None,
) -> tuple[str, str, dict[str, Any]]:
    if deadline <= created_at or deadline - created_at > timedelta(seconds=30):
        return ambiguous("the readiness deadline is not anchored within 30 seconds of creation")
    if now < created_at:
        return ambiguous("the readiness clock is earlier than pane creation")
    current, error = process_snapshot(payload, expected_pane)
    if error:
        return ambiguous(error)
    if previous_payload is not None:
        previous, previous_error = process_snapshot(previous_payload, expected_pane)
        if previous_error:
            return ambiguous(f"previous snapshot is invalid: {previous_error}")
        if previous["shellPid"] != current["shellPid"]:
            return ambiguous("pane or shell identity changed between readiness snapshots")
        if len(previous["processes"]) == 1:
            return ambiguous("readiness was rechecked after the pane was already ready")
        previous_extras = {
            item["pid"]: item
            for item in previous["processes"]
            if item["pid"] != previous["shellPid"]
        }
        current_extras = {
            item["pid"]: item
            for item in current["processes"]
            if item["pid"] != current["shellPid"]
        }
        if any(previous_extras.get(pid) != item for pid, item in current_extras.items()):
            return ambiguous("foreground work was added or replaced during readiness recheck")
    if now >= deadline:
        return "expired", "the original pane-readiness deadline has elapsed", {
            "paneId": expected_pane,
            "shellPid": current["shellPid"],
        }
    processes = current["processes"]
    if len(processes) == 1:
        return "ready", "the interactive shell is the sole foreground process", {
            "paneId": expected_pane,
            "shellPid": current["shellPid"],
        }
    extras = [str(item.get("name") or "unknown") for item in processes if item["pid"] != current["shellPid"]]
    return "busy", "the shell has additional foreground work", {
        "paneId": expected_pane,
        "shellPid": current["shellPid"],
        "extraProcessCount": len(extras),
        "extraProcessNames": extras,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Saved JSON from herdr pane process-info")
    parser.add_argument("--previous-input", help="Previous saved process snapshot for a bounded recheck")
    parser.add_argument(
        "--previous-classification",
        help="Previous saved busy classification that binds the immutable recheck deadline",
    )
    parser.add_argument("--expected-pane", required=True, help="Exact pane ID being certified")
    parser.add_argument("--created-at", required=True, help="Persisted pre-create intent timestamp")
    parser.add_argument(
        "--deadline-at",
        help="Persisted RFC 3339 deadline; when omitted, derive exactly 30 seconds from created-at",
    )
    parser.add_argument("--now", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        previous_supplied = args.previous_input is not None
        previous_classification_supplied = args.previous_classification is not None
        if previous_supplied != previous_classification_supplied:
            raise ValueError("--previous-input and --previous-classification must be supplied together")
        previous = (
            json.loads(Path(args.previous_input).read_text(encoding="utf-8"))
            if previous_supplied
            else None
        )
        previous_classification = (
            json.loads(Path(args.previous_classification).read_text(encoding="utf-8"))
            if previous_classification_supplied
            else None
        )
        if previous_supplied and args.deadline_at is None:
            raise ValueError("--deadline-at is required for a bounded recheck")
        if previous_supplied and previous is None:
            raise ValueError("previous snapshot must not be null")
        created_at = parse_time(args.created_at)
        if args.deadline_at is not None:
            deadline = parse_time(args.deadline_at)
        else:
            try:
                deadline = created_at + timedelta(seconds=30)
            except OverflowError:
                deadline = datetime.max.replace(tzinfo=timezone.utc)
                raise ValueError("derived deadline exceeds the supported timestamp range")
        if previous_supplied:
            previous_snapshot, previous_error = process_snapshot(previous, args.expected_pane)
            if previous_error:
                raise ValueError(f"previous snapshot is invalid: {previous_error}")
            validate_previous_classification(
                previous_classification,
                args.expected_pane,
                args.created_at,
                args.deadline_at,
                previous_snapshot,
            )
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        if previous_supplied and now < parse_time(previous_classification["observedAt"]):
            raise ValueError("readiness observation time moved backward")
        classification, reason, details = classify(
            payload, args.expected_pane, created_at, deadline, now, previous
        )
    except (OSError, ValueError, OverflowError, json.JSONDecodeError) as error:
        classification, reason, details = ambiguous(str(error))
    print(json.dumps({
        "classification": classification,
        "reason": reason,
        "expectedPane": args.expected_pane,
        "createdAt": args.created_at,
        "deadlineAt": (
            args.deadline_at
            if args.deadline_at is not None
            else format_time(deadline) if "deadline" in locals() else None
        ),
        "observedAt": format_time(now) if "now" in locals() else None,
        **details,
    }, sort_keys=True))
    return EXIT_CODES[classification]


if __name__ == "__main__":
    sys.exit(main())
