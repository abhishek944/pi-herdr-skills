#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import path from "node:path";

function parse(argv) {
  const input = { root: "", port: 0, idleTimeoutMs: 2 * 60 * 60 * 1000 };
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--root" && argv[index + 1]) input.root = argv[++index];
    else if (argv[index] === "--port" && argv[index + 1]) input.port = Number(argv[++index]);
    else if (argv[index] === "--idle-timeout-ms" && argv[index + 1]) {
      input.idleTimeoutMs = Number(argv[++index]);
    }
  }
  return input;
}

const input = parse(process.argv);
if (!input.root || !Number.isInteger(input.port) || input.port < 1) {
  console.error("Usage: report-server.mjs --root <report-dir> --port <port> [--idle-timeout-ms <ms>]");
  process.exit(1);
}
if (!Number.isFinite(input.idleTimeoutMs) || input.idleTimeoutMs < 500) {
  throw new Error("Idle timeout must be at least 500 milliseconds");
}
const root = fs.realpathSync(input.root);
if (!fs.statSync(root).isDirectory()) throw new Error("Report root must be a directory");
const pidFile = path.join(root, `.herdr-orchestrator-report-server-${input.port}.pid`);
let idleTimer;

function insideRoot(file) {
  const relative = path.relative(root, file);
  return relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

function headers(contentType) {
  return {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:",
    "Content-Type": contentType,
    "X-Content-Type-Options": "nosniff",
  };
}

function scheduleShutdown() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => shutdown("idle timeout"), input.idleTimeoutMs);
}

const server = http.createServer((request, response) => {
  scheduleShutdown();
  if (request.method === "GET" && request.url === "/__herdr_orchestrator_report") {
    response.writeHead(200, headers("application/json; charset=utf-8"));
    response.end(JSON.stringify({ root }));
    return;
  }
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405).end();
    return;
  }
  let relative;
  try {
    relative = decodeURIComponent((request.url || "/").split("?", 1)[0]).replace(/^\/+/, "");
  } catch {
    response.writeHead(400).end("Bad request");
    return;
  }
  const candidate = path.resolve(root, relative);
  if (!relative || !insideRoot(candidate) || !fs.existsSync(candidate)) {
    response.writeHead(404).end("Not found");
    return;
  }
  const file = fs.realpathSync(candidate);
  if (!insideRoot(file) || !fs.statSync(file).isFile() || path.extname(file) !== ".html") {
    response.writeHead(404).end("Not found");
    return;
  }
  response.writeHead(200, headers("text/html; charset=utf-8"));
  if (request.method === "HEAD") response.end();
  else fs.createReadStream(file).pipe(response);
});

function shutdown(reason) {
  clearTimeout(idleTimer);
  server.close(() => {
    try {
      if (fs.readFileSync(pidFile, "utf8").trim() === String(process.pid)) fs.unlinkSync(pidFile);
    } catch {}
    console.log(`Herdr orchestrator report server stopped: ${reason}`);
    process.exit(0);
  });
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
server.listen(input.port, "127.0.0.1", () => {
  fs.writeFileSync(pidFile, String(process.pid), { mode: 0o600 });
  scheduleShutdown();
  console.log(`Herdr orchestrator report server: http://127.0.0.1:${input.port}/`);
});
