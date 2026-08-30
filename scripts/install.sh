#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_root="$repo_root/skills"
agent_dir=${PI_CODING_AGENT_DIR:-"$HOME/.pi/agent"}
destination="$agent_dir/skills"
mode=install
force=0
dry_run=0

usage() {
  cat <<'EOF'
Usage: scripts/install.sh [--force] [--dry-run] [--uninstall]

Installs this repository's skills into Pi's global skill directory.

  --dry-run    Show what would change.
  --force      Back up and replace conflicting skill directories.
  --uninstall  Remove matching installed skills. Modified skills require --force
               and are backed up before removal.

Set PI_CODING_AGENT_DIR to use a non-default Pi agent directory.
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

if [[ ${#conflicts[@]} -gt 0 && $force -eq 0 ]]; then
  printf 'Refusing to overwrite modified or different skills:\n' >&2
  printf '  %s\n' "${conflicts[@]}" >&2
  printf 'Review the differences, then rerun with --force to create a backup first.\n' >&2
  exit 1
fi

backup_root=""
if [[ ${#conflicts[@]} -gt 0 ]]; then
  backup_parent="$agent_dir/skills-backups"
  if [[ $dry_run -eq 1 ]]; then
    backup_root="$backup_parent/pi-herdr-skills-<unique>"
    echo "Would back up conflicts to: $backup_root"
  else
    mkdir -p "$backup_parent"
    backup_root=$(mktemp -d "$backup_parent/pi-herdr-skills-XXXXXXXX")
    for name in "${conflicts[@]}"; do
      cp -R -p "$destination/$name" "$backup_root/$name"
    done
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

echo "Done. Restart Pi or run /reload in an existing Pi session."
