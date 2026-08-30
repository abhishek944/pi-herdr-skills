#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
base_ref="HEAD"
target_ref="WORKTREE"
format="hash"
scopes=()

usage() {
  cat >&2 <<'EOF'
Usage: review-fingerprint.sh [--base REF] [--target REF|WORKTREE] [--scope PATH ...] [--format hash|json]

The default target is the current index and worktree relative to HEAD. Scope
paths must be repository-relative. The JSON format reports the resolved base,
target, and normalized scope that must be persisted with the fingerprint.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) base_ref="${2:-}"; shift 2 ;;
    --target) target_ref="${2:-}"; shift 2 ;;
    --scope) scopes+=("${2:-}"); shift 2 ;;
    --format) format="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done

if [[ -z "$base_ref" || -z "$target_ref" || ( "$format" != "hash" && "$format" != "json" ) ]]; then
  usage
  exit 2
fi

if [[ ${#scopes[@]} -eq 0 ]]; then
  scopes=(".")
fi

python3 - "$repo_root" "$base_ref" "$target_ref" "$format" "${scopes[@]}" <<'PY'
import hashlib
import json
import os
import posixpath
import stat
import subprocess
import sys

root, base_ref, target_ref, output_format, *raw_scopes = sys.argv[1:]

def git(*args):
    return subprocess.check_output(["git", "-C", root, *args])

def resolve_commit(ref):
    try:
        return git("rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    except subprocess.CalledProcessError:
        raise SystemExit(f"FAIL: review ref does not resolve to a commit: {ref}")

def normalize_scope(raw):
    raw = raw.replace("\\", "/").strip()
    normalized = posixpath.normpath(raw or ".")
    if normalized.startswith("/") or normalized == ".." or normalized.startswith("../"):
        raise SystemExit(f"FAIL: review scope must stay inside the repository: {raw}")
    return normalized

base_sha = resolve_commit(base_ref)
target_is_worktree = target_ref.upper() == "WORKTREE"
target_sha = None if target_is_worktree else resolve_commit(target_ref)
scopes = sorted(set(normalize_scope(scope) for scope in raw_scopes))
pathspec = ["--", *scopes]

digest = hashlib.sha256()
digest.update(b"BASE\0")
digest.update(base_sha.encode())
digest.update(b"\0TARGET\0")
digest.update(("WORKTREE" if target_is_worktree else target_sha).encode())
for scope in scopes:
    digest.update(b"\0SCOPE\0")
    digest.update(scope.encode())

if target_is_worktree:
    digest.update(b"\0DIFF\0")
    digest.update(git("diff", "--binary", "--no-ext-diff", base_sha, *pathspec))
    untracked = git("ls-files", "--others", "--exclude-standard", "-z", *pathspec).split(b"\0")
    for raw_path in sorted(path for path in untracked if path):
        path = raw_path.decode("utf-8", "surrogateescape")
        file_stat = os.lstat(os.path.join(root, path))
        digest.update(b"\0UNTRACKED\0")
        digest.update(raw_path)
        digest.update(b"\0")
        digest.update(oct(stat.S_IFMT(file_stat.st_mode) | stat.S_IMODE(file_stat.st_mode)).encode())
        digest.update(b"\0")
        if stat.S_ISLNK(file_stat.st_mode):
            digest.update(os.readlink(os.path.join(root, path)).encode("utf-8", "surrogateescape"))
        elif stat.S_ISREG(file_stat.st_mode):
            with open(os.path.join(root, path), "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            raise SystemExit(f"FAIL: unsupported untracked file type: {path}")
else:
    digest.update(b"\0DIFF\0")
    digest.update(git("diff", "--binary", "--no-ext-diff", base_sha, target_sha, *pathspec))

result = {
    "fingerprint": digest.hexdigest(),
    "base_ref": base_ref,
    "base_sha": base_sha,
    "target_ref": "WORKTREE" if target_is_worktree else target_ref,
    "target_sha": target_sha,
    "scope": scopes,
}
print(result["fingerprint"] if output_format == "hash" else json.dumps(result, sort_keys=True))
PY
