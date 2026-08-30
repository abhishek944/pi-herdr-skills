#!/usr/bin/env bash
# Bootstrap one atomic recursive state tree under var/<feature-name>/implement/.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
FEATURE_NAME="${1:-}"
ACTION="${2:-}"
OWNER_TOKEN_ARG="${IMPLEMENT_TASK_CAPABILITY:-}"
LEASE_ID_ARG="${IMPLEMENT_COORDINATOR_LEASE_ID:-}"
STATE_DIR="$ROOT/var/$FEATURE_NAME/implement"
STATE_FILE="$STATE_DIR/state.json"
CLAIM_DIR="$ROOT/var/$FEATURE_NAME/.implement-coordinator-claim"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "Usage: $0 <feature-name> [--resume] (resume credentials come from IMPLEMENT_TASK_CAPABILITY and IMPLEMENT_COORDINATOR_LEASE_ID)" >&2
}

if [[ ! "$FEATURE_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  usage
  echo "feature-name must be lowercase kebab-case" >&2
  exit 2
fi
if [[ -n "$ACTION" && "$ACTION" != "--resume" ]]; then
  usage
  exit 2
fi
if ! git -C "$ROOT" check-ignore -q "var/.implement-state-probe" 2>/dev/null; then
  echo "FAIL: var/ must be ignored by Git before implement state is created" >&2
  exit 1
fi
for candidate in "$ROOT/var" "$ROOT/var/$FEATURE_NAME" "$STATE_DIR"; do
  if [[ -L "$candidate" ]]; then
    echo "FAIL: implementation state paths cannot use symbolic links: $candidate" >&2
    exit 1
  fi
done

if [[ "$ACTION" == "--resume" ]]; then
  if [[ -z "$OWNER_TOKEN_ARG" || -z "$LEASE_ID_ARG" ]]; then
    echo "FAIL: resume requires the owner token and coordinator lease ID printed when the run was created" >&2
    exit 1
  fi
  if [[ ! -f "$STATE_FILE" ]]; then
    if [[ -f "$STATE_DIR/loop.json" ]]; then
      echo "FAIL: this is legacy version 3 state. Do not convert or resume it automatically." >&2
      echo "Finish it with the earlier one-level workflow or start a separately named version 4 run." >&2
    else
      echo "FAIL: no recursive implementation state exists for '$FEATURE_NAME'" >&2
    fi
    exit 1
  fi
  IMPLEMENT_TASK_CAPABILITY="$OWNER_TOKEN_ARG" IMPLEMENT_COORDINATOR_LEASE_ID="$LEASE_ID_ARG" \
    python3 "$SCRIPT_DIR/state-store.py" resume "$STATE_FILE" --feature "$FEATURE_NAME"
  exit 0
fi

if [[ -e "$STATE_DIR" ]]; then
  echo "FAIL: an implementation run already exists for '$FEATURE_NAME'" >&2
  echo "Inspect it first, then use --resume only for the same version 4 run." >&2
  exit 1
fi

mkdir -p "$ROOT/var/$FEATURE_NAME"
if [[ -d "$CLAIM_DIR" ]]; then
  claim_pid="$(cat "$CLAIM_DIR/pid" 2>/dev/null || true)"
  claim_age="$(python3 - "$CLAIM_DIR" <<'PY'
import os, sys, time
print(int(time.time() - os.stat(sys.argv[1]).st_mtime))
PY
)"
  if [[ "$claim_pid" =~ ^[0-9]+$ ]] && kill -0 "$claim_pid" 2>/dev/null; then
    echo "FAIL: another coordinator is initializing '$FEATURE_NAME'" >&2
    exit 1
  fi
  if (( claim_age < 300 )); then
    echo "FAIL: a recent initialization claim exists; retry after five minutes if its process was interrupted" >&2
    exit 1
  fi
  rm -rf "$CLAIM_DIR"
fi
if ! mkdir "$CLAIM_DIR" 2>/dev/null; then
  echo "FAIL: another coordinator is initializing '$FEATURE_NAME'" >&2
  exit 1
fi
printf '%s\n' "$$" > "$CLAIM_DIR/pid"
printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$CLAIM_DIR/started-at"
cleanup() {
  rm -rf "$CLAIM_DIR" 2>/dev/null || true
}
trap cleanup EXIT

STAGE_DIR="$(mktemp -d "$ROOT/var/$FEATURE_NAME/.implement-init.XXXXXX")"
OWNER_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
LEASE_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
COORDINATOR_INSTANCE_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
if ! BASE_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)"; then
  echo "FAIL: implement state requires a repository with an initial commit" >&2
  exit 1
fi
mkdir -p "$STAGE_DIR/evidence" "$STAGE_DIR/outputs" "$STAGE_DIR/reviews"
IMPLEMENT_TASK_CAPABILITY="$OWNER_TOKEN" IMPLEMENT_COORDINATOR_LEASE_ID="$LEASE_ID" \
python3 "$SCRIPT_DIR/state-store.py" init "$STAGE_DIR/state.json" \
  --feature "$FEATURE_NAME" \
  --coordinator-instance-id "$COORDINATOR_INSTANCE_ID" \
  --base-commit "$BASE_COMMIT" \
  --repo-root "$ROOT" \
  --canonical-path "$STATE_FILE" >/dev/null

if [[ -e "$STATE_DIR" ]]; then
  rm -rf "$STAGE_DIR"
  echo "FAIL: implementation state appeared while initializing: $STATE_DIR" >&2
  exit 1
fi
mv "$STAGE_DIR" "$STATE_DIR"
trap - EXIT
rm -rf "$CLAIM_DIR"

printf 'State directory: %s\n' "$STATE_DIR"
printf 'State file: %s\n' "$STATE_FILE"
printf 'Owner token: %s\n' "$OWNER_TOKEN"
printf 'Coordinator lease ID: %s\n' "$LEASE_ID"
printf 'Coordinator instance ID: %s\n' "$COORDINATOR_INSTANCE_ID"
printf 'Set IMPLEMENT_TASK_CAPABILITY and IMPLEMENT_COORDINATOR_LEASE_ID for root state updates.\n'
