#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

for required in package.json README.md LICENSE SECURITY.md THIRD_PARTY_NOTICES.md scripts/install.sh; do
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

skill_files = sorted((root / "skills").glob("*/SKILL.md"))
assert len(skill_files) == 13, f"expected 13 skills, found {len(skill_files)}"
manifest = json.loads((root / "skills-manifest.json").read_text())
expected = {item["path"]: item for item in manifest["files"]}
actual_paths = {path.relative_to(root).as_posix() for path in (root / "skills").rglob("*") if path.is_file()}
assert actual_paths == expected.keys(), f"skill file inventory mismatch: {actual_paths ^ expected.keys()}"
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

printf 'PASS: skills, licenses, links, scripts, installer safety, portability, and sensitive-data checks\n'
