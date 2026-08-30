#!/usr/bin/env node
/**
 * Capture a viewport screenshot (never full-page).
 *
 * Usage:
 *   node capture-viewport.mjs \
 *     --url "$APP_URL" \
 *     --out var/landing-page/ui-ux-grill-me/landing-improve/screenshots/B1-current.png \
 *     --session project-ui \
 *     [--scroll-top]
 *
 * Requires browser-use CLI. Does NOT pass --full.
 */

import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

function parseArgs(argv) {
  const out = { url: "", outPath: "", session: "default", scrollTop: true };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--url" && argv[i + 1]) out.url = argv[++i];
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
if (!args.url || !args.outPath) {
  console.error(
    "Usage: node capture-viewport.mjs --url <url> --out <png> --session <browser-session>",
  );
  process.exit(1);
}

const absOut = path.resolve(args.outPath);
fs.mkdirSync(path.dirname(absOut), { recursive: true });

const sessionFlag = `--session ${args.session}`;
run(`browser-use ${sessionFlag} open ${JSON.stringify(args.url)}`);
if (args.scrollTop) {
  run(`browser-use ${sessionFlag} eval "window.scrollTo(0, 0)"`);
}
// Viewport only — never --full
run(`browser-use ${sessionFlag} screenshot ${JSON.stringify(absOut)}`);
console.log(`Viewport screenshot: ${absOut}`);
