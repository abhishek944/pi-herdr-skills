#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { resolveSessionDir } from "./session-path.mjs";

function args(argv) {
  const out = { dir: "", port: 9877, idleTimeoutMs: 2 * 60 * 60 * 1000 };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--port" && argv[i + 1]) out.port = Number(argv[++i]);
    else if (argv[i] === "--idle-timeout-ms" && argv[i + 1])
      out.idleTimeoutMs = Number(argv[++i]);
  }
  return out;
}

const input = args(process.argv);
if (!input.dir) {
  console.error(
    "Usage: node save-server.mjs --dir <session-dir> [--port 9877]",
  );
  process.exit(1);
}
const root = resolveSessionDir(input.dir);
fs.mkdirSync(root, { recursive: true });
const mime = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
};
const pidFile = path.join(root, "save-server.pid");
let idleTimer;

const server = http.createServer((req, res) => {
  scheduleIdleShutdown();
  if (req.method === "GET" && req.url === "/__grill_me_session") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ root }));
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
        const branch = /^B\d+$/.test(data.questionId) ? data.questionId : "B1";
        const output = path.join(root, `response-${branch}.json`);
        fs.writeFileSync(output, JSON.stringify(data, null, 2));
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
        console.log(`[save] ${output}`);
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
  const relative = decodeURIComponent((req.url || "/").split("?")[0]).replace(
    /^\/+/,
    "",
  );
  const file = path.resolve(root, relative || "index.html");
  const rootRelative = path.relative(root, file);
  const outsideRoot =
    rootRelative === ".." ||
    rootRelative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(rootRelative);
  if (outsideRoot || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end("Not found");
    return;
  }
  res.writeHead(200, {
    "Content-Type": mime[path.extname(file)] || "application/octet-stream",
  });
  if (req.method === "HEAD") res.end();
  else fs.createReadStream(file).pipe(res);
});

function scheduleIdleShutdown() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => shutdown("idle timeout"), input.idleTimeoutMs);
}

function shutdown(reason) {
  clearTimeout(idleTimer);
  server.close(() => {
    try {
      if (fs.readFileSync(pidFile, "utf8").trim() === String(process.pid))
        fs.unlinkSync(pidFile);
    } catch {}
    console.log(`grill-me save server stopped: ${reason}`);
    process.exit(0);
  });
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
server.listen(input.port, "127.0.0.1", () => {
  scheduleIdleShutdown();
  console.log(`grill-me save server: http://127.0.0.1:${input.port}/`);
});
