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
  const out = { dir: "", port: 9877, branch: "B1", open: false, reset: false };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--port" && argv[i + 1]) out.port = Number(argv[++i]);
    else if (argv[i] === "--branch" && argv[i + 1]) out.branch = argv[++i];
    else if (argv[i] === "--open") out.open = true;
    else if (argv[i] === "--reset-response") out.reset = true;
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
function sessionRoot(port) {
  return new Promise((resolve) => {
    const req = http.get(
      `http://127.0.0.1:${port}/__grill_me_session`,
      (res) => {
        let body = "";
        res.on("data", (chunk) => {
          body += chunk;
        });
        res.on("end", () => {
          if (res.statusCode !== 200) return resolve("occupied");
          try {
            resolve(JSON.parse(body).root || "occupied");
          } catch {
            resolve("occupied");
          }
        });
      },
    );
    req.on("error", () => resolve(null));
    req.setTimeout(2500, () => {
      req.destroy();
      resolve(null);
    });
  });
}
const input = parse(process.argv);
if (!input.dir) {
  console.error(
    "Usage: node preflight-question.mjs --dir <session-dir> --port <port> --branch B1 [--reset-response] [--open]",
  );
  process.exit(1);
}
const root = resolveSessionDir(input.dir);
const page = path.join(root, "questions", `question-${input.branch}.html`);
const response = path.join(root, `response-${input.branch}.json`);
const url = `http://127.0.0.1:${input.port}/questions/question-${input.branch}.html`;
if (!fs.existsSync(page)) throw new Error(`Missing question page: ${page}`);
if (input.reset && fs.existsSync(response)) fs.unlinkSync(response);
let activeRoot = await sessionRoot(input.port);
if (activeRoot && activeRoot !== root) {
  throw new Error(
    `Port ${input.port} is already serving a different grill-me session`,
  );
}
let code = activeRoot === root ? await status(url) : 0;
if (code !== 200) {
  fs.mkdirSync(root, { recursive: true });
  const log = fs.openSync(path.join(root, "save-server.log"), "a");
  const child = spawn(
    process.execPath,
    [
      path.join(here, "save-server.mjs"),
      "--dir",
      root,
      "--port",
      String(input.port),
    ],
    { detached: true, stdio: ["ignore", log, log] },
  );
  child.unref();
  fs.writeFileSync(path.join(root, "save-server.pid"), String(child.pid));
  for (let attempt = 0; attempt < 20 && code !== 200; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 250));
    activeRoot = await sessionRoot(input.port);
    code = activeRoot === root ? await status(url) : 0;
  }
}
if (code !== 200)
  throw new Error(`Preflight failed: ${url} returned ${code || "no response"}`);
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
