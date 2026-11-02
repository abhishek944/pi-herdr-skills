#!/usr/bin/env node
/**
 * Capture a viewport screenshot (never full-page).
 *
 * Usage:
 *   node capture-viewport.mjs \
 *     --url "$APP_URL" \
 *     --dir var/<sessionId>/<Wn>/<Tn> \
 *     --out screenshots/B1-current.png \
 *     --session project-ui \
 *     [--scroll-top]
 *
 * --dir is the owner's canonical task directory (a root task directory, or the
 * nested delegated triple beneath the exact parent task directory). --out is
 * resolved against it and must stay inside it.
 *
 * Requires browser-use CLI. Does NOT pass --full.
 */

import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { resolveTaskDir, resolveWriteTarget } from "./task-dir.mjs";

function parseArgs(argv) {
  const out = { url: "", dir: "", outPath: "", session: "default", scrollTop: true };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--url" && argv[i + 1]) out.url = argv[++i];
    else if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--out" && argv[i + 1]) out.outPath = argv[++i];
    else if (argv[i] === "--session" && argv[i + 1]) out.session = argv[++i];
    else if (argv[i] === "--no-scroll-top") out.scrollTop = false;
  }
  return out;
}

function run(cmd) {
  execSync(cmd, { stdio: "inherit", encoding: "utf8" });
}

const args = parseArgs(process.argv);
if (!args.url || !args.dir || !args.outPath) {
  console.error(
    "Usage: node capture-viewport.mjs --url <url> --dir <canonical-task-dir> --out <png> --session <browser-session>",
  );
  process.exit(1);
}

const taskDir = resolveTaskDir(args.dir, { requireExisting: false });
const absOut = resolveWriteTarget(taskDir, args.outPath);
fs.mkdirSync(path.dirname(absOut), { recursive: true });

const sessionFlag = `--session ${args.session}`;
run(`browser-use ${sessionFlag} open ${JSON.stringify(args.url)}`);
if (args.scrollTop) {
  run(`browser-use ${sessionFlag} eval "window.scrollTo(0, 0)"`);
}
// Viewport only — never --full
run(`browser-use ${sessionFlag} screenshot ${JSON.stringify(absOut)}`);
console.log(`Viewport screenshot: ${absOut}`);
