#!/usr/bin/env bash
set -euo pipefail

FEATURE_NAME="${1:-}"
if [[ ! "$FEATURE_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ || $# -ne 1 ]]; then
  echo "Usage: $0 <feature-name>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_STORE="$SCRIPT_DIR/state-store.py"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "FAIL: run this command inside a Git repository" >&2
  exit 1
}
STATE="$REPO_ROOT/var/$FEATURE_NAME/implement/state.json"

if [[ ! -f "$STATE" ]]; then
  echo "FAIL: implementation state does not exist: $STATE" >&2
  exit 1
fi

python3 "$STATE_STORE" validate "$STATE" >/dev/null
PYTHONDONTWRITEBYTECODE=1 python3 - "$STATE_STORE" "$STATE" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

store_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("implement_state_store", store_path)
if spec is None or spec.loader is None:
    raise SystemExit("FAIL: could not load implementation state helper")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
state = json.loads(state_path.read_text(encoding="utf-8"))
module.validate(state, state_path)
module.validate_integration_ready(state)
print("PASS: implementation checks, behavior handoff, changed files, and review reports are ready")
PY
