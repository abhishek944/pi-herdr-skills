#!/usr/bin/env bash
set -euo pipefail
unset PYTHONOPTIMIZE

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

for required in package.json README.md LICENSE SECURITY.md THIRD_PARTY_NOTICES.md scripts/install.sh extensions/permission-gate.ts; do
  [[ -e "$required" ]] || fail "$required is missing"
done
[[ -d skills ]] || fail "skills/ is missing"

python3 - <<'PY'
import hashlib
import json
import re
from pathlib import Path

root = Path.cwd()
package = json.loads((root / "package.json").read_text())
assert "pi" not in package, "this snapshot must not advertise incompatible Pi-package installation"
assert package.get("private") is True, "package must remain private to prevent accidental npm publication"

permission_gate = (root / "extensions/permission-gate.ts").read_text()
for contract in [
    'label: "recursive deletion of the current home directory"',
    'label: "recursive deletion with a broad or ambiguous target"',
    'label: "recursive deletion of the filesystem, home, or a protected system root"',
    'label: "recursive deletion of credential-sensitive files"',
    'label: "recursive or forced file deletion"',
    'pi.events.emit("herdr:blocked", { active: true, label })',
    'pi.events.emit("herdr:blocked", { active: false, label })',
    "ctx.ui.confirm(",
    "{ signal: ctx.signal }",
]:
    assert contract in permission_gate, f"permission gate is missing safety contract: {contract}"

skill_files = sorted((root / "skills").glob("*/SKILL.md"))
assert len(skill_files) == 14, f"expected 14 skills, found {len(skill_files)}"
manifest = json.loads((root / "skills-manifest.json").read_text())
assert set(manifest) == {"snapshot", "skills", "files"}, "unexpected skills manifest schema"
assert isinstance(manifest["snapshot"], str) and manifest["snapshot"], "manifest snapshot is required"
assert manifest["skills"] == len(skill_files), "manifest skill count does not match discovered skills"
assert isinstance(manifest["files"], list), "manifest files must be a list"
manifest_paths = [item["path"] for item in manifest["files"]]
assert len(manifest_paths) == len(set(manifest_paths)), "manifest contains duplicate paths"
expected = {item["path"]: item for item in manifest["files"]}
actual_paths = {path.relative_to(root).as_posix() for path in (root / "skills").rglob("*") if path.is_file()}
assert actual_paths == expected.keys(), f"skill file inventory mismatch: {actual_paths ^ expected.keys()}"
ignored_test_roots = {".git", "var", "node_modules"}
test_paths = []
for path in root.rglob("*"):
    if not path.is_file():
        continue
    relative = path.relative_to(root)
    if relative.parts[0] in ignored_test_roots:
        continue
    name = relative.name
    lowered_parts = {part.lower() for part in relative.parts}
    lowered_name = name.lower()
    if (
        lowered_parts.intersection({"test", "tests", "__test__", "__tests__", "spec", "specs", "__spec__", "__specs__"})
        or lowered_name.startswith(("test", "spec"))
        or re.search(r"(^|[._-])(tests?|specs?)([._-]|$)", lowered_name)
        or re.search(r"(Test|Tests|Spec|Specs)\.[^.]+$", name)
    ):
        test_paths.append(relative.as_posix())
assert not sorted(test_paths), f"standalone test files are not part of this repository: {sorted(test_paths)}"
for relative, item in expected.items():
    path = root / relative
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], f"skill checksum mismatch: {relative}"
    assert bool(path.stat().st_mode & 0o111) == item["executable"], f"skill executable mode mismatch: {relative}"
seen = set()
for path in skill_files:
    text = path.read_text()
    assert text.startswith("---\n"), f"missing frontmatter: {path}"
    end = text.find("\n---\n", 4)
    assert end >= 0, f"unterminated frontmatter: {path}"
    frontmatter = text[4:end]
    name_match = re.search(r'^name:\s*["\']?([^"\'\n]+)', frontmatter, re.M)
    description_match = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.M)
    assert name_match, f"missing skill name: {path}"
    assert description_match and description_match.group(1).strip(), f"missing description: {path}"
    name = name_match.group(1).strip()
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name), f"invalid skill name {name}: {path}"
    assert name not in seen, f"duplicate skill name: {name}"
    seen.add(name)

plainspoken_policy = (root / "skills/plainspoken-responses/SKILL.md").read_text()
assert "## Helper-script boundary" not in plainspoken_policy, "the writing-only skill must not impose helper execution policy"
for path in skill_files:
    if path.name == "SKILL.md" and path.parent.name == "plainspoken-responses":
        continue
    text = path.read_text()
    assert "Continue correcting and retrying" in text, f"missing repeatable helper recovery in {path}"
    assert "proven to have made no change" in text, f"helper recovery must require non-mutation proof in {path}"
    assert "retry at most once" not in text, f"fixed helper retry cap remains in {path}"
    assert "stop and report the documentation gap instead of inspecting the script" not in text, f"obsolete unconditional stop policy remains in {path}"

