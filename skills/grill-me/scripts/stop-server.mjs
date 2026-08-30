#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { resolveSessionDir } from "./session-path.mjs";

const dirIndex = process.argv.indexOf("--dir");
const portIndex = process.argv.indexOf("--port");
if (
  dirIndex < 0 ||
  !process.argv[dirIndex + 1] ||
  portIndex < 0 ||
  !process.argv[portIndex + 1]
) {
  console.error(
    "Usage: node stop-server.mjs --dir <session-dir> --port <port>",
  );
  process.exit(1);
}
const root = resolveSessionDir(process.argv[dirIndex + 1]);
const port = Number(process.argv[portIndex + 1]);
const pidFile = path.join(root, "save-server.pid");

const servedRoot = await sessionRoot(port);
if (servedRoot && servedRoot !== root) {
  throw new Error(
    `Refusing to stop port ${port}; it serves a different grill-me session`,
  );
}
if (!servedRoot) {
  fs.rmSync(pidFile, { force: true });
  console.log("grill-me save server already stopped");
  process.exit(0);
}
const pid = Number(fs.readFileSync(pidFile, "utf8").trim());
if (!Number.isInteger(pid) || pid <= 0)
  throw new Error(`Invalid save server pid: ${pidFile}`);
process.kill(pid, "SIGTERM");
for (let attempt = 0; attempt < 20; attempt += 1) {
  await new Promise((resolve) => setTimeout(resolve, 100));
  if (!(await sessionRoot(port))) break;
}
if (await sessionRoot(port)) throw new Error(`Save server ${pid} did not stop`);
fs.rmSync(pidFile, { force: true });
console.log(`Stopped grill-me save server ${pid}`);

function sessionRoot(targetPort) {
  return new Promise((resolve) => {
    const request = http.get(
      `http://127.0.0.1:${targetPort}/__grill_me_session`,
      (response) => {
        let body = "";
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          if (response.statusCode !== 200) return resolve("occupied");
          try {
            resolve(JSON.parse(body).root || "occupied");
          } catch {
            resolve("occupied");
          }
        });
      },
    );
    request.on("error", () => resolve(null));
    request.setTimeout(500, () => {
      request.destroy();
      resolve(null);
    });
  });
}
