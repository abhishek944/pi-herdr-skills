#!/usr/bin/env node
/**
 * Ensure save-server is running and comparison page is reachable before opening browser.
 *
 * Usage:
 *   node preflight-comparison.mjs \
 *     --dir var/landing-page/ui-ux-grill-me/landing-improve \
 *     --port 9876 \
 *     --branch B1 \
 *     [--reset-selection] \
 *     [--open]
 *
 * Exits 0 only when GET /comparisons/comparison-<branch>.html returns 200.
 * Starts a detached save-server if the port is down.
 */

import fs from "node:fs";
import path from "node:path";
import http from "node:http";
import { execSync, spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { openSystemBrowser } from "./open-system-browser.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SAVE_SERVER = path.join(__dirname, "save-server.mjs");

function parseArgs(argv) {
  const out = {
    dir: "",
    port: 9876,
    branch: "B1",
    open: false,
    resetSelection: false,
  };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--port" && argv[i + 1]) out.port = Number(argv[++i]);
    else if (argv[i] === "--branch" && argv[i + 1]) out.branch = argv[++i];
    else if (argv[i] === "--reset-selection") out.resetSelection = true;
    else if (argv[i] === "--open") out.open = true;
  }
  return out;
}

function httpStatus(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      res.resume();
      resolve(res.statusCode ?? 0);
    });
    req.on("error", () => resolve(0));
    req.setTimeout(3000, () => {
      req.destroy();
      resolve(0);
    });
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function portInUse(port) {
  try {
    const out = execSync(`lsof -ti:${port} 2>/dev/null || true`, {
      encoding: "utf8",
    }).trim();
    return Boolean(out);
  } catch {
    return false;
  }
}

function startDetachedServer(dir, port, pidFile) {
  const logFile = path.join(dir, "save-server.log");
  const out = fs.openSync(logFile, "a");
  const child = spawn(
    process.execPath,
    [SAVE_SERVER, "--dir", dir, "--port", String(port)],
    {
      detached: true,
      stdio: ["ignore", out, out],
    },
  );
  child.unref();
  fs.writeFileSync(pidFile, String(child.pid));
  console.log(`Started save-server (pid ${child.pid}) → ${logFile}`);
}

const args = parseArgs(process.argv);
if (!args.dir) {
  console.error(
    "Usage: node preflight-comparison.mjs --dir <session-dir> --port <port> --branch B1 [--reset-selection] [--open]",
  );
  process.exit(1);
}

const absDir = path.resolve(args.dir);
const comparisonRel = `comparisons/comparison-${args.branch}.html`;
const comparisonPath = path.join(absDir, comparisonRel);
const comparisonUrl = `http://127.0.0.1:${args.port}/${comparisonRel}`;
const pidFile = path.join(absDir, "save-server.pid");
const selectionPath = path.join(absDir, `selection-${args.branch}.json`);

if (!fs.existsSync(comparisonPath)) {
  console.error(`Missing comparison page: ${comparisonPath}`);
  console.error("Run generate-comparison.mjs first.");
  process.exit(1);
}

if (args.resetSelection && fs.existsSync(selectionPath)) {
  fs.unlinkSync(selectionPath);
  console.log(`Removed stale feedback: ${selectionPath}`);
}

let status = await httpStatus(comparisonUrl);

if (status !== 200) {
  console.log(
    `Save server not reachable at :${args.port} (status ${status || "down"})`,
  );
  if (portInUse(args.port)) {
    console.error(
      `Port ${args.port} is in use but not serving the comparison page.`,
    );
    console.error(
      `Free the port or pick another --port, then re-run preflight.`,
    );
    process.exit(1);
  }
  fs.mkdirSync(absDir, { recursive: true });
  startDetachedServer(absDir, args.port, pidFile);

  for (let i = 0; i < 20; i++) {
    await sleep(250);
    status = await httpStatus(comparisonUrl);
    if (status === 200) break;
  }
}

if (status !== 200) {
  console.error(
    `Preflight failed: ${comparisonUrl} returned ${status || "no response"}`,
  );
  console.error(`Check ${path.join(absDir, "save-server.log")}`);
  process.exit(1);
}

console.log(`Preflight OK: ${comparisonUrl}`);

if (args.open) {
  try {
    openSystemBrowser(comparisonUrl);
    console.log("Opened in the visible system browser.");
  } catch (err) {
    console.error("Could not open the visible system browser:", err.message);
    process.exit(1);
  }
}