herdr_policy = (root / "skills/herdr/SKILL.md").read_text()
assert "at least `900000` milliseconds (15 minutes)" in herdr_policy, "Herdr must enforce the 15-minute minimum productive subagent wait"
assert "--wait --timeout 900000" in herdr_policy, "Herdr's productive prompt example must use the 15-minute minimum"
for contract in [
    "No Herdr operation performed by these skills may create a fifth pane in any tab.",
    "exactly `ceil(N / 4)` dedicated tabs",
    "14 agents use four tabs: three tabs with four panes and one tab with two panes",
    "Assignment 4 is created by splitting assignment 2's pane `down` (bottom-right).",
    "complete and verify cleanup before resolving or creating its replacement",
    "create the replacement in the root pane of a new unfocused remainder tab",
    "do not close or split a pane while any successful peer there is working",
    "Assignment-to-slot order may change during fallback",
]:
    assert contract in herdr_policy, f"incomplete four-pane Herdr topology contract: {contract}"
readiness_contracts = [
    "herdr pane process-info --pane <returned-pane-id>",
    "exactly one entry whose positive integer PID equals `shell_pid`",
    "Missing, empty, malformed, duplicate, or Boolean PID data is ambiguous and must fail closed.",
    "single clock anchor",
    "never resets the deadline derived from the persisted creation anchor",
    "foreground process-group ID equal to the shell PID is not enough",
    "classify-pane-readiness.py",
    "--expected-pane <returned-pane-id>",
    "--created-at <persisted-pre-create-intent-time>",
    "--previous-input",
    "--previous-classification",
    "A `busy` result is not automatically shell warm-up",
    "If `agent start` returns `agent_pane_busy` after a recorded ready proof",
    "Do not reopen the terminal readiness sequence or retry the start",
    "the pane's process history is ambiguous",
    "Never retry an ambiguous or partial launch.",
]
for contract in readiness_contracts:
    assert contract in herdr_policy, f"incomplete Herdr pane-readiness contract: {contract}"
command_section = herdr_policy.split("## Run an ordinary command in another pane\n", 1)[1].split("\n## Safety and coordination rules", 1)[0]
for contract in ["herdr pane rename", "herdr pane process-info", "classify-pane-readiness.py", "herdr pane run"]:
    assert contract in command_section, f"ordinary-command readiness gate is incomplete: {contract}"
assert command_section.index("classify-pane-readiness.py") < command_section.index("herdr pane run"), "ordinary commands must wait for readiness classification"
phase_policy = (root / "skills/implement/references/phase-machine.md").read_text()
state_schema = (root / "skills/implement/references/state-schema.md").read_text()
for text, label in [(phase_policy, "phase machine"), (state_schema, "state schema")]:
    assert "persisted pre-create intent timestamp" in text, f"{label} must preserve the original readiness deadline"
    assert "agent_pane_busy" in text and "without retry" in text, f"{label} must fail closed when a certified pane becomes busy"
    assert "record-pane-readiness" in text, f"{label} must require typed readiness evidence"
for relative in [
    "skills/agent-review/SKILL.md",
    "skills/design-council/SKILL.md",
    "skills/discuss/SKILL.md",
    "skills/grill-me/SKILL.md",
    "skills/implement/SKILL.md",
    "skills/implement/references/phase-machine.md",
    "skills/ui-ux-grill-me/SKILL.md",
]:
    text = (root / relative).read_text()
    assert "bounded readiness" in text, f"missing bounded pane-readiness recovery in {relative}"
    assert "agent_pane_busy" in text, f"missing post-certification busy handling in {relative}"
for relative in [
    "skills/design-council/SKILL.md",
    "skills/discuss/SKILL.md",
    "skills/grill-me/SKILL.md",
    "skills/ui-ux-grill-me/SKILL.md",
]:
    assert "groups of at most four" in (root / relative).read_text(), f"missing multi-tab four-pane grouping in {relative}"
for relative in ["skills/implement/SKILL.md", "skills/implement/references/phase-machine.md"]:
    text = (root / relative).read_text()
    assert "groups of at most four" in text and "split child two down for child four" in text, f"incomplete implementation 2x2 grouping in {relative}"
