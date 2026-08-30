#!/usr/bin/env node
/**
 * Static file server for ui-ux-grill-me comparison pages.
 * Serves --dir and accepts POST /save with JSON body → writes selection file.
 *
 * Usage:
 *   node save-server.mjs --dir var/landing-page/ui-ux-grill-me/landing-improve --port 9876
 */

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const out = { dir: "", port: 9876 };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--dir" && argv[i + 1]) out.dir = argv[++i];
    else if (argv[i] === "--port" && argv[i + 1]) out.port = Number(argv[++i]);
  }
  return out;
}

const { dir: rootDir, port } = parseArgs(process.argv);
if (!rootDir) {
  console.error(
    "Usage: node save-server.mjs --dir <session-dir> [--port 9876]",
  );
  process.exit(1);
}

const absRoot = path.resolve(rootDir);
fs.mkdirSync(absRoot, { recursive: true });

const MIME = {
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
  const decoded = decodeURIComponent(urlPath.split("?")[0]);
  const rel = decoded === "/" ? "/index.html" : decoded;
  const resolved = path.normalize(path.join(absRoot, rel));
  if (!resolved.startsWith(absRoot)) return null;
  return resolved;
}

const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url === "/save") {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      try {
        const data = JSON.parse(body);
        const questionId = data.questionId || "B1";
        const outPath = path.join(absRoot, `selection-${questionId}.json`);
        fs.writeFileSync(outPath, JSON.stringify(data, null, 2));
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, path: outPath }));
        console.log(`[save] ${outPath} → selected: ${data.selected}`);
      } catch (err) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: false, error: String(err) }));
      }
    });
    return;
  }

  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405);
    res.end();
    return;
  }

  const filePath = safePath(req.url || "/");
  if (
    !filePath ||
    !fs.existsSync(filePath) ||
    fs.statSync(filePath).isDirectory()
  ) {
    res.writeHead(404);
    res.end("Not found");
    return;
  }

  const ext = path.extname(filePath);
  res.writeHead(200, {
    "Content-Type": MIME[ext] || "application/octet-stream",
  });
  if (req.method === "HEAD") {
    res.end();
    return;
  }
  fs.createReadStream(filePath).pipe(res);
});

server.listen(port, "127.0.0.1", () => {
  console.log(`ui-ux-grill-me save-server`);
  console.log(`  root: ${absRoot}`);
  console.log(`  url:  http://127.0.0.1:${port}/`);
});
