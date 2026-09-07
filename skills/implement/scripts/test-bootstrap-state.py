#!/usr/bin/env python3
"""End-to-end checks for documented implementation-state bootstrap and recovery."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
STORE = SCRIPT_DIR / "state-store.py"
VALIDATE_PLAN = SCRIPT_DIR / "validate-plan.sh"


def require(condition: bool, message: object) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def run(
    arguments: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        arguments,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        result.returncode == expected,
        {
            "arguments": arguments,
            "expected": expected,
            "actual": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )
    return result


def main() -> None:
    catalog = json.loads(
        run(["python3", str(STORE), "events"], cwd=SCRIPT_DIR, env=os.environ.copy()).stdout
    )
    require(catalog.get("mutation") == "none", catalog)
    event_types = catalog.get("event_types", [])
    for event_type in (
        "set-run",
        "update-contract",
        "add-todo",
        "set-run-phase",
        "set-task-status",
    ):
        require(event_type in event_types, event_types)
    handlers = set()
    for node in ast.walk(ast.parse(STORE.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
            continue
        if not isinstance(node.left, ast.Name) or node.left.id != "event_type":
            continue
        comparator = node.comparators[0]
        if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
            handlers.add(comparator.value)
    advertised = set(event_types) | set(catalog.get("deprecated_event_types", {}))
    require(advertised == handlers, {"advertised_only": sorted(advertised - handlers), "handler_only": sorted(handlers - advertised)})

    with tempfile.TemporaryDirectory(prefix="implement-bootstrap-state-") as directory:
        root = Path(directory)
        run(["git", "init", "-q"], cwd=root, env=os.environ.copy())
        (root / ".gitignore").write_text("var/\n", encoding="utf-8")
        (root / "README.md").write_text("# Bootstrap fixture\n", encoding="utf-8")
        run(["git", "add", "."], cwd=root, env=os.environ.copy())
        run(
            [
                "git",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=user@example.com",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=root,
            env=os.environ.copy(),
        )
        base_commit = run(
            ["git", "rev-parse", "HEAD"], cwd=root, env=os.environ.copy()
        ).stdout.strip()

        feature = "bootstrap-state"
        state = root / "var" / feature / "implement" / "state.json"
        state.parent.mkdir(parents=True)
        owner = "fixture-owner-capability"
        lease = "fixture-coordinator-lease"
        environment = {
            **os.environ,
            "IMPLEMENT_TASK_CAPABILITY": owner,
            "IMPLEMENT_COORDINATOR_LEASE_ID": lease,
            "PI_PROVIDER": "fixture-provider",
            "PI_MODEL": "fixture-model",
            "PI_REASONING_LEVEL": "medium",
        }
        run(
            [
                "python3",
                str(STORE),
                "init",
                str(state),
                "--feature",
                feature,
                "--coordinator-instance-id",
                "fixture-coordinator-instance",
                "--base-commit",
                base_commit,
                "--repo-root",
                str(root),
                "--canonical-path",
                str(state),
            ],
            cwd=root,
            env=environment,
        )

        def apply(event: dict[str, object], expected: int = 0) -> subprocess.CompletedProcess[str]:
            return run(
                [
                    "python3",
                    str(STORE),
                    "apply",
                    str(state),
                    "--actor",
                    "task-0001",
                    "--event-json",
                    json.dumps(event),
                ],
                cwd=root,
                env=environment,
                expected=expected,
            )

        apply(
            {
                "type": "set-run",
                "updates": {"user_goal": "Exercise the documented bootstrap sequence."},
            }
        )
        apply(
            {
                "type": "update-contract",
                "updates": {
                    "title": "Verify bootstrap",
                    "outcome": "The startup sequence validates.",
                    "acceptance_criteria": ["Plan validation passes."],
                    "boundaries": ["Use a temporary repository."],
                    "inputs": ["Documented event payloads."],
                    "expected_result": "A valid plan-stage state file.",
                },
            }
        )
        apply(
            {
                "type": "add-todo",
                "title": "Validate the plan",
                "acceptance": "The plan validator passes.",
            }
        )
        apply({"type": "set-run-phase", "phase": "plan"})
        run(["bash", str(VALIDATE_PLAN), feature], cwd=root, env=environment)

        before = state.read_bytes()
        rejected = apply({"type": "set-root-contract", "updates": {}}, expected=1)
        require("Did you mean 'update-contract'?" in rejected.stderr, rejected.stderr)
        require(state.read_bytes() == before, "a rejected event changed the state file")
        apply({"type": "update-contract", "updates": {"title": "Verify bootstrap"}})
        apply({"type": "set-task-status", "status": "working"})
        apply({"type": "set-run-phase", "phase": "execute"})
        final_state = json.loads(state.read_text(encoding="utf-8"))
        root_task = final_state["tasks"]["task-0001"]
        require(final_state["run"]["phase"] == "execute", final_state["run"])
        require(final_state["run"]["user_goal"] == "Exercise the documented bootstrap sequence.", final_state["run"])
        require(root_task["status"] == "working", root_task)
        require(root_task["title"] == "Verify bootstrap", root_task)
        require(root_task["outcome"] == "The startup sequence validates.", root_task)
        require(root_task["acceptance_criteria"] == ["Plan validation passes."], root_task)
        require(root_task["boundaries"] == ["Use a temporary repository."], root_task)
        require(root_task["inputs"] == ["Documented event payloads."], root_task)
        require(root_task["expected_result"] == "A valid plan-stage state file.", root_task)
        require(len(root_task["todos"]) == 1 and root_task["todos"][0]["title"] == "Validate the plan", root_task["todos"])

    print("PASS: implementation bootstrap is documented, discoverable, valid, and safely recoverable")


if __name__ == "__main__":
    main()
