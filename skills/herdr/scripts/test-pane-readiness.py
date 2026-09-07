#!/usr/bin/env python3
"""Deterministic checks for the fail-closed Herdr pane-readiness classifier."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("classify-pane-readiness.py")
PANE = "w1:p2"
NOW = "2026-09-02T18:00:00Z"
CREATED = "2026-09-02T17:59:50Z"
FUTURE = "2026-09-02T18:00:20Z"
OVERLONG = "2026-09-02T18:00:21Z"
PAST = "2026-09-02T17:59:59Z"


def response(processes: object, shell_pid: object = 100, pane: str = PANE) -> dict[str, object]:
    return {
        "id": "cli:pane:process_info",
        "result": {
            "type": "pane_process_info",
            "process_info": {"pane_id": pane, "shell_pid": shell_pid, "foreground_processes": processes},
        },
    }


def require(condition: bool, message: object) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def check(
    name: str,
    payload: object,
    deadline: str,
    expected: str,
    exit_code: int,
    *,
    previous: object | None = None,
    expected_pane: str = PANE,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "process.json"
        source.write_text(json.dumps(payload), encoding="utf-8")
        command = [
            str(SCRIPT), "--input", str(source), "--expected-pane", expected_pane,
            "--created-at", CREATED, "--deadline-at", deadline, "--now", NOW,
        ]
        if previous is not None:
            previous_source = Path(directory) / "previous.json"
            previous_source.write_text(json.dumps(previous), encoding="utf-8")
            command.extend(["--previous-input", str(previous_source)])
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    require(result.returncode == exit_code, (name, result.returncode, result.stdout, result.stderr))
    parsed = json.loads(result.stdout)
    require(parsed["classification"] == expected, (name, parsed))


def main() -> None:
    shell = {"pid": 100, "name": "zsh", "argv": ["-zsh"]}
    helper = {"pid": 101, "name": "python", "argv": ["conda", "shell.zsh", "hook"]}
    busy = response([shell, helper])
    check("ready", response([shell]), FUTURE, "ready", 0)
    check("busy", busy, FUTURE, "busy", 10)
    check("busy-to-ready", response([shell]), FUTURE, "ready", 0, previous=busy)
    check("busy-to-busy", busy, FUTURE, "busy", 10, previous=busy)
    check("changed-shell", response([{"pid": 200, "name": "zsh"}], 200), FUTURE, "ambiguous", 30, previous=busy)
    check("already-ready-recheck", response([shell]), FUTURE, "ambiguous", 30, previous=response([shell]))
    check("wrong-pane", response([shell], pane="w1:p3"), FUTURE, "ambiguous", 30)
    check("missing-pane", response([shell], pane=""), FUTURE, "ambiguous", 30)
    wrong_id = response([shell]); wrong_id["id"] = "cli:pane:get"
    check("wrong-response-id", wrong_id, FUTURE, "ambiguous", 30)
    wrong_type = response([shell]); wrong_type["result"]["type"] = "other"
    check("wrong-response-type", wrong_type, FUTURE, "ambiguous", 30)
    check("empty", response([]), FUTURE, "ambiguous", 30)
    check("missing-list", response(None), FUTURE, "ambiguous", 30)
    check("boolean-shell", response([{"pid": True}], True), FUTURE, "ambiguous", 30)
    check("boolean-process", response([shell, {"pid": True}]), FUTURE, "ambiguous", 30)
    check("zero-pid", response([{"pid": 0}], 0), FUTURE, "ambiguous", 30)
    check("negative-pid", response([{"pid": -1}], -1), FUTURE, "ambiguous", 30)
    check("duplicate-pid", response([shell, shell]), FUTURE, "ambiguous", 30)
    check("overlong-deadline", response([shell]), OVERLONG, "ambiguous", 30)
    check("expired", response([shell]), PAST, "expired", 20)
    check("expired-malformed", {}, PAST, "ambiguous", 30)
    check("malformed-json-shape", {}, FUTURE, "ambiguous", 30)
    print("PASS: pane readiness classifications")


if __name__ == "__main__":
    main()
