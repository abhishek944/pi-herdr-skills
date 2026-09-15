#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

for required in package.json README.md LICENSE SECURITY.md THIRD_PARTY_NOTICES.md scripts/install.sh extensions/permission-gate.ts skills-manifest.json; do
  [[ -e "$required" ]] || fail "$required is missing"
done

python3 - <<'PY'
import hashlib
import json
import re
from pathlib import Path

root = Path.cwd()
package = json.loads((root / "package.json").read_text())
assert package.get("private") is True, "package must remain private"
assert "pi" not in package, "this repository is installed with its installer"

permission_gate = (root / "extensions/permission-gate.ts").read_text()
for text in [
    'label: "recursive deletion of the current home directory"',
    'label: "recursive deletion with a broad or ambiguous target"',
    'label: "recursive deletion of credential-sensitive files"',
    'pi.events.emit("herdr:blocked", { active: true, label })',
    'pi.events.emit("herdr:blocked", { active: false, label })',
    "ctx.ui.confirm(",
]:
    assert text in permission_gate, f"permission gate is missing: {text}"

skill_files = sorted((root / "skills").glob("*/SKILL.md"))
assert len(skill_files) == 14, f"expected 14 skills, found {len(skill_files)}"

names = set()
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
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name), f"invalid skill name: {name}"
    assert name == path.parent.name, f"skill folder/name mismatch: {path}"
    assert name not in names, f"duplicate skill name: {name}"
    names.add(name)

for path in (root / "skills").rglob("*"):
    assert not path.is_symlink(), f"skill content must not be a symlink: {path}"

manifest = json.loads((root / "skills-manifest.json").read_text())
assert set(manifest) == {"snapshot", "skills", "files"}, "unexpected manifest schema"
assert manifest["skills"] == 14, "manifest skill count mismatch"
expected = {item["path"]: item for item in manifest["files"]}
actual = {
    path.relative_to(root).as_posix(): path
    for path in (root / "skills").rglob("*")
    if path.is_file()
}
assert actual.keys() == expected.keys(), f"manifest inventory mismatch: {actual.keys() ^ expected.keys()}"
for relative, path in actual.items():
    item = expected[relative]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], f"checksum mismatch: {relative}"
    assert bool(path.stat().st_mode & 0o111) == item["executable"], f"mode mismatch: {relative}"

readme = (root / "README.md").read_text()
for name in names:
    assert f"`{name}`" in readme, f"README does not list {name}"

for markdown in [root / "README.md", root / "THIRD_PARTY_NOTICES.md", root / "SECURITY.md"]:
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", markdown.read_text()):
        target = match.group(1)
        if "://" in target or target.startswith("#"):
            continue
        local = target.split("#", 1)[0]
        assert (root / local).exists(), f"broken local link in {markdown.name}: {target}"

ignored = {".git", "var", "node_modules"}
patterns = {
    "home path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "private key": re.compile(r"BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY"),
    "provider secret": re.compile(r"sk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_-]{16,}"),
}
for path in root.rglob("*"):
    if not path.is_file() or any(part in ignored for part in path.relative_to(root).parts) or path == root / "scripts/check-repo.sh":
        continue
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        continue
    for label, pattern in patterns.items():
        assert not pattern.search(text), f"{label} found in {path.relative_to(root)}"
PY

bash -n scripts/install.sh
bash -n scripts/check-repo.sh

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --dry-run >/dev/null
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh >/dev/null
for source_skill in skills/*; do
  name=$(basename "$source_skill")
  diff -qr "$source_skill" "$tmp/agent/skills/$name" >/dev/null || fail "installer copy mismatch: $name"
done
cmp -s extensions/permission-gate.ts "$tmp/agent/extensions/permission-gate.ts" || fail "installer extension copy mismatch"
printf '\nlocal change\n' >> "$tmp/agent/skills/read-flows/SKILL.md"
if PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh >/dev/null 2>&1; then
  fail "installer did not detect a conflict"
fi
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --force >/dev/null
PI_CODING_AGENT_DIR="$tmp/agent" scripts/install.sh --uninstall >/dev/null

printf 'PASS: repository structure, manifest, safety, portability, and installer checks\n'
