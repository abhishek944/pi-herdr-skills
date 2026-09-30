#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { openSystemBrowser } from "./open-system-browser.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const saveServer = path.join(here, "save-server.mjs");

function parseArgs(argv) {
  const out = { dir: "", port: null, branch: "B1", open: false, resetSelection: false };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--port" && argv[i + 1]) out.port = Number(argv[++i]);
    else if (argv[i] === "--branch" && argv[i + 1]) out.branch = argv[++i];
    else if (argv[i] === "--reset-selection") out.resetSelection = true;
    else if (argv[i] === "--open") out.open = true;
  }
  if (out.port !== null && (!Number.isInteger(out.port) || out.port < 1 || out.port > 65535)) {
    throw new Error("--port must be an integer from 1 to 65535");
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
    req.setTimeout(2500, () => {
      req.destroy();
      resolve(0);
    });
  });
}

function sessionInfo(port) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/__grill_me_session`, (res) => {
      let body = "";
      res.on("data", (chunk) => {
        body += chunk;
      });
      res.on("end", () => {
        if (res.statusCode !== 200) return resolve({ occupied: true });
        try {
          const parsed = JSON.parse(body);
          resolve(parsed.root ? parsed : { occupied: true });
        } catch {
          resolve({ occupied: true });
        }
      });
    });
    req.on("error", () => resolve(null));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(null);
    });
  });
}

function readPort(portFile) {
  try {
    const port = Number(fs.readFileSync(portFile, "utf8").trim());
    return Number.isInteger(port) && port >= 1 && port <= 65535 ? port : null;
  } catch {
    return null;
  }
}

function startServer(root, requestedPort, portFile) {
  fs.rmSync(portFile, { force: true });
  const logFile = path.join(root, "save-server.log");
  const output = fs.openSync(logFile, "a");
  const child = spawn(
    process.execPath,
    [saveServer, "--dir", root, "--port", String(requestedPort)],
    { detached: true, stdio: ["ignore", output, output] },
  );
  fs.closeSync(output);
  child.unref();
  fs.writeFileSync(path.join(root, "save-server.pid"), String(child.pid));
  console.log(`Started save-server (pid ${child.pid}) → ${logFile}`);
}

const input = parseArgs(process.argv);
if (!input.dir) {
  console.error(
    "Usage: node preflight-comparison.mjs --dir <session-dir> [--port <free-port>] --branch B1 [--reset-selection] [--open]",
  );
  process.exit(1);
}

const root = path.resolve(input.dir);
const comparisonRel = `comparisons/comparison-${input.branch}.html`;
const comparisonPath = path.join(root, comparisonRel);
const selectionPath = path.join(root, `selection-${input.branch}.json`);
const portFile = path.join(root, "save-server.port");
if (!fs.existsSync(comparisonPath)) {
  throw new Error(`Missing comparison page: ${comparisonPath}. Run generate-comparison.mjs first.`);
}
if (input.resetSelection && fs.existsSync(selectionPath)) fs.unlinkSync(selectionPath);
fs.mkdirSync(root, { recursive: true });

let port = input.port ?? readPort(portFile);
let active = port ? await sessionInfo(port) : null;
if (active && active.root !== root) {
  if (input.port !== null) {
    throw new Error(`Port ${port} is already occupied by another process`);
  }
  port = null;
  active = null;
}

if (!port || !active) {
  const requestedPort = input.port ?? 0;
  startServer(root, requestedPort, portFile);
  port = null;
  active = null;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 125));
    port = readPort(portFile);
    if (!port) continue;
    active = await sessionInfo(port);
    if (active?.root === root) break;
  }
}

if (!port || active?.root !== root) {
  throw new Error(`Could not start a save server for ${root}; check save-server.log`);
}

const comparisonUrl = `http://127.0.0.1:${port}/${comparisonRel}`;
const status = await httpStatus(comparisonUrl);
if (status !== 200) {
  throw new Error(`Preflight failed: ${comparisonUrl} returned ${status || "no response"}`);
}
console.log(`Assigned session port: ${port}`);
console.log(`Preflight OK: ${comparisonUrl}`);
if (input.open) {
  try {
    openSystemBrowser(comparisonUrl);
    console.log("Opened in the visible system browser.");
  } catch (error) {
    console.error("Could not open the visible system browser:", error.message);
    process.exit(1);
  }
}
