#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_root="$repo_root/skills"
permission_config_source="$repo_root/config/pi-permission-system.json"
permission_package="npm:@gotgenes/pi-permission-system@33.0.1"
agent_dir=${PI_CODING_AGENT_DIR:-"$HOME/.pi/agent"}
destination="$HOME/.agents/skills"
permission_config_destination="$agent_dir/extensions/pi-permission-system/config.json"
legacy_extension_destination="$agent_dir/extensions/permission-gate.ts"
mode=install
force=0
dry_run=0

usage() {
  cat <<'EOF'
Usage: scripts/install.sh [--force] [--dry-run] [--uninstall]

Installs skills into ~/.agents/skills and the pi-permission-system policy into Pi's global agent directory.

Prerequisite: pi install npm:@gotgenes/pi-permission-system@33.0.1

  --dry-run    Show what would change.
  --force      Back up and replace conflicting managed files.
  --uninstall  Remove matching installed skills and policy. Modified files require
               --force and are backed up before removal. The Pi package is retained.

Set PI_CODING_AGENT_DIR to use a non-default Pi agent directory for the policy.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    --dry-run) dry_run=1 ;;
    --uninstall) mode=uninstall ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

[[ -d "$source_root" ]] || { echo "Missing skills directory: $source_root" >&2; exit 1; }
[[ -f "$permission_config_source" ]] || { echo "Missing permission policy: $permission_config_source" >&2; exit 1; }

trees_equal() {
  python3 - "$1" "$2" <<'PY'
from pathlib import Path
import hashlib
import os
import stat
import sys

left, right = map(Path, sys.argv[1:])
if not left.is_dir() or not right.is_dir():
    raise SystemExit(1)

def entries(root):
    return {path.relative_to(root): path for path in root.rglob("*")}

a, b = entries(left), entries(right)
if a.keys() != b.keys():
    raise SystemExit(1)
for rel, first in a.items():
    second = b[rel]
    first_stat, second_stat = first.lstat(), second.lstat()
    if stat.S_IFMT(first_stat.st_mode) != stat.S_IFMT(second_stat.st_mode):
        raise SystemExit(1)
    if stat.S_ISREG(first_stat.st_mode):
        if (first_stat.st_mode & 0o111) != (second_stat.st_mode & 0o111):
            raise SystemExit(1)
        if hashlib.sha256(first.read_bytes()).digest() != hashlib.sha256(second.read_bytes()).digest():
            raise SystemExit(1)
    elif stat.S_ISLNK(first_stat.st_mode):
        if os.readlink(first) != os.readlink(second):
            raise SystemExit(1)
PY
}

package_installed=$(python3 - "$agent_dir/settings.json" "$permission_package" <<'PY'
import json
from pathlib import Path
import sys

settings_path = Path(sys.argv[1])
expected = sys.argv[2]
if not settings_path.is_file():
    print("no")
    raise SystemExit
try:
    packages = json.loads(settings_path.read_text()).get("packages", [])
except (OSError, ValueError):
    print("no")
    raise SystemExit
for package in packages:
    if package == expected:
        print("yes")
        break
else:
    print("no")
PY
)
if [[ $mode == install && $package_installed != yes ]]; then
  printf 'Required enabled Pi package is not installed at the pinned version. Run:\n  pi install %s\n' "$permission_package" >&2
  exit 1
fi

skill_names=()
while IFS= read -r line; do
  skill_names+=("$line")
