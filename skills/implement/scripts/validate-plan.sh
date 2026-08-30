#!/usr/bin/env bash
# Validate the recursive logical task plan. No folder ownership is required.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
FEATURE_NAME="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="$ROOT/var/$FEATURE_NAME/implement/state.json"

if [[ ! "$FEATURE_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "Usage: $0 <feature-name>" >&2
  exit 2
fi
if [[ ! -r "$STATE_FILE" ]]; then
  echo "FAIL: missing $STATE_FILE" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/state-store.py" validate "$STATE_FILE" >/dev/null
python3 - "$STATE_FILE" <<'PY'
import json
import sys

with open(sys.argv[1]) as handle:
    state = json.load(handle)

errors = []
run = state["run"]
tasks = state["tasks"]
root = tasks[run["root_task_id"]]

def nonempty(value):
    return isinstance(value, str) and bool(value.strip())

if not nonempty(run.get("user_goal")):
    errors.append("run.user_goal must be recorded before execution")
if not root.get("todos"):
    errors.append("the root task must create todos before any implementation begins")
if not nonempty(root.get("outcome")) or not root.get("acceptance_criteria"):
    errors.append("the root task needs an outcome and acceptance criteria")

children_exist = len(tasks) > 1
if children_exist:
    catalog = run.get("model_catalog")
    if not isinstance(catalog, dict) or not nonempty(catalog.get("path")):
        errors.append("delegated plans must record the model catalog path")

for task_id, task in tasks.items():
    if not nonempty(task.get("outcome")):
        errors.append(f"{task_id} needs one clear outcome")
    if not nonempty(task.get("expected_result")):
        errors.append(f"{task_id} needs an expected result")
    if not task.get("acceptance_criteria"):
        errors.append(f"{task_id} needs acceptance criteria")
    if task.get("task_class") == "review" and task.get("allow_subagents"):
        errors.append(f"{task_id} is a reviewer and cannot allow subagents")
    if task.get("status") in {"launching", "working", "waiting", "integrating", "done"}:
        for dependency in task.get("dependencies", []):
            if tasks[dependency]["status"] != "done":
                errors.append(f"{task_id} started before dependency {dependency} completed")

for task_id, task in tasks.items():
    child_outcomes = []
    for child_id in task.get("children", []):
        outcome = " ".join(tasks[child_id]["outcome"].lower().split())
        if outcome in child_outcomes:
            errors.append(f"{task_id} has children with duplicate outcomes")
        child_outcomes.append(outcome)

if errors:
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: logical task tree has {len(tasks)} task(s), valid limits, todos, dependencies, and model routing state")
PY
