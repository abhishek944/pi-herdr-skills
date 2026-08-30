#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { resolveSessionSlug } from "./session-path.mjs";

function parseArgs(argv) {
  const out = {
    feature: "",
    session: "",
    branch: "B1",
    question: "",
    options: "",
  };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--feature" && argv[i + 1]) out.feature = argv[++i];
    else if (argv[i] === "--session" && argv[i + 1]) out.session = argv[++i];
    else if (argv[i] === "--branch" && argv[i + 1]) out.branch = argv[++i];
    else if (argv[i] === "--question" && argv[i + 1]) out.question = argv[++i];
    else if (argv[i] === "--options" && argv[i + 1]) out.options = argv[++i];
  }
  return out;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function imageDataUri(sessionDir, relativePath) {
  const full = path.resolve(sessionDir, relativePath);
  if (!fs.existsSync(full)) return null;
  const root = fs.realpathSync(sessionDir);
  const resolved = fs.realpathSync(full);
  const relative = path.relative(root, resolved);
  if (
    relative === ".." ||
    relative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relative)
  ) {
    return null;
  }
  const ext = path.extname(resolved).toLowerCase();
  const mime =
    ext === ".svg"
      ? "image/svg+xml"
      : ext === ".jpg" || ext === ".jpeg"
        ? "image/jpeg"
        : "image/png";
  return `data:${mime};base64,${fs.readFileSync(resolved).toString("base64")}`;
}

const args = parseArgs(process.argv);
if (!args.feature || !args.session || !args.question || !args.options) {
  console.error(
    'Usage: node generate-question.mjs --feature <feature-name> --session <slug> --branch B1 --question "..." --options <json>',
  );
  process.exit(1);
}

const sessionDir = resolveSessionSlug(args.feature, args.session);
const outputDir = path.join(sessionDir, "questions");
const config = JSON.parse(fs.readFileSync(path.resolve(args.options), "utf8"));
if (
  !Array.isArray(config.options) ||
  config.options.length < 2 ||
  config.options.length > 6
) {
  throw new Error("Question config must contain 2–6 options.");
}
const ids = new Set();
for (const option of config.options) {
  if (!option.id || !option.label || ids.has(option.id))
    throw new Error("Every option needs a unique id and label.");
  ids.add(option.id);
}
const recommended = config.recommended ?? config.options[0].id;
if (!ids.has(recommended))
  throw new Error("recommended must match an option id.");

let visual = "";
let mermaidModule = "";
if (config.visual?.type === "mermaid" && config.visual.content) {
  visual = `<section class="concept" aria-label="Concept diagram"><pre class="mermaid">${escapeHtml(config.visual.content)}</pre></section>`;
  mermaidModule = `<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"; mermaid.initialize({ startOnLoad: true, theme: "dark", securityLevel: "strict" });</script>`;
} else if (config.visual?.type === "html" && config.visual.content) {
  visual = `<section class="concept" aria-label="Concept explanation">${config.visual.content}</section>`;
} else if (config.visual?.type === "image" && config.visual.path) {
  const uri = imageDataUri(sessionDir, config.visual.path);
  if (!uri) throw new Error(`Visual image not found: ${config.visual.path}`);
  visual = `<section class="concept"><img src="${uri}" alt="${escapeHtml(config.visual.alt || "Concept explanation")}" /></section>`;
}

const labels = Object.fromEntries(
  config.options.map((option) => [option.id, option.label]),
);
const cards = config.options
  .map(
    (option) => `
  <label class="option">
    <input type="radio" name="choice" value="${escapeHtml(option.id)}" />
    <span class="option-id">${escapeHtml(option.id)}</span>
    <span class="option-copy"><strong>${escapeHtml(option.label)}${option.id === recommended ? " · Recommended" : ""}</strong><small>${escapeHtml(option.description || "")}</small></span>
  </label>`,
  )
  .join("");

