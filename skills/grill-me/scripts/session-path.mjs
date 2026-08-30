import fs from "node:fs";
import path from "node:path";

const varRoot = path.resolve("var");
const kebab = /^[a-z0-9][a-z0-9-]*$/;

export function resolveSessionSlug(feature, slug) {
  if (!kebab.test(feature)) {
    throw new Error(
      "Feature name must use lowercase letters, numbers, and hyphens only",
    );
  }
  if (!kebab.test(slug)) {
    throw new Error(
      "Session slug must use lowercase letters, numbers, and hyphens only",
    );
  }
  return resolveSessionDir(
    path.join(varRoot, feature, "grill-me", slug),
    false,
  );
}

export function resolveSessionDir(input, requireExisting = true) {
  const resolved = path.resolve(input);
  assertFeatureSession(resolved);
  assertExistingAncestorContained(resolved);
  if (requireExisting && !fs.existsSync(resolved)) {
    throw new Error(`Grill-me session directory does not exist: ${resolved}`);
  }
  if (fs.existsSync(resolved)) {
    assertFeatureSession(fs.realpathSync(resolved));
  }
  return resolved;
}

function assertExistingAncestorContained(candidate) {
  let ancestor = candidate;
  while (!fs.existsSync(ancestor)) {
    const parent = path.dirname(ancestor);
    if (parent === ancestor)
      throw new Error("Could not find an existing Grill-me session ancestor");
    ancestor = parent;
  }
  const realVarRoot = fs.realpathSync(varRoot);
  const realAncestor = fs.realpathSync(ancestor);
  const relative = path.relative(realVarRoot, realAncestor);
  if (
    path.isAbsolute(relative) ||
    relative === ".." ||
    relative.startsWith(`..${path.sep}`)
  ) {
    throw new Error(
      "Grill-me session ancestors must stay inside the repository var directory",
    );
  }
}

function assertFeatureSession(candidate) {
  const relative = path.relative(varRoot, candidate);
  const parts = relative.split(path.sep);
  if (
    path.isAbsolute(relative) ||
    parts.length !== 3 ||
    !kebab.test(parts[0]) ||
    parts[1] !== "grill-me" ||
    !kebab.test(parts[2])
  ) {
    throw new Error(
      "Grill-me sessions must use var/<feature-name>/grill-me/<session-slug>",
    );
  }
}
