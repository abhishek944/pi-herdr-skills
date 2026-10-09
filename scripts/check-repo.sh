#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

for source_skill in "$repo_root"/skills/*; do
  [[ -d "$source_skill" ]] || continue
  name=$(basename "$source_skill")
  installed_skill="$HOME/.agents/skills/$name"
  [[ -d "$installed_skill" ]] || fail "missing global skill: $installed_skill"
  diff -qr "$source_skill" "$installed_skill" >/dev/null || fail "global skill differs: $name"
done

printf 'PASS: repository skills match shared global skills\n'