const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Grill me · ${escapeHtml(args.branch)}</title>
<style>
:root{color-scheme:dark;--bg:#0f1419;--panel:#18202a;--line:rgba(255,255,255,.11);--text:#edf2f7;--muted:#a7b0bc;--accent:#86efac}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 50% -10%,rgba(134,239,172,.10),transparent 34%),var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}.wrap{width:min(920px,calc(100% - 32px));margin:0 auto;padding:40px 0 64px}.eyebrow{color:#7dd3fc;font:12px ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase}h1{font-size:clamp(25px,4vw,38px);line-height:1.15;margin:10px 0 12px}.context{color:var(--muted);max-width:760px;margin:0 0 24px}.concept{margin:20px 0 26px;padding:20px;border:1px solid var(--line);border-radius:16px;background:rgba(24,32,42,.72);overflow:auto}.concept img{display:block;max-width:100%;margin:auto}.choices{display:grid;gap:10px}.option{display:flex;gap:14px;align-items:flex-start;padding:16px;border:1px solid var(--line);border-radius:14px;background:var(--panel);cursor:pointer}.option:has(input:checked){border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}.option input{margin-top:5px}.option-id{color:var(--accent);font:13px ui-monospace,monospace}.option-copy{display:grid;gap:4px}.option-copy small{color:var(--muted)}.response{display:grid;gap:7px;margin-top:20px;color:var(--muted)}textarea{width:100%;min-height:100px;padding:13px;border:1px solid var(--line);border-radius:12px;background:var(--panel);color:var(--text);font:inherit;resize:vertical}.actions{display:flex;align-items:center;gap:14px;margin-top:16px}button{padding:11px 18px;border:0;border-radius:10px;background:var(--accent);color:#07110b;font:600 15px system-ui;cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}.status{color:var(--muted)}.status.ok{color:var(--accent)}.status.err{color:#fca5a5}@media(max-width:560px){.wrap{padding-top:24px}.option{padding:13px}.concept{padding:12px}}
</style></head><body><main class="wrap"><div class="eyebrow">grill-me · ${escapeHtml(args.session)} · ${escapeHtml(args.branch)}</div><h1>${escapeHtml(args.question)}</h1><p class="context">${escapeHtml(config.context || "Choose the direction that best matches your intent, or respond in your own words.")}</p>${visual}<form id="form"><div class="choices">${cards}</div><label class="response" for="response">Response or refinement<textarea id="response" placeholder="Explain your choice, combine options, or reject them all…"></textarea></label><div class="actions"><button id="submit" type="submit" disabled>Submit response</button><span id="status" class="status" role="status"></span></div></form></main>
<script>
const form=document.getElementById("form"),submit=document.getElementById("submit"),response=document.getElementById("response"),status=document.getElementById("status"),labels=${JSON.stringify(labels)};
function update(){submit.disabled=!document.querySelector('input[name="choice"]:checked')&&!response.value.trim()}form.addEventListener("input",update);form.addEventListener("submit",async(event)=>{event.preventDefault();const choice=document.querySelector('input[name="choice"]:checked'),text=response.value.trim();if(!choice&&!text)return;submit.disabled=true;status.textContent="Saving…";const payload={questionId:${JSON.stringify(args.branch)},sessionSlug:${JSON.stringify(args.session)},selected:choice?.value||null,label:choice?(labels[choice.value]||choice.value):null,submissionType:choice?"selection":"comments-only",response:text,timestamp:new Date().toISOString()};try{const result=await fetch("/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}),data=await result.json();if(!result.ok||!data.ok)throw new Error(data.error||"Save failed");status.textContent="Saved — continuing automatically.";status.className="status ok"}catch(error){status.textContent="Save failed: "+error.message;status.className="status err";submit.disabled=false}});
</script>${mermaidModule}</body></html>`;

fs.mkdirSync(outputDir, { recursive: true });
const out = path.join(outputDir, `question-${args.branch}.html`);
fs.writeFileSync(out, html);
console.log(`Wrote ${out}`);