agent_review_policy = (root / "skills/agent-review/SKILL.md").read_text()
assert "split it right for architecture" in agent_review_policy and "split the root down for regression" in agent_review_policy, "agent review must use the bounded partial grid"
assert "Close every exact tab created by the wave" in agent_review_policy, "agent review must close every owned review tab"
assert (root / "skills/herdr/scripts/classify-pane-readiness.py").is_file(), "missing pane-readiness classifier"
readiness_state = (root / "skills/implement/scripts/state-store.py").read_text()
for contract in ["event_type == \"record-pane-readiness\"", "pane readiness cannot be recorded before pane creation", "non-monotonic readiness observations", "pane readiness observation time moved backward", "failed_attempt_resources", "exact live parent tab", "parent_tab_id", "cascade-deleted-with-owned-tab", "def validate_readiness_probe_evidence(", "def validate_readiness_probe_transition(", "readiness is not bound to its target pane intent", "readiness does not match the task runtime pane", "current ready pane and its exact live parent tab", "a ready pane snapshot still contains foreground helpers", "PANE_READINESS_TIMEOUT = timedelta(seconds=300)", "valid_readiness_deadline(created_at, deadline_at)", "READINESS_OVERFLOW_REASON", "terminal overflow ambiguity proof", "readiness evidence after a terminal probe", "cannot be rechecked after a terminal proof", "an agent_pane_busy response cannot reopen completed readiness"]:
    assert contract in readiness_state, f"implementation state does not enforce readiness: {contract}"
assert 'or parse_time(readiness["deadline_at"], "pane readiness deadline_at") <= datetime.now(timezone.utc)' not in readiness_state, "a ready proof must not expire while a synchronized launch is being bound"
for contract in ["SUPPORTED_EVENT_TYPES", "DEPRECATED_EVENT_TYPES", "def event_catalog()", "Did you mean", "subparsers.add_parser(\n        \"events\""]:
    assert contract in readiness_state, f"implementation event discovery is incomplete: {contract}"
for contract in ["### Exact root bootstrap sequence", "state-store.py events", "There is no `set-root-contract` event", "Continue correcting and retrying"]:
    assert contract in state_schema, f"implementation bootstrap documentation is incomplete: {contract}"
readiness_classifier = (root / "skills/herdr/scripts/classify-pane-readiness.py").read_text()
for contract in [
    'parser.add_argument(\n        "--deadline-at"',
    'READINESS_TIMEOUT = timedelta(seconds=300)',
    'deadline = created_at + READINESS_TIMEOUT',
    'deadline_text = format_time(deadline)',
    '"--anchor-file"',
    'pane or shell identity changed between readiness snapshots',
    'the readiness clock is earlier than pane creation',
    'readiness observation time moved backward',
    '"observedAt": format_time(now)',
]:
    assert contract in readiness_classifier, f"readiness classifier must derive canonical deadlines: {contract}"
timeout_contracts = [
    "skills/agent-review/SKILL.md",
    "skills/design-council/SKILL.md",
    "skills/discuss/SKILL.md",
    "skills/grill-me/SKILL.md",
    "skills/implement/SKILL.md",
    "skills/implement/references/phase-machine.md",
    "skills/ui-ux-grill-me/SKILL.md",
]
for relative in timeout_contracts:
    assert "`900000` milliseconds (15 minutes)" in (root / relative).read_text(), f"missing 15-minute subagent wait contract: {relative}"

readme = (root / "README.md").read_text()
for name in seen:
    assert f"`{name}`" in readme, f"README does not list {name}"

for markdown in [root / "README.md", root / "THIRD_PARTY_NOTICES.md", root / "SECURITY.md"]:
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", markdown.read_text()):
        target = match.group(1)
        if "://" in target or target.startswith("#"):
            continue
        local = target.split("#", 1)[0]
        assert (root / local).exists(), f"broken local link in {markdown.name}: {target}"

licenses = {
    "browser-use-MIT.txt": "Copyright (c) 2024 Gregor Zunic",
    "visual-explainer-MIT.txt": "Copyright (c) 2025 Nico Bailon",
    "herdr-Apache-2.0.txt": "Apache License",
}
for filename, marker in licenses.items():
    text = (root / "third_party" / "licenses" / filename).read_text()
    assert marker in text, f"invalid or incomplete third-party license: {filename}"
PY

