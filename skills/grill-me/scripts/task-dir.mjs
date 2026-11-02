import fs from "node:fs";
import path from "node:path";

const varRoot = path.resolve("var");
const sessionIdPattern = /^[A-Za-z0-9][A-Za-z0-9_-]*$/;
const workIdPattern = /^W[1-9][0-9]*$/;
const taskIdPattern = /^T[1-9][0-9]*$/;

/**
 * Resolve and validate the explicit canonical owner task directory used by
 * every grill-me helper. Root owners use var/<sessionId>/<workId>/<taskId>/;
 * delegated owners append their own triple beneath the exact parent task
 * directory, recursively. Feature names and interview slugs never select a
 * directory.
 */
export function resolveTaskDir(input, { requireExisting = true } = {}) {
  if (typeof input !== "string" || !input.trim()) {
    throw new Error(
      "A canonical task directory is required: --dir <taskDir>",
    );
  }
  const resolved = path.resolve(input);
  const relative = path.relative(varRoot, resolved);
  if (isOutside(relative)) {
    throw new Error(
      `Grill-me task directories must stay inside the repository var directory: ${resolved}`,
    );
  }
  assertOwnerTriples(relative, resolved);
  const realRelative = path.relative(realpathWithTail(varRoot), realpathWithTail(resolved));
  if (isOutside(realRelative)) {
    throw new Error(
      `Grill-me task directories must resolve inside the repository var directory: ${resolved}`,
    );
  }
  assertOwnerTriples(realRelative, resolved);
  if (requireExisting && !fs.existsSync(resolved)) {
    throw new Error(`Grill-me task directory does not exist: ${resolved}`);
  }
  return resolved;
}

/** Default display label: the owner task ID of the canonical directory. */
export function taskLabel(dir) {
  const relative = path.relative(varRoot, path.resolve(dir));
  const segments = relative === "" ? [] : relative.split(path.sep);
  return segments[segments.length - 1] || "task";
}

/**
 * Resolve an existing file or directory that must stay inside the owner task
 * directory, following real paths so a symlink cannot escape it.
 */
export function insideTaskDir(dir, candidate) {
  const root = path.resolve(dir);
  const full = path.resolve(root, candidate);
  if (isOutside(path.relative(root, full)) || !fs.existsSync(full)) return null;
  const relative = path.relative(fs.realpathSync(root), fs.realpathSync(full));
  if (isOutside(relative)) return null;
  return { path: full, relative: relative.split(path.sep).join("/") };
}

/**
 * Resolve a helper-owned write target (generated page, capture, response or
 * server file) and require it to stay inside the owner task directory.
 * Existing aliases are followed through their real paths, so an escaping
 * symlink is rejected before any mkdir or write; a valid contained alias and
 * a not-yet-created tail are preserved. Callers must mkdir/write only the
 * returned path, and only after this check.
 */
export function resolveWriteTarget(dir, candidate) {
  const root = path.resolve(dir);
  const full = path.resolve(root, candidate);
  const realRoot = realpathWithTail(root);
  let realTarget;
  try {
    realTarget = realpathWithTail(full);
  } catch {
    throw new Error(
      `Grill-me write targets cannot resolve through this path: ${full}`,
    );
  }
  if (isOutside(path.relative(realRoot, realTarget))) {
    throw new Error(
      `Grill-me write targets must stay inside the owner task directory: ${full}`,
    );
  }
  return full;
}

function assertOwnerTriples(relative, resolved) {
  const segments = relative === "" ? [] : relative.split(path.sep);
  const valid =
    segments.length >= 3 &&
    segments.length % 3 === 0 &&
    segments.every((segment, index) => {
      if (index % 3 === 0) return sessionIdPattern.test(segment);
      if (index % 3 === 1) return workIdPattern.test(segment);
      return taskIdPattern.test(segment);
    });
  if (!valid) {
    throw new Error(
      `Grill-me task directories must use var/<sessionId>/<Wn>/<Tn>/, or append a nested <sessionId>/<Wn>/<Tn> triple beneath a delegated parent task directory: ${resolved}`,
    );
  }
}

function realpathWithTail(target) {
  const tail = [];
  let current = target;
  while (!pathExists(current)) {
    const parent = path.dirname(current);
    if (parent === current) {
      throw new Error(
        `Could not resolve an existing ancestor for the task directory: ${target}`,
      );
    }
    tail.unshift(path.basename(current));
    current = parent;
  }
  let real;
  try {
    real = fs.realpathSync(current);
  } catch {
    throw new Error(
      `Could not resolve the real path of the task directory ancestor: ${current}`,
    );
  }
  return path.join(real, ...tail);
}

function pathExists(target) {
  try {
    fs.lstatSync(target);
    return true;
  } catch {
    return false;
  }
}

function isOutside(relative) {
  return (
    relative === ".." ||
    relative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relative)
  );
}
