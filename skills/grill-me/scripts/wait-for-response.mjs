#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { resolveSessionDir } from "./session-path.mjs";

function parse(argv) {
  const out = { dir: "", branch: "B1", timeout: 1800, interval: 500 };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--branch" && argv[i + 1]) out.branch = argv[++i];
    else if (argv[i] === "--timeout" && argv[i + 1])
      out.timeout = Number(argv[++i]);
    else if (argv[i] === "--interval" && argv[i + 1])
      out.interval = Number(argv[++i]);
  }
  return out;
}
const input = parse(process.argv);
if (!input.dir || input.timeout <= 0) {
  console.error(
    "Usage: node wait-for-response.mjs --dir <session-dir> --branch B1 [--timeout 1800]",
  );
  process.exit(1);
}
const output = path.join(
  resolveSessionDir(input.dir),
  `response-${input.branch}.json`,
);
const deadline = Date.now() + input.timeout * 1000;
let heartbeat = Date.now() + 45000;
console.log(`Waiting for response: ${output}`);
while (Date.now() < deadline) {
  if (fs.existsSync(output)) {
    try {
      const value = JSON.parse(fs.readFileSync(output, "utf8"));
      if (value.selected || value.response?.trim()) {
        console.log(JSON.stringify(value));
        process.exit(0);
      }
    } catch {}
  }
  if (Date.now() >= heartbeat) {
    console.log("Still waiting for browser response…");
    heartbeat = Date.now() + 45000;
  }
  await new Promise((resolve) => setTimeout(resolve, input.interval));
}
console.error(`Timed out waiting for ${output}`);
process.exit(2);