done < <(find "$source_root" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | LC_ALL=C sort)
[[ ${#skill_names[@]} -gt 0 ]] || { echo "No skills found." >&2; exit 1; }

conflicts=()
for name in "${skill_names[@]}"; do
  target="$destination/$name"
  [[ -e "$target" || -L "$target" ]] || continue
  if ! trees_equal "$source_root/$name" "$target"; then
    conflicts+=("$name")
  fi
done

permission_config_conflict=0
if [[ -e "$permission_config_destination" || -L "$permission_config_destination" ]]; then
  if [[ ! -f "$permission_config_destination" ]] || ! cmp -s "$permission_config_source" "$permission_config_destination"; then
    permission_config_conflict=1
  fi
fi

legacy_extension_present=0
if [[ -e "$legacy_extension_destination" || -L "$legacy_extension_destination" ]]; then
  legacy_extension_present=1
fi

if [[ ${#conflicts[@]} -gt 0 || $permission_config_conflict -eq 1 ]]; then
  if [[ $force -eq 0 ]]; then
    printf 'Refusing to overwrite modified or different managed files:\n' >&2
    if [[ ${#conflicts[@]} -gt 0 ]]; then
      printf '  skill: %s\n' "${conflicts[@]}" >&2
    fi
    [[ $permission_config_conflict -eq 0 ]] || printf '  policy: pi-permission-system/config.json\n' >&2
    printf 'Review the differences, then rerun with --force to create a backup first.\n' >&2
    exit 1
  fi
fi

backup_root=""
if [[ ${#conflicts[@]} -gt 0 || $permission_config_conflict -eq 1 || $legacy_extension_present -eq 1 ]]; then
  backup_parent="$agent_dir/skills-backups"
  if [[ $dry_run -eq 1 ]]; then
    backup_root="$backup_parent/pi-herdr-skills-<unique>"
    echo "Would back up conflicts to: $backup_root"
  else
    mkdir -p "$backup_parent"
    backup_root=$(mktemp -d "$backup_parent/pi-herdr-skills-XXXXXXXX")
    if [[ ${#conflicts[@]} -gt 0 ]]; then
      for name in "${conflicts[@]}"; do
        cp -R -p "$destination/$name" "$backup_root/$name"
      done
    fi
    if [[ $permission_config_conflict -eq 1 ]]; then
      mkdir -p "$backup_root/extensions/pi-permission-system"
      cp -R -p "$permission_config_destination" "$backup_root/extensions/pi-permission-system/config.json"
    fi
    if [[ $legacy_extension_present -eq 1 ]]; then
      mkdir -p "$backup_root/extensions"
      cp -R -p "$legacy_extension_destination" "$backup_root/extensions/permission-gate.ts"
    fi
    echo "Backed up conflicts to: $backup_root"
  fi
fi

if [[ $mode == uninstall ]]; then
  for name in "${skill_names[@]}"; do
    target="$destination/$name"
    [[ -e "$target" || -L "$target" ]] || continue
    if [[ $dry_run -eq 1 ]]; then
      echo "Would remove: $target"
    else
      rm -rf -- "$target"
      echo "Removed: $target"
    fi
  done
  for managed_file in "$permission_config_destination" "$legacy_extension_destination"; do
    [[ -e "$managed_file" || -L "$managed_file" ]] || continue
    if [[ $dry_run -eq 1 ]]; then
      echo "Would remove: $managed_file"
    else
      rm -rf -- "$managed_file"
      echo "Removed: $managed_file"
    fi
  done
  exit 0
fi

if [[ $dry_run -eq 0 ]]; then
  mkdir -p "$destination"
fi
for name in "${skill_names[@]}"; do
  source_skill="$source_root/$name"
  target="$destination/$name"
  if [[ -d "$target" ]] && trees_equal "$source_skill" "$target"; then
    echo "Already current: $name"
    continue
  fi
  if [[ $dry_run -eq 1 ]]; then
    echo "Would install: $name -> $target"
    continue
  fi
  staging="$destination/.pi-herdr-skills-$name-$$"
  rm -rf -- "$staging"
  cp -R -p "$source_skill" "$staging"
  rm -rf -- "$target"
  mv "$staging" "$target"
  echo "Installed: $name"
done

if [[ -f "$permission_config_destination" ]] && cmp -s "$permission_config_source" "$permission_config_destination"; then
  echo "Already current: pi-permission-system policy"
elif [[ $dry_run -eq 1 ]]; then
  echo "Would install: pi-permission-system policy -> $permission_config_destination"
else
  mkdir -p "$(dirname "$permission_config_destination")"
  permission_staging="$permission_config_destination.$$"
  cp -p "$permission_config_source" "$permission_staging"
  rm -rf -- "$permission_config_destination"
  mv "$permission_staging" "$permission_config_destination"
  echo "Installed: pi-permission-system policy"
fi

if [[ $legacy_extension_present -eq 1 ]]; then
  if [[ $dry_run -eq 1 ]]; then
    echo "Would retire: $legacy_extension_destination"
  else
    rm -rf -- "$legacy_extension_destination"
    echo "Retired: $legacy_extension_destination"
  fi
fi

echo "Done. Restart Pi or run /reload in an existing Pi session."
