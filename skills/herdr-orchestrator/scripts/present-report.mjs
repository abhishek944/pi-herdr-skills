#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import net from "node:net";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { openSystemBrowser } from "./open-system-browser.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
function parse(argv) {
  const input = { file: "", noOpen: false, idleTimeoutMs: 2 * 60 * 60 * 1000 };
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--file" && argv[index + 1]) input.file = argv[++index];
    else if (argv[index] === "--no-open") input.noOpen = true;
    else if (argv[index] === "--idle-timeout-ms" && argv[index + 1]) {
      input.idleTimeoutMs = Number(argv[++index]);
    }
  }
  return input;
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close((error) => (error ? reject(error) : resolve(port)));
    });
  });
}

function get(url) {
  return new Promise((resolve) => {
    const request = http.get(url, (response) => {
      let body = "";
      response.on("data", (chunk) => { body += chunk; });
      response.on("end", () => resolve({ status: response.statusCode || 0, body }));
    });
    request.on("error", () => resolve({ status: 0, body: "" }));
    request.setTimeout(1000, () => request.destroy());
  });
}

const input = parse(process.argv);
if (!input.file) {
  console.error("Usage: present-report.mjs --file <report.html> [--no-open] [--idle-timeout-ms <ms>]");
  process.exit(1);
}
if (!Number.isFinite(input.idleTimeoutMs) || input.idleTimeoutMs < 500) {
  throw new Error("Idle timeout must be at least 500 milliseconds");
}
const file = fs.realpathSync(input.file);
if (!fs.statSync(file).isFile() || path.extname(file) !== ".html") {
  throw new Error("Report must be a regular HTML file");
}
const root = path.dirname(file);
const port = await freePort();
const logPath = path.join(root, `.herdr-orchestrator-report-server-${port}.log`);
const log = fs.openSync(logPath, "a", 0o600);
const child = spawn(
  process.execPath,
  [
    path.join(here, "report-server.mjs"),
    "--root", root,
    "--port", String(port),
    "--idle-timeout-ms", String(input.idleTimeoutMs),
  ],
  { detached: true, stdio: ["ignore", log, log] },
);
child.unref();
const markerUrl = `http://127.0.0.1:${port}/__herdr_orchestrator_report`;
let ready = false;
for (let attempt = 0; attempt < 20; attempt += 1) {
  await new Promise((resolve) => setTimeout(resolve, 100));
  const marker = await get(markerUrl);
  if (marker.status !== 200) continue;
  try {
    ready = JSON.parse(marker.body).root === root;
  } catch {
    ready = false;
  }
  if (ready) break;
}
const reportUrl = `http://127.0.0.1:${port}/${encodeURIComponent(path.basename(file))}`;
const report = ready ? await get(reportUrl) : { status: 0 };
if (!ready || report.status !== 200) {
  try { process.kill(child.pid, "SIGTERM"); } catch {}
  throw new Error(`Report preflight failed: ${reportUrl} returned ${report.status || "no response"}`);
}
if (!input.noOpen) openSystemBrowser(reportUrl);
console.log(JSON.stringify({ opened: !input.noOpen, url: reportUrl, serverPid: child.pid }));
