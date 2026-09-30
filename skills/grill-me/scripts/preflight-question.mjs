#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { openSystemBrowser } from "./open-system-browser.mjs";
import { resolveSessionDir } from "./session-path.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));

function parse(argv) {
  const out = { dir: "", port: null, branch: "B1", open: false, reset: false };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--port" && argv[i + 1]) out.port = Number(argv[++i]);
    else if (argv[i] === "--branch" && argv[i + 1]) out.branch = argv[++i];
    else if (argv[i] === "--open") out.open = true;
    else if (argv[i] === "--reset-response") out.reset = true;
  }
  if (out.port !== null && (!Number.isInteger(out.port) || out.port < 1 || out.port > 65535)) {
    throw new Error("--port must be an integer from 1 to 65535");
  }
  return out;
}

function status(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      res.resume();
      resolve(res.statusCode || 0);
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
  const log = fs.openSync(path.join(root, "save-server.log"), "a");
  const child = spawn(
    process.execPath,
    [path.join(here, "save-server.mjs"), "--dir", root, "--port", String(requestedPort)],
    { detached: true, stdio: ["ignore", log, log] },
  );
  fs.closeSync(log);
  child.unref();
  fs.writeFileSync(path.join(root, "save-server.pid"), String(child.pid));
  return child.pid;
}

const input = parse(process.argv);
if (!input.dir) {
  console.error(
    "Usage: node preflight-question.mjs --dir <session-dir> [--port <free-port>] --branch B1 [--reset-response] [--open]",
  );
  process.exit(1);
}

const root = resolveSessionDir(input.dir);
const page = path.join(root, "questions", `question-${input.branch}.html`);
const response = path.join(root, `response-${input.branch}.json`);
const portFile = path.join(root, "save-server.port");
if (!fs.existsSync(page)) throw new Error(`Missing question page: ${page}`);
if (input.reset && fs.existsSync(response)) fs.unlinkSync(response);
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

const url = `http://127.0.0.1:${port}/questions/question-${input.branch}.html`;
const code = await status(url);
if (code !== 200) {
  throw new Error(`Preflight failed: ${url} returned ${code || "no response"}`);
}
console.log(`Assigned session port: ${port}`);
console.log(`Preflight OK: ${url}`);
if (input.open) {
  try {
    openSystemBrowser(url);
    console.log("Opened in the visible system browser.");
  } catch (error) {
    console.error("Could not open the visible system browser:", error.message);
    process.exit(1);
  }
}
