#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import path from "node:path";

function parseArgs(argv) {
  const out = { dir: "", port: 0, idleTimeoutMs: 2 * 60 * 60 * 1000 };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--port" && argv[i + 1]) out.port = Number(argv[++i]);
    else if (argv[i] === "--idle-timeout-ms" && argv[i + 1]) out.idleTimeoutMs = Number(argv[++i]);
  }
  if (!Number.isInteger(out.port) || out.port < 0 || out.port > 65535) {
    throw new Error("--port must be an integer from 0 to 65535");
  }
  return out;
}

const input = parseArgs(process.argv);
if (!input.dir) {
  console.error("Usage: node save-server.mjs --dir <session-dir> [--port <free-port>|0]");
  process.exit(1);
}
const root = path.resolve(input.dir);
fs.mkdirSync(root, { recursive: true });
const pidFile = path.join(root, "save-server.pid");
const portFile = path.join(root, "save-server.port");
let idleTimer;
let assignedPort = 0;

const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
};

function safePath(urlPath) {
  const relative = decodeURIComponent(urlPath.split("?")[0]).replace(/^\/+/, "") || "index.html";
  const resolved = path.resolve(root, relative);
  const rootRelative = path.relative(root, resolved);
  if (rootRelative === ".." || rootRelative.startsWith(`..${path.sep}`) || path.isAbsolute(rootRelative)) {
    return null;
  }
  return resolved;
}

const server = http.createServer((req, res) => {
  scheduleIdleShutdown();
  if (req.method === "GET" && req.url === "/__grill_me_session") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ root, port: assignedPort }));
    return;
  }
  if (req.method === "POST" && req.url === "/save") {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      try {
        const data = JSON.parse(body);
        const questionId = /^B\d+$/.test(data.questionId) ? data.questionId : "B1";
        const output = path.join(root, `selection-${questionId}.json`);
        fs.writeFileSync(output, JSON.stringify(data, null, 2));
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, path: output }));
        console.log(`[save] ${output} → selected: ${data.selected}`);
      } catch (error) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: false, error: String(error) }));
      }
    });
    return;
  }
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405).end();
    return;
  }
  const file = safePath(req.url || "/");
  if (!file || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end("Not found");
    return;
  }
  res.writeHead(200, { "Content-Type": mime[path.extname(file)] || "application/octet-stream" });
  if (req.method === "HEAD") res.end();
  else fs.createReadStream(file).pipe(res);
});

function scheduleIdleShutdown() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => shutdown("idle timeout"), input.idleTimeoutMs);
}

function removeOwnedFile(file, expected) {
  try {
    if (fs.readFileSync(file, "utf8").trim() === String(expected)) fs.unlinkSync(file);
  } catch {}
}

function shutdown(reason) {
  clearTimeout(idleTimer);
  server.close(() => {
    removeOwnedFile(pidFile, process.pid);
    removeOwnedFile(portFile, assignedPort);
    console.log(`ui-ux-grill-me save server stopped: ${reason}`);
    process.exit(0);
  });
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
server.on("error", (error) => {
  console.error(`ui-ux-grill-me save server failed: ${error.message}`);
  process.exit(1);
});
server.listen(input.port, "127.0.0.1", () => {
  const address = server.address();
  assignedPort = typeof address === "object" && address ? address.port : 0;
  const temporary = `${portFile}.${process.pid}`;
  fs.writeFileSync(temporary, String(assignedPort));
  fs.renameSync(temporary, portFile);
  scheduleIdleShutdown();
  console.log(`ui-ux-grill-me save server: http://127.0.0.1:${assignedPort}/`);
});
