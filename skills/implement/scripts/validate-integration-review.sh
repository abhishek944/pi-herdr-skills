#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
FEATURE_NAME="${1:-}"
ACTION="${2:-}"
STATE_DIR="$REPO_ROOT/var/$FEATURE_NAME/implement"
STATE_FILE="$STATE_DIR/state.json"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_ROOT="$(cd "$SCRIPTS_DIR/../.." && pwd)"

if [[ ! "$FEATURE_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ || ( -n "$ACTION" && "$ACTION" != "--certify" ) ]]; then
  echo "Usage: $0 <feature-name> [--certify]" >&2
  exit 2
fi
if [[ "$ACTION" == "--certify" && ( -z "${IMPLEMENT_TASK_CAPABILITY:-}" || -z "${IMPLEMENT_COORDINATOR_LEASE_ID:-}" ) ]]; then
  echo "FAIL: --certify requires the root task capability and coordinator lease environment" >&2
  exit 1
fi

python3 "$SCRIPTS_DIR/state-store.py" validate "$STATE_FILE" >/dev/null
VALIDATION_OUTPUT="$(python3 - "$REPO_ROOT" "$STATE_DIR" "$SKILLS_ROOT" <<'PY'
import datetime
import hashlib
import json
import os
import subprocess
import sys

def clean_failure(error_type, value, traceback):
    print(f"FAIL: malformed integration state or artifact: {value}", file=sys.stderr)

sys.excepthook = clean_failure
repo_root, state_dir, skills_root = sys.argv[1:]
with open(os.path.join(state_dir, "state.json")) as handle:
    whole = json.load(handle)
state = whole["integration"]
errors = []
revision = whole["revision"]

root_id = whole["run"]["root_task_id"]
if whole["run"].get("active_agent_slots"):
    errors.append("active descendant agent slots remain")
contributors = {whole["run"]["coordinator_instance_id"], *whole["run"].get("coordinator_instance_history", [])}
reported_changed_files = {os.path.normpath(item).replace(os.sep, "/") for item in (whole["tasks"][root_id].get("result") or {}).get("files_changed", []) if isinstance(item, str) and item.strip()}
for task_id, task in whole["tasks"].items():
    if task_id != root_id and task.get("status") not in {"done", "cancelled"}:
        errors.append(f"descendant task is not settled: {task_id}")
    agent_instance_id = (task.get("runtime") or {}).get("agent_instance_id")
    if agent_instance_id and ((task.get("runtime") or {}).get("productive_prompt") or (task.get("result") or {}).get("files_changed")):
        contributors.add(agent_instance_id)
    for resource in task.get("runtime_resources", []):
        if resource.get("status") != "closed":
            errors.append(f"task has an unclosed runtime resource: {task_id}")

def worktree_snapshot():
    base = whole["run"]["base_commit"]
    changed = subprocess.check_output(["git", "-C", repo_root, "diff", "--name-only", "-z", base, "--"])
    untracked = subprocess.check_output(["git", "-C", repo_root, "ls-files", "--others", "--exclude-standard", "-z", "--"])
    paths = {item.decode("utf-8", "surrogateescape") for item in (changed + untracked).split(b"\0") if item}
    result = {}
    for relative in paths:
        candidate = os.path.join(repo_root, relative)
        if os.path.islink(candidate):
            result[relative] = f"{os.lstat(candidate).st_mode:o}:symlink:" + os.readlink(candidate)
        elif os.path.isfile(candidate):
            with open(candidate, "rb") as handle:
                result[relative] = f"{os.stat(candidate).st_mode:o}:" + hashlib.sha256(handle.read()).hexdigest()
        else:
            result[relative] = "<deleted>"
    return result

baseline = whole["run"].get("initial_worktree") or {}
current_snapshot = worktree_snapshot()
actual_run_owned = {path for path in set(baseline) | set(current_snapshot) if baseline.get(path) != current_snapshot.get(path)}
integration_changed = state.get("changed_files")
if not isinstance(integration_changed, list):
    errors.append("integration.changed_files must be a list")
    integration_changed_set = set()
else:
    integration_changed_set = {os.path.normpath(item).replace(os.sep, "/") for item in integration_changed if isinstance(item, str) and item.strip()}
if reported_changed_files != integration_changed_set:
    errors.append("integration.changed_files must exactly match the root's surviving integrated files")
if actual_run_owned != integration_changed_set:
    errors.append("integration.changed_files must exactly match the worktree delta created by this run")
collisions = state.get("collisions") or []
for collision in collisions:
    if collision.get("status") != "resolved" or not str(collision.get("resolution") or "").strip() or not collision.get("rerun_evidence"):
        errors.append("every changed-file or behavioral collision must be resolved with rerun evidence")
for parent_id, parent in whole["tasks"].items():
    children = parent.get("children", [])
    for index, left_id in enumerate(children):
        left_files = set((whole["tasks"][left_id].get("result") or {}).get("files_changed", []))
        for right_id in children[index + 1:]:
            overlap = left_files & set((whole["tasks"][right_id].get("result") or {}).get("files_changed", []))
            if overlap and not any({left_id, right_id}.issubset(set(item.get("tasks", []))) and overlap.issubset(set(item.get("files", []))) for item in collisions):
                errors.append(f"missing collision ledger entry for {left_id}, {right_id}: {sorted(overlap)}")

scope = state.get("review_scope") or {}
base_sha = scope.get("base_sha")
target = scope.get("target_ref")
if base_sha and base_sha != whole["run"].get("base_commit"):
    errors.append("review base must equal the run's recorded base commit")
paths = scope.get("paths")
if not base_sha or not target or not isinstance(paths, list) or not paths:
    errors.append("review_scope must persist the resolved base, target, and non-empty scope")
    live = None
else:
    command = [
        "bash",
        os.path.join(skills_root, "agent-review/scripts/review-fingerprint.sh"),
        "--base", base_sha,
        "--target", target,
        "--format", "json",
    ]
    for item in paths:
        command.extend(["--scope", item])
    try:
        live = json.loads(subprocess.check_output(command, text=True))
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as error:
        errors.append(f"could not calculate the live review fingerprint: {error}")
        live = None

if live:
    if scope.get("base_sha") != live.get("base_sha"):
        errors.append("review base does not match the live base")
    if scope.get("target_ref") != live.get("target_ref") or scope.get("target_sha") != live.get("target_sha"):
        errors.append("review target does not match the live target")
    if paths != live.get("scope"):
        errors.append("review scope does not match the normalized live scope")
    expected = live.get("fingerprint")
else:
    expected = None

normalized_scope = [os.path.normpath(item).replace(os.sep, "/").rstrip("/") or "." for item in paths or []]
def covered(path):
    return any(scope_item == "." or path == scope_item or path.startswith(scope_item + "/") for scope_item in normalized_scope)
for changed in sorted(integration_changed_set):
    if not covered(changed):
        errors.append(f"review scope does not cover run-owned changed file: {changed}")

if state.get("review_verdict") != "pass":
    errors.append("review_verdict is not pass")
execution = state.get("review_execution")
if execution != "independent":
    errors.append("review_execution must be independent")
wave = state.get("review_wave")
if not isinstance(wave, int) or wave < 1:
    errors.append("review_wave must be a positive integer")
for field in ("review_target_fingerprint", "review_wave_fingerprint", "test_target_fingerprint", "evidence_target_fingerprint"):
    if expected and state.get(field) != expected:
        errors.append(f"{field} does not match the live combined change")
if state.get("test_verdict") not in {"pass", "skipped"}:
    errors.append("test_verdict must be pass or explicitly skipped")
if state.get("test_verdict") == "skipped" and not str(state.get("skipped_reason") or "").strip():
    errors.append("skipped tests require a reason")
test_evidence = state.get("test_evidence") or []
if state.get("test_verdict") == "pass":
    if not test_evidence:
        errors.append("passing tests require evidence")
    test_root = os.path.realpath(os.path.join(state_dir, "evidence")) + os.sep
    for item in test_evidence:
        candidate = os.path.realpath(os.path.join(state_dir, item.get("artifact", ""))) if isinstance(item, dict) else ""
        if not isinstance(item, dict) or item.get("fingerprint") != expected or not str(item.get("summary") or "").strip() or not candidate.startswith(test_root) or not os.path.isfile(candidate) or os.path.getsize(candidate) == 0:
            errors.append("test evidence is stale, missing, or outside the evidence folder")
behavior = state.get("behavior_verdict")
if behavior not in {"pass", "user-pending", "not-applicable"}:
    errors.append("behavior verification must pass, have a user-owned handoff, or be explicitly not applicable")
if behavior == "not-applicable":
    eligibility = state.get("behavior_eligibility") or {}
    if not str(state.get("behavior_reason") or "").strip() or eligibility.get("classification") != "documentation-only" or not str(eligibility.get("evidence") or "").strip():
        errors.append("not-applicable behavior verification requires documented documentation-only eligibility")
    if not integration_changed_set or any(os.path.splitext(item)[1].lower() not in {".md", ".txt", ".rst"} for item in integration_changed_set):
        errors.append("not-applicable behavior verification is limited to documentation-only changes")
if behavior == "user-pending" and not str(state.get("behavior_reason") or "").strip():
    errors.append("user-pending behavior verification requires a reason")
if expected and state.get("behavior_target_fingerprint") != expected:
    errors.append("behavior verification is for a different combined change")
behavior_evidence = state.get("behavior_evidence") or []
if behavior == "pass":
    if {item.get("case_type") for item in behavior_evidence if isinstance(item, dict)} != {"happy", "error", "edge"} or len({item.get("artifact") for item in behavior_evidence if isinstance(item, dict)}) != 3:
        errors.append("behavior pass requires distinct happy, error, and edge evidence")
    evidence_root = os.path.realpath(os.path.join(state_dir, "evidence")) + os.sep
    for item in behavior_evidence:
        artifact = item.get("artifact") if isinstance(item, dict) else None
        candidate = os.path.realpath(os.path.join(state_dir, artifact or ""))
        if item.get("fingerprint") != expected or not candidate.startswith(evidence_root) or not os.path.isfile(candidate) or os.path.getsize(candidate) == 0:
            errors.append("behavior evidence is stale, missing, or outside the run evidence folder")
if behavior == "user-pending":
    evidence_root = os.path.realpath(os.path.join(state_dir, "evidence")) + os.sep
    if len(behavior_evidence) != 1 or behavior_evidence[0].get("case_type") != "user-handoff":
        errors.append("user-pending behavior verification requires one manual-test handoff")
    else:
        artifact = behavior_evidence[0].get("artifact")
        candidate = os.path.realpath(os.path.join(state_dir, artifact or ""))
        if behavior_evidence[0].get("fingerprint") != expected or not candidate.startswith(evidence_root) or not os.path.isfile(candidate) or os.path.getsize(candidate) == 0:
            errors.append("user test handoff is stale, missing, or outside the run evidence folder")

waves = state.get("review_waves") or []
matching_wave = next((item for item in waves if item.get("wave") == wave), None)
if waves and wave != waves[-1].get("wave"):
    errors.append("review_wave must be the newest appended wave")
wave_started_at = None
if not matching_wave or matching_wave.get("fingerprint") != expected or matching_wave.get("status") != "complete":
    errors.append("the current review wave record is missing, stale, or incomplete")
else:
    try:
        wave_started_at = datetime.datetime.fromisoformat(matching_wave.get("started_at").replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        errors.append("current review wave started_at is missing or invalid")

def contained_file(relative, expected_relative, label):
    if relative != expected_relative:
        errors.append(f"{label} is not from the current review wave")
        return None
    candidate = os.path.realpath(os.path.join(state_dir, relative))
    root = os.path.realpath(os.path.join(state_dir, "reviews")) + os.sep
    if not candidate.startswith(root) or not os.path.isfile(candidate) or os.path.getsize(candidate) == 0:
        errors.append(f"{label} is missing or outside the review folder")
        return None
    return relative

combined = contained_file(state.get("combined_report_path"), f"reviews/wave-{wave}-combined.md", "combined review report")
if combined:
    combined_text = open(os.path.join(state_dir, combined), encoding="utf-8").read()
    for marker in (f"Fingerprint: {expected}", f"Review wave: {wave}"):
        if marker not in combined_text:
            errors.append(f"combined review report is missing marker: {marker}")
required = {
    "correctness_safety": f"reviews/wave-{wave}-correctness.md",
    "architecture_integration": f"reviews/wave-{wave}-architecture.md",
    "regression_fix_quality": f"reviews/wave-{wave}-regression.md",
}
agent_ids = []
agent_instance_ids = []
report_finding_ids = set()
outputs = []
for name, expected_output in required.items():
    item = (state.get("review_perspectives") or {}).get(name) or {}
    if not item.get("agent_id"):
        errors.append(f"{name} reviewer ID is missing")
    else:
        agent_ids.append(item["agent_id"])
    if item.get("status") != "complete":
        errors.append(f"{name} review is incomplete")
    reviewer_instance = item.get("agent_instance_id")
    if not reviewer_instance:
        errors.append(f"{name} reviewer instance provenance is missing")
    else:
        agent_instance_ids.append(reviewer_instance)
        if reviewer_instance in contributors:
            errors.append(f"{name} reviewer previously contributed to implementation")
    for field in ("provider", "model_id", "thinking_level"):
        if not str(item.get(field) or "").strip():
            errors.append(f"{name} reviewer {field} is missing")
    for field in ("resolution_artifact", "start_response_artifact", "verification_artifact"):
        artifact = item.get(field) or {}
        relative = artifact.get("path")
        digest = artifact.get("digest")
        candidate = os.path.realpath(os.path.join(state_dir, relative or ""))
        outputs_root = os.path.realpath(os.path.join(state_dir, "outputs")) + os.sep
        if not isinstance(relative, str) or not candidate.startswith(outputs_root) or not os.path.isfile(candidate):
            errors.append(f"{name} reviewer {field} is missing or outside outputs")
        elif not isinstance(digest, str) or len(digest) != 64 or hashlib.sha256(open(candidate, "rb").read()).hexdigest() != digest:
            errors.append(f"{name} reviewer {field} digest is invalid")
    output = contained_file(item.get("output_path"), expected_output, f"{name} output")
    if output:
        outputs.append(output)
        report_text = open(os.path.join(state_dir, output), encoding="utf-8").read()
        for marker in (f"Fingerprint: {expected}", f"Review wave: {wave}", f"Reviewer: {item.get('agent_id')}"):
            if marker not in report_text:
                errors.append(f"{name} output is missing marker: {marker}")
        finding_line = next((line for line in report_text.splitlines() if line.startswith("Finding IDs: ")), None)
        if finding_line is None:
            errors.append(f"{name} output is missing Finding IDs marker")
        else:
            raw_ids = finding_line.split(":", 1)[1].strip()
            if raw_ids.lower() != "none":
                report_finding_ids.update(item.strip() for item in raw_ids.split(",") if item.strip())
    for field in ("started_at", "deadline_at"):
        value = item.get(field)
        try:
            parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if field == "started_at" and wave_started_at and parsed < wave_started_at:
                errors.append(f"{name} started before the current review wave")
        except (AttributeError, ValueError):
            errors.append(f"{name} {field} is missing or invalid")
if len(agent_ids) == 3:
    if execution == "independent" and (len(set(agent_ids)) != 3 or len(set(agent_instance_ids)) != 3):
        errors.append("independent reviewer IDs and instance IDs must be distinct")
    if matching_wave and set(matching_wave.get("reviewer_instance_ids") or []) != set(agent_instance_ids):
        errors.append("current review wave does not bind the current reviewer instances")
    prior_instances = {instance for item in waves if item.get("wave") != wave for instance in (item.get("reviewer_instance_ids") or [])}
    if execution == "independent" and prior_instances & set(agent_instance_ids):
        errors.append("current independent review reuses a reviewer instance from an earlier wave")
if combined in outputs or len(outputs) != len(set(outputs)):
    errors.append("review outputs and the combined report must be distinct")
structured_findings = state.get("review_findings") or []
structured_ids = {item.get("id") for item in structured_findings if isinstance(item, dict)}
if report_finding_ids != structured_ids:
    errors.append("structured review findings must exactly match reviewer Finding IDs markers")
if any(item.get("status") == "open" for item in structured_findings if isinstance(item, dict)):
    errors.append("review findings remain open")

evidence = state.get("evidence_index")
expected_evidence = os.path.realpath(os.path.join(state_dir, "evidence-index.md"))
if not evidence:
    errors.append("evidence index path is missing")
else:
    evidence_path = evidence if os.path.isabs(evidence) else os.path.join(repo_root, evidence)
    if os.path.realpath(evidence_path) != expected_evidence or not os.path.isfile(evidence_path) or os.path.getsize(evidence_path) == 0:
        errors.append("evidence index is missing or outside this implementation run")

if errors:
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    raise SystemExit(1)
task_outputs = [task.get("runtime", {}).get("output_path") for task in whole["tasks"].values() if task.get("runtime", {}).get("productive_prompt") and task.get("runtime", {}).get("output_path")]
intent_outputs = [intent.get("output_path") for task in whole["tasks"].values() for intent in task.get("runtime_intents", []) if intent.get("status") == "bound" and intent.get("output_path")]
closure_outputs = [resource.get("closure_artifact") for task in whole["tasks"].values() for resource in task.get("runtime_resources", []) if resource.get("status") == "closed" and resource.get("closure_artifact")]
artifact_relatives = [combined, *outputs, os.path.relpath(expected_evidence, state_dir), *[item.get("artifact") for item in test_evidence if isinstance(item, dict) and item.get("artifact")], *[item.get("artifact") for item in behavior_evidence if isinstance(item, dict) and item.get("artifact")], *task_outputs, *intent_outputs, *closure_outputs]
artifact_digests = {}
for relative in artifact_relatives:
    if relative:
        candidate = os.path.join(state_dir, relative)
        with open(candidate, "rb") as handle:
            artifact_digests[relative] = hashlib.sha256(handle.read()).hexdigest()
print(f"PASS: all descendants settled and the {execution} review matches the live combined change")
print(f"CERTIFY_FINGERPRINT={expected}")
print(f"CERTIFY_REVISION={revision}")
print("CERTIFY_ARTIFACTS=" + json.dumps(artifact_digests, sort_keys=True, separators=(",", ":")))
PY
)"
printf '%s\n' "$VALIDATION_OUTPUT" | grep -v '^CERTIFY_'

if [[ "$ACTION" == "--certify" ]]; then
  FINGERPRINT="$(printf '%s\n' "$VALIDATION_OUTPUT" | awk -F= '/^CERTIFY_FINGERPRINT=/{print $2}')"
  REVISION="$(printf '%s\n' "$VALIDATION_OUTPUT" | awk -F= '/^CERTIFY_REVISION=/{print $2}')"
  ARTIFACTS="$(printf '%s\n' "$VALIDATION_OUTPUT" | sed -n 's/^CERTIFY_ARTIFACTS=//p')"
  EVENT_JSON="$(python3 - "$FINGERPRINT" "$REVISION" "$ARTIFACTS" <<'PY'
import json, sys
print(json.dumps({"type": "certify-integration", "fingerprint": sys.argv[1], "validated_revision": int(sys.argv[2]), "artifact_digests": json.loads(sys.argv[3])}))
PY
)"
  python3 "$SCRIPTS_DIR/state-store.py" apply "$STATE_FILE" \
    --actor task-0001 \
    --event-json "$EVENT_JSON" >/dev/null
  echo "PASS: final integration state certified"
fi
