#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
agent_dir=${PI_CODING_AGENT_DIR:-"$HOME/.pi/agent"}

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

source_config="$repo_root/config/pi-permission-system.json"
installed_config="$agent_dir/extensions/pi-permission-system/config.json"
[[ -f "$source_config" ]] || fail "missing repository config: $source_config"
[[ -f "$installed_config" ]] || fail "missing global config: $installed_config"
cmp -s "$source_config" "$installed_config" || fail "global permission config differs"

printf 'PASS: repository skills match shared global skills and permission config matches Pi\n'