python3 - <<'PY'
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
classifier = Path("skills/herdr/scripts/classify-pane-readiness.py").resolve()
created = "2025-01-01T00:00:00Z"
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    previous = root / "previous.json"
    current = root / "current.json"
    ready = root / "ready.json"
    prior_class = root / "prior-class.json"
    current_class = root / "current-class.json"
    expanded = root / "expanded.json"
    partial = root / "partial.json"
    wrong_pane = root / "wrong-pane.json"
    previous.write_text(json.dumps({
        "id": "cli:pane:process_info",
        "result": {"type": "pane_process_info", "process_info": {
            "pane_id": "w:p1", "shell_pid": 10,
            "foreground_processes": [{"pid": 10, "name": "shell"}, {"pid": 11, "name": "startup"}],
        }},
    }))
    current.write_text(json.dumps({
        "id": "cli:pane:process_info",
        "result": {"type": "pane_process_info", "process_info": {
            "pane_id": "w:p1", "shell_pid": 10,
            "foreground_processes": [{"pid": 10, "name": "shell"}, {"pid": 12, "name": "other"}],
        }},
    }))
    expanded.write_text(json.dumps({
        "id": "cli:pane:process_info",
        "result": {"type": "pane_process_info", "process_info": {
            "pane_id": "w:p1", "shell_pid": 10,
            "foreground_processes": [{"pid": 10, "name": "shell"}, {"pid": 11, "name": "hook"}, {"pid": 12, "name": "activate"}],
        }},
    }))
    partial.write_text(json.dumps({
        "id": "cli:pane:process_info",
        "result": {"type": "pane_process_info", "process_info": {
            "pane_id": "w:p1", "shell_pid": 10,
            "foreground_processes": [{"pid": 10, "name": "shell"}, {"pid": 12, "name": "activate"}],
        }},
    }))
    wrong_pane.write_text(json.dumps({
        "id": "cli:pane:process_info",
        "result": {"type": "pane_process_info", "process_info": {
            "pane_id": "w:wrong", "shell_pid": 10,
            "foreground_processes": [{"pid": 10, "name": "shell"}],
        }},
    }))
    ready.write_text(json.dumps({
        "id": "cli:pane:process_info",
        "result": {"type": "pane_process_info", "process_info": {
            "pane_id": "w:p1", "shell_pid": 10,
            "foreground_processes": [{"pid": 10, "name": "shell"}],
        }},
    }))
    first = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", created, "--now", "2025-01-01T00:00:01Z"],
        text=True, capture_output=True, check=False,
    )
    first_payload = json.loads(first.stdout)
    assert first_payload["classification"] == "busy", "initial shell helper must classify busy"
    prior_class.write_text(first.stdout)
    changed = subprocess.run(
        ["python3", str(classifier), "--input", str(current), "--previous-input", str(previous), "--previous-classification", str(prior_class), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", first_payload["deadlineAt"], "--now", "2025-01-01T00:00:02Z"],
        text=True, capture_output=True, check=False,
    )
    changed_payload = json.loads(changed.stdout)
    assert changed_payload["classification"] == "busy", "sequential startup helper replacement must remain busy"
    current_class.write_text(changed.stdout)
    settled = subprocess.run(
        ["python3", str(classifier), "--input", str(ready), "--previous-input", str(current), "--previous-classification", str(current_class), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", first_payload["deadlineAt"], "--now", "2025-01-01T00:00:03Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(settled.stdout)["classification"] == "ready", "startup helper chain did not settle to the sole shell"
    added = subprocess.run(
        ["python3", str(classifier), "--input", str(expanded), "--previous-input", str(previous), "--previous-classification", str(prior_class), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", first_payload["deadlineAt"], "--now", "2025-01-01T00:00:02Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(added.stdout)["classification"] == "busy", "startup helper addition must remain busy"
    expanded_class = root / "expanded-class.json"
    expanded_class.write_text(added.stdout)
    removed = subprocess.run(
        ["python3", str(classifier), "--input", str(partial), "--previous-input", str(expanded), "--previous-classification", str(expanded_class), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", first_payload["deadlineAt"], "--now", "2025-01-01T00:00:03Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(removed.stdout)["classification"] == "busy", "partial startup helper removal must remain busy"
    wrong = subprocess.run(
        ["python3", str(classifier), "--input", str(wrong_pane), "--previous-input", str(previous), "--previous-classification", str(prior_class), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", first_payload["deadlineAt"], "--now", "2025-01-01T00:00:02Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(wrong.stdout)["classification"] == "ambiguous", "changed pane identity must fail closed"
    almost_expired = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", created, "--now", "2025-01-01T00:04:59Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(almost_expired.stdout)["classification"] == "busy", "busy startup must remain within the 300-second budget"
    expired = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", created, "--now", "2025-01-01T00:05:00Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(expired.stdout)["classification"] == "expired", "busy startup must expire exactly at the 300-second deadline"
    legacy = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", "2025-01-01T00:00:30Z", "--now", "2025-01-01T00:00:29Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(legacy.stdout)["classification"] == "busy", "persisted legacy shorter deadlines must remain valid"
    legacy_expired = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", "2025-01-01T00:00:30Z", "--now", "2025-01-01T00:00:30Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(legacy_expired.stdout)["classification"] == "expired", "persisted legacy deadlines must expire exactly at their recorded boundary"
    too_long = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", "2025-01-01T00:05:00.000001Z", "--now", "2025-01-01T00:00:01Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(too_long.stdout)["classification"] == "ambiguous", "deadlines beyond 300 seconds must fail closed"
    overflow = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", "9999-12-31T23:59:59Z", "--now", "9999-12-31T23:59:59Z"],
        text=True, capture_output=True, check=False,
    )
    overflow_payload = json.loads(overflow.stdout)
    assert overflow_payload["classification"] == "ambiguous" and overflow_payload["reason"] == "derived deadline exceeds the supported timestamp range", "timestamp overflow must fail closed"
    later_first = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", created, "--now", "2025-01-01T00:00:20Z"],
        text=True, capture_output=True, check=False,
    )
    prior_class.write_text(later_first.stdout)
    rolled_recheck = subprocess.run(
        ["python3", str(classifier), "--input", str(current), "--previous-input", str(previous), "--previous-classification", str(prior_class), "--expected-pane", "w:p1", "--created-at", created, "--deadline-at", json.loads(later_first.stdout)["deadlineAt"], "--now", "2025-01-01T00:00:10Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(rolled_recheck.stdout)["classification"] == "ambiguous", "inter-probe clock rollback must fail closed"
    empty = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "", "--created-at", created, "--now", "2025-01-01T00:00:01Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(empty.stdout)["classification"] == "ambiguous", "empty expected pane must fail closed"
    rollback = subprocess.run(
        ["python3", str(classifier), "--input", str(previous), "--expected-pane", "w:p1", "--created-at", "2025-01-01T00:00:10Z", "--now", "2025-01-01T00:00:09Z"],
        text=True, capture_output=True, check=False,
    )
    assert json.loads(rollback.stdout)["classification"] == "ambiguous", "clock rollback before pane creation must fail closed"

    module_path = Path("skills/implement/scripts/state-store.py").resolve()
    spec = importlib.util.spec_from_file_location("inline_state_store_check", module_path)
    assert spec is not None and spec.loader is not None
    store = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(store)
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert store.valid_readiness_deadline(base_time, base_time + timedelta(seconds=30)), "durable state must accept legacy shorter deadlines"
    assert store.valid_readiness_deadline(base_time, base_time + timedelta(seconds=300)), "durable state must accept the 300-second boundary"
    assert not store.valid_readiness_deadline(base_time, base_time + timedelta(seconds=301)), "durable state must reject deadlines over 300 seconds"
    assert not store.valid_readiness_deadline(base_time, base_time), "durable state must reject ordinary zero-length deadlines"
    assert store.valid_readiness_deadline(store.MAX_UTC_TIMESTAMP, store.MAX_UTC_TIMESTAMP), "durable state must preserve the overflow sentinel"
    store.validate_readiness_probe_transition(json.loads(previous.read_text()), json.loads(current.read_text()))
    store.validate_readiness_probe_transition(json.loads(current.read_text()), json.loads(ready.read_text()))
    changed_shell = json.loads(ready.read_text())
    changed_shell["result"]["process_info"]["shell_pid"] = 99
    changed_shell["result"]["process_info"]["foreground_processes"] = [{"pid": 99, "name": "shell"}]
    try:
        store.validate_readiness_probe_transition(json.loads(ready.read_text()), changed_shell)
    except SystemExit:
        pass
    else:
        raise AssertionError("changed shell identity must fail closed")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = lambda value: value.isoformat().replace("+00:00", "Z")
    run = root / "var" / "inline" / "implement"
    state_path = run / "state.json"
    coordinator_session = "inline-coordinator-session"
    os.environ["PI_SESSION_FILE"] = coordinator_session
    state = {
        "feature_name": "inline", "revision": 0, "next_todo_sequence": 1, "updated_at": stamp(now),
        "run": {"repo_root": str(root), "root_task_id": "task-0001", "coordinator_instance_id": coordinator_session, "coordinator_lease": {"id": "lease", "expires_at": stamp(now + timedelta(hours=1))}, "reconciliation_required": False, "status": "running", "phase": "execute", "limits": copy.deepcopy(store.HARD_LIMITS)},
        "integration": {},
        "tasks": {
            "task-0001": {"allow_subagents": True, "updated_at": stamp(now), "runtime_intents": [], "runtime_resources": [{"kind": "tab", "id": "w:t1", "status": "live"}, {"kind": "tab", "id": "w:t2", "status": "live"}, {"kind": "pane", "id": "w:p1", "status": "live", "parent_tab_id": "w:t1"}]},
            "task-0002": {"parent_id": "task-0001", "runtime": {"pane_id": None}},
            "task-0003": {"parent_id": "task-0001", "runtime": {"pane_id": None}},
        },
    }
    pane_intent = {"id": "pane-intent", "kind": "pane", "status": "bound", "resource_id": "w:p1", "created_at": stamp(now), "target_task_id": "task-0003"}
    agent_intent = {"id": "agent-intent", "kind": "agent", "status": "planned", "created_at": stamp(now), "target_task_id": "task-0002"}
    state["tasks"]["task-0001"]["runtime_intents"] = [pane_intent, agent_intent]
    store.validate = lambda *_args, **_kwargs: None
    os.environ["PI_SESSION_FILE"] = "wrong-coordinator-session"
    try:
        store.apply_event(state, state_path, "task-0001", "lease", {"type": "add-todo", "title": "must fail"})
    except SystemExit:
        pass
    else:
        raise AssertionError("root mutation from a different Pi session must fail closed")
    finally:
        os.environ["PI_SESSION_FILE"] = coordinator_session
    state["tasks"]["task-0002"]["runtime"]["agent_instance_id"] = "child-session"
    try:
        store.apply_event(state, state_path, "task-0002", None, {"type": "add-todo", "title": "must fail"})
    except SystemExit:
        pass
    else:
        raise AssertionError("descendant mutation from a different Pi session must fail closed")
    state["tasks"]["task-0002"].update({"status": "working", "todos": [], "updated_at": stamp(now)})
    os.environ["PI_SESSION_FILE"] = "child-session"
    store.apply_event(state, state_path, "task-0002", None, {"type": "add-todo", "title": "child-owned update"})
    os.environ["PI_SESSION_FILE"] = coordinator_session
    assert state["tasks"]["task-0002"]["todos"], "descendant mutation from its recorded Pi session must succeed"
    try:
        store.apply_event(state, state_path, "task-0001", "lease", {"type": "record-pane-readiness", "intent_id": "agent-intent", "pane_intent_id": "pane-intent", "pane_id": "w:p1"})
    except SystemExit:
        pass
    else:
        raise AssertionError("cross-target readiness binding must fail closed")

    pane_intent["target_task_id"] = "task-0002"
    readiness_created = now - timedelta(minutes=6)
    pane_intent["created_at"] = stamp(readiness_created)
    deadline = stamp(readiness_created + timedelta(seconds=300))
    def artifact(name, payload):
        path = run / "outputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
        return {"path": f"outputs/{name}", "digest": hashlib.sha256(path.read_bytes()).hexdigest()}
    future_state = copy.deepcopy(state)
    future_created = now + timedelta(minutes=1)
    future_deadline = future_created + timedelta(seconds=300)
    future_state["tasks"]["task-0001"]["runtime_intents"][0]["created_at"] = stamp(future_created)
    future_snapshot = artifact("future-ready.json", {"id": "cli:pane:process_info", "result": {"type": "pane_process_info", "process_info": {"pane_id": "w:p1", "shell_pid": 10, "foreground_processes": [{"pid": 10, "name": "shell"}]}}})
    future_class = artifact("future-class.json", {"classification": "ready", "reason": "the interactive shell is the sole foreground process", "expectedPane": "w:p1", "createdAt": stamp(future_created), "deadlineAt": stamp(future_deadline), "observedAt": stamp(future_created), "paneId": "w:p1", "shellPid": 10})
    try:
        store.apply_event(future_state, state_path, "task-0001", "lease", {"type": "record-pane-readiness", "intent_id": "agent-intent", "pane_intent_id": "pane-intent", "pane_id": "w:p1", "deadline_at": stamp(future_deadline), "classification": "ready", "snapshot_artifact": future_snapshot, "classification_artifact": future_class})
    except SystemExit:
        pass
    else:
        raise AssertionError("readiness before pane creation must fail closed")

    snapshot = artifact("ready.json", {"id": "cli:pane:process_info", "result": {"type": "pane_process_info", "process_info": {"pane_id": "w:p1", "shell_pid": 10, "foreground_processes": [{"pid": 10, "name": "shell"}]}}})
    classification = artifact("ready-class.json", {"classification": "ready", "reason": "the interactive shell is the sole foreground process", "expectedPane": "w:p1", "createdAt": stamp(readiness_created), "deadlineAt": deadline, "observedAt": stamp(readiness_created + timedelta(seconds=1)), "paneId": "w:p1", "shellPid": 10})
    ready_event = {"type": "record-pane-readiness", "intent_id": "agent-intent", "pane_intent_id": "pane-intent", "pane_id": "w:p1", "deadline_at": deadline, "classification": "ready", "snapshot_artifact": snapshot, "classification_artifact": classification}
    store.apply_event(state, state_path, "task-0001", "lease", ready_event)
    matching_start = artifact("matching-start.json", {"id": "cli:agent:start", "result": {"agent": {"agent": "inline-agent", "pane_id": "w:p1", "tab_id": "w:t1"}}})
    late_bind_state = copy.deepcopy(state)
    late_agent_intent = next(item for item in late_bind_state["tasks"]["task-0001"]["runtime_intents"] if item["id"] == "agent-intent")
    late_agent_intent.update({"response_id_path": "result.agent.agent", "output_path": matching_start["path"]})
    store.apply_event(late_bind_state, state_path, "task-0001", "lease", {"type": "bind-runtime-intent", "intent_id": "agent-intent", "resource": {"kind": "agent", "id": "inline-agent"}, "output_digest": matching_start["digest"]})
    assert any(item.get("kind") == "agent" and item.get("id") == "inline-agent" for item in late_bind_state["tasks"]["task-0001"]["runtime_resources"]), "matching agent launch did not bind after readiness deadline"
    busy_start = artifact("busy-start.json", {"error": {"code": "agent_pane_busy"}})
    retry_event = copy.deepcopy(ready_event)
    retry_event["busy_start_artifact"] = busy_start
    try:
        store.apply_event(state, state_path, "task-0001", "lease", retry_event)
    except SystemExit:
        pass
    else:
        raise AssertionError("ready must remain terminal after agent_pane_busy")
    agent_intent.update({"response_id_path": "result.agent.agent"})
    for filename, start_pane, start_tab, message in [
        ("wrong-pane-start.json", "w:wrong", "w:t1", "launch response for a different pane must fail closed"),
        ("wrong-tab-start.json", "w:p1", "w:t2", "launch response for a different parent tab must fail closed"),
    ]:
        start = artifact(filename, {"id": "cli:agent:start", "result": {"agent": {"agent": "inline-agent", "pane_id": start_pane, "tab_id": start_tab}}})
        agent_intent["output_path"] = start["path"]
        try:
            store.apply_event(state, state_path, "task-0001", "lease", {"type": "bind-runtime-intent", "intent_id": "agent-intent", "resource": {"kind": "agent", "id": "inline-agent"}, "output_digest": start["digest"]})
        except SystemExit:
            pass
        else:
            raise AssertionError(message)
PY

while IFS= read -r -d '' file; do
  case "$file" in
    *.sh) bash -n "$file" ;;
    *.py) python3 - "$file" <<'PY'
import sys
path = sys.argv[1]
compile(open(path, "rb").read(), path, "exec")
PY
      ;;
    *.mjs) node --check "$file" >/dev/null ;;
  esac
done < <(find skills scripts -type f -print0)

python3 - <<'PY'
from pathlib import Path

router = Path("skills/model-routing-policy/scripts/model-routing.py").read_text()
policy = Path("skills/model-routing-policy/SKILL.md").read_text()
herdr = Path("skills/herdr/SKILL.md").read_text()
assert '"--fallback-from"' in router, "router must bind fallback to a prior resolution"
assert '"fallbackFrom": fallback_record' in router, "resolution must preserve fallback provenance"
assert "callers cannot submit an arbitrary exclusion list" in policy, "fallback exclusions must be derived from the verified chain"
assert "user-pinned routing cannot fall back" in router, "user pins must remain fail-closed"
assert "## Automatic fallback routing" in policy, "routing policy must define bounded fallback"
assert "same routing zone" in policy, "fallback must preserve the routing zone"
assert "fresh named pane and fresh Pi session" in policy, "fallback must use a fresh runtime"
assert "--review-complexity" in router and '"reviewComplexity"' in router, "review routing must bind structured complexity"
assert "simple-review fallback remains Sol-only" in policy and "Astra high" in policy, "review model policy must be proportional"
assert "Never start the replacement in a pane that may still contain the failed process" in herdr, "Herdr replacement must isolate failed processes"
state_store = Path("skills/implement/scripts/state-store.py").read_text()
assert 'event_type == "prepare-fallback"' in state_store, "implementation state must own fallback transitions"
assert '"max_retries_per_task"' not in state_store, "fallback must not have a fixed attempt-count ceiling"
assert "attempts must be a non-negative integer" in state_store, "attempt history must remain validated"
for relative in [
    "skills/agent-review/SKILL.md",
    "skills/design-council/SKILL.md",
    "skills/discuss/SKILL.md",
    "skills/grill-me/SKILL.md",
    "skills/implement/SKILL.md",
    "skills/ui-ux-grill-me/SKILL.md",
]:
    text = Path(relative).read_text()
    assert "no-contribution" in text, f"{relative} must distinguish safe fallback from partial work"
PY
python3 - <<'PY'
import json
from pathlib import Path

review = Path("skills/agent-review/SKILL.md").read_text()
implement = Path("skills/implement/SKILL.md").read_text()
validator = Path("skills/implement/scripts/validate-integration-review.sh").read_text()
state_store = Path("skills/implement/scripts/state-store.py").read_text()

for removed in [
    "fingerprint",
    "contract-review-pack",
    "contract preflight",
    "contract-preflight",
    "evidence index",
    "certify-integration",
]:
    assert removed not in review.lower(), f"agent review still requires removed machinery: {removed}"
    assert removed not in implement.lower(), f"implement still requires removed machinery: {removed}"

assert "wave-<n>-correctness.md" in review
assert "wave-<n>-architecture.md" in review
assert "wave-<n>-regression.md" in review
assert "wave-<n>-summary.md" in review
assert "three fresh, read-only Pi agents" in review
assert "validate_integration_ready" in validator
assert "--certify" not in validator
assert '"certify-integration"' not in state_store
assert "def validate_integration_ready(" in state_store
for contract in [
    "def report_footer(",
    "def require_readable_evidence(",
    "minimum_review_wave",
    "review_resources",
    "resume identity must match the calling Pi session",
    "review tabs must be closed before reconciliation finishes",
]:
    assert contract in state_store, f"simplified live integration safety is missing: {contract}"
assert "def live_review_fingerprint(" not in state_store
assert "def recompute_contract_preflight(" not in state_store
assert '"review_target_fingerprint"' not in state_store
assert '"evidence_index"' not in state_store
for removed_path in [
    Path("skills/agent-review/references/contract-preflight.md"),
    Path("skills/agent-review/scripts/review-fingerprint.sh"),
    Path("skills/agent-review/scripts/validate-contract-preflight.py"),
]:
    assert not removed_path.exists(), f"obsolete review helper remains: {removed_path}"

catalog = json.loads(Path("skills/model-routing-policy/models.json").read_text())
by_id = {item["modelId"]: item for item in catalog["models"]}
assert by_id["gpt-5.6-sol"]["routing"]["reviewComplexities"] == ["simple"]
assert by_id["gpt-6-astra"]["routing"]["reviewComplexities"] == ["complicated"]
assert by_id["gpt-6-astra"]["routing"]["reviewThinking"]["complicated"] == "high"
PY

if find skills -type l -print -quit | grep -q .; then
  fail "skills must not contain symlinks"
fi
if find skills -type f \( -name '*.pyc' -o -path '*/__pycache__/*' \) -print -quit | grep -q .; then
  fail "skills contain generated Python bytecode"
fi

python3 - <<'PY'
from pathlib import Path
import re

root = Path.cwd()
ignored_roots = {".git", "var", "node_modules"}
excluded_files = {Path("scripts/check-repo.sh")}
files = []
for path in root.rglob("*"):
    rel = path.relative_to(root)
    if not path.is_file() or any(part in ignored_roots for part in rel.parts) or rel in excluded_files:
        continue
    files.append(rel)

forbidden_names = {".env", "credentials.json", "settings.json", "auth.json"}
for rel in files:
    assert rel.name not in forbidden_names, f"forbidden private/config file: {rel}"

patterns = {
    "Unix/macOS home path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "Windows home path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
    "private key": re.compile(r"BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "Slack token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    "provider secret": re.compile(r"sk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_-]{16,}"),
}
email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
allowed_emails = {"user@example.com", "user@example.org"}

for rel in files:
    try:
        text = (root / rel).read_text()
    except UnicodeDecodeError:
        continue
    for label, pattern in patterns.items():
        match = pattern.search(text)
        assert not match, f"{label} in {rel}: {match.group(0)}"
    for found in email.findall(text):
        assert found.lower() in allowed_emails or found.lower().endswith("@example.com"), f"email address in {rel}: {found}"

negative_fixtures = [
    "/Users/alice/project/file.txt",
    "/home/bob/project/file.txt",
    r"C:\Users\carol\project\file.txt",
    "sk-proj-abcdefghijklmnopqrstuv",
    "ghp_abcdefghijklmnopqrstuvwxyz123456",
]
assert any(patterns["Unix/macOS home path"].search(x) for x in negative_fixtures)
assert patterns["Windows home path"].search(negative_fixtures[2])
assert patterns["provider secret"].search(negative_fixtures[3])
assert patterns["GitHub token"].search(negative_fixtures[4])
PY

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --dry-run >/dev/null
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh >/dev/null
for source_skill in skills/*; do
  name=$(basename "$source_skill")
  diff -qr "$source_skill" "$tmp/agent/skills/$name" >/dev/null || fail "installer copy mismatch: $name"
done
cmp -s extensions/permission-gate.ts "$tmp/agent/extensions/permission-gate.ts" || fail "installer permission-gate copy mismatch"
chmod -x "$tmp/agent/skills/implement/scripts/init-state.sh"
if PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh >/dev/null 2>&1; then
  fail "installer did not detect an executable-mode conflict"
fi
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --force >/dev/null
find "$tmp/agent/skills-backups" -path '*/implement/scripts/init-state.sh' -print -quit | grep -q . || fail "forced install did not back up conflict"
test -x "$tmp/agent/skills/implement/scripts/init-state.sh" || fail "forced install did not restore executable mode"
printf '\nfirst local change\n' >> "$tmp/agent/skills/read-flows/SKILL.md"
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --force >/dev/null
printf '\nsecond local change\n' >> "$tmp/agent/skills/read-flows/SKILL.md"
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --force >/dev/null
backup_count=$(find "$tmp/agent/skills-backups" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
[[ "$backup_count" -ge 3 ]] || fail "forced installs reused a backup directory"
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --uninstall >/dev/null
ln -s "$tmp/missing-skill" "$tmp/agent/skills/read-flows"
if PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh >/dev/null 2>&1; then
  fail "installer did not reject a dangling destination symlink"
fi
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --force >/dev/null
test -f "$tmp/agent/skills/read-flows/SKILL.md" || fail "forced install did not replace dangling symlink safely"
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --uninstall >/dev/null
if find "$tmp/agent/skills" -mindepth 1 -maxdepth 1 -type d -print -quit | grep -q .; then
  fail "uninstall left managed skill directories behind"
fi
[[ ! -e "$tmp/agent/extensions/permission-gate.ts" ]] || fail "uninstall left the managed permission gate behind"

printf 'PASS: skills, licenses, links, scripts, installer safety, portability, and sensitive-data checks\n'
