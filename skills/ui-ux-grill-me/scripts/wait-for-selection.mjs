#!/usr/bin/env node
/** Keep the agent turn alive until the comparison page saves feedback. */

import fs from "node:fs";
import path from "node:path";

function parseArgs(argv) {
  const out = { dir: "", branch: "B1", timeout: 1800, interval: 500 };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--branch" && argv[i + 1]) out.branch = argv[++i];
    else if (argv[i] === "--timeout" && argv[i + 1])
      out.timeout = Number(argv[++i]);
    else if (argv[i] === "--interval" && argv[i + 1])
      out.interval = Number(argv[++i]);
  }
  return out;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const args = parseArgs(process.argv);
if (!args.dir || !Number.isFinite(args.timeout) || args.timeout <= 0) {
  console.error(
    "Usage: node wait-for-selection.mjs --dir <session-dir> --branch B1 [--timeout 1800]",
  );
  process.exit(1);
}

const selectionPath = path.join(
  path.resolve(args.dir),
  `selection-${args.branch}.json`,
);
const deadline = Date.now() + args.timeout * 1000;
let nextHeartbeat = Date.now() + 45000;

console.log(`Waiting for feedback: ${selectionPath}`);
while (Date.now() < deadline) {
  if (fs.existsSync(selectionPath)) {
    try {
      const selection = JSON.parse(fs.readFileSync(selectionPath, "utf8"));
      if (selection.selected || selection.why?.trim()) {
        console.log(JSON.stringify(selection));
        process.exit(0);
      }
    } catch {
      // The save may still be completing; retry on the next interval.
    }
  }
  if (Date.now() >= nextHeartbeat) {
    console.log("Still waiting for browser feedback…");
    nextHeartbeat = Date.now() + 45000;
  }
  await sleep(args.interval);
}

console.error(`Timed out waiting for ${selectionPath}`);
process.exit(2);
