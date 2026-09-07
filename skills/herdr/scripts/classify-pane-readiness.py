#!/usr/bin/env python3
"""Fail-closed classification for saved `herdr pane process-info` responses."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

EXIT_CODES = {"ready": 0, "busy": 10, "expired": 20, "ambiguous": 30}


def parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def ambiguous(reason: str) -> tuple[str, str, dict[str, Any]]:
    return "ambiguous", reason, {}


def positive_integer(value: Any) -> bool:
    return type(value) is int and value > 0


def process_snapshot(payload: Any, expected_pane: str) -> tuple[dict[str, Any] | None, str | None]:
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


def classify(
    payload: Any,
    expected_pane: str,
    created_at: datetime,
    deadline: datetime,
    now: datetime,
    previous_payload: Any | None = None,
) -> tuple[str, str, dict[str, Any]]:
    if deadline <= created_at or deadline > created_at + timedelta(seconds=30):
        return ambiguous("the readiness deadline is not anchored within 30 seconds of creation")
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
    parser.add_argument("--previous-input", help="Previous saved snapshot for a bounded recheck")
    parser.add_argument("--expected-pane", required=True, help="Exact pane ID being certified")
    parser.add_argument("--created-at", required=True, help="Persisted pre-create intent timestamp")
    parser.add_argument("--deadline-at", required=True, help="Original RFC 3339 readiness deadline")
    parser.add_argument("--now", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        previous = json.loads(Path(args.previous_input).read_text(encoding="utf-8")) if args.previous_input else None
        created_at = parse_time(args.created_at)
        deadline = parse_time(args.deadline_at)
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        classification, reason, details = classify(
            payload, args.expected_pane, created_at, deadline, now, previous
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        classification, reason, details = ambiguous(str(error))
    print(json.dumps({
        "classification": classification,
        "reason": reason,
        "expectedPane": args.expected_pane,
        "createdAt": args.created_at,
        "deadlineAt": args.deadline_at,
        **details,
    }, sort_keys=True))
    return EXIT_CODES[classification]


if __name__ == "__main__":
    sys.exit(main())
