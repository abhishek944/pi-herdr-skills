#!/usr/bin/env node
/**
 * Generate a comparison HTML page for one ui-ux-grill-me branch.
 *
 * Usage:
 *   node generate-comparison.mjs \
 *     --feature landing-page --session landing-improve \
 *     --branch B1 \
 *     --question "Which hero layout?" \
 *     --options path/to/options.json
 *
 * options.json:
 * {
 *   "recommended": "A",
 *   "options": [
 *     { "id": "A", "category": "baseline", "label": "Current split", "description": "...", "image": "screenshots/B1-current.png" },
 *     { "id": "B", "category": "standard", "label": "Centered stack", "description": "...", "image": "screenshots/B1-centered.png" },
 *     { "id": "C", "category": "standard", "label": "Preview dominant", "description": "...", "image": "screenshots/B1-preview.png" },
 *     { "id": "D", "category": "standard", "label": "Compact split", "description": "...", "image": "screenshots/B1-compact.png" },
 *     { "id": "E", "category": "out-of-the-box", "label": "Guided canvas", "description": "...", "image": "screenshots/B1-guided.png" },
 *     { "id": "F", "category": "out-of-the-box", "label": "Command first", "description": "...", "image": "screenshots/B1-command.png" }
 *   ]
 * }
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
function parseArgs(argv) {
  const out = {
    feature: "",
    session: "",
    branch: "B1",
    question: "",
    options: "",
  };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--feature" && argv[i + 1]) out.feature = argv[++i];
    else if (argv[i] === "--session" && argv[i + 1]) out.session = argv[++i];
    else if (argv[i] === "--branch" && argv[i + 1]) out.branch = argv[++i];
    else if (argv[i] === "--question" && argv[i + 1]) out.question = argv[++i];
    else if (argv[i] === "--options" && argv[i + 1]) out.options = argv[++i];
  }
  return out;
}

function toDataUri(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  const ext = path.extname(filePath).toLowerCase();
  const mime =
    ext === ".png"
      ? "image/png"
      : ext === ".jpg" || ext === ".jpeg"
        ? "image/jpeg"
        : "image/png";
  const b64 = fs.readFileSync(filePath).toString("base64");
  return `data:${mime};base64,${b64}`;
}

function mockupIframeSrc(sessionDir, mockupHtml) {
  const full = path.isAbsolute(mockupHtml)
    ? mockupHtml
    : path.join(sessionDir, mockupHtml);
  if (!fs.existsSync(full)) return null;
  const rel = path.relative(sessionDir, full).split(path.sep).join("/");
  return `/${rel}`;
}

function readMockupFrame(sessionDir, mockupHtml, label) {
  const src = mockupIframeSrc(sessionDir, mockupHtml);
  if (!src) return '<div class="mockup-missing">Mockup missing</div>';
  return `<iframe class="mockup-iframe" src="${escapeHtml(src)}" title="${escapeHtml(label || "Variant mockup")}" loading="lazy"></iframe>`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const args = parseArgs(process.argv);
const kebab = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
if (
  !kebab.test(args.feature) ||
  !kebab.test(args.session) ||
  !args.question ||
  !args.options
) {
  console.error(
    'Usage: node generate-comparison.mjs --feature <feature-name> --session <slug> --branch B1 --question "..." --options <json>',
  );
  process.exit(1);
}

const sessionDir = path.resolve(
  process.cwd(),
  "var",
  args.feature,
  "ui-ux-grill-me",
  args.session,
);
const featureRoot = path.resolve(
  process.cwd(),
  "var",
  args.feature,
  "ui-ux-grill-me",
);
if (!sessionDir.startsWith(`${featureRoot}${path.sep}`)) {
  throw new Error(
    "Session path must stay inside the feature's ui-ux-grill-me folder",
  );
}
const comparisonsDir = path.join(sessionDir, "comparisons");
fs.mkdirSync(comparisonsDir, { recursive: true });

const configPath = path.isAbsolute(args.options)
  ? args.options
  : path.resolve(args.options);
const config = JSON.parse(fs.readFileSync(configPath, "utf8"));

if (!Array.isArray(config.options) || config.options.length !== 6) {
  throw new Error(
    "Comparison config must contain exactly 6 options: current + 3 standard + 2 out-of-the-box.",
  );
}
const categoryCounts = config.options.reduce((counts, option) => {
  counts[option.category] = (counts[option.category] || 0) + 1;
  return counts;
}, {});
if (
  categoryCounts.baseline !== 1 ||
  categoryCounts.standard !== 3 ||
  categoryCounts["out-of-the-box"] !== 2
) {
  throw new Error(
    "Option categories must be: 1 baseline, 3 standard, and 2 out-of-the-box.",
  );
}

const provenanceErrors = config.options.flatMap((option) => {
  const source = option.source;
  const errors = [];
  if (!option.image) errors.push("image screenshot path is required");
  if (!source || !["live-route", "mockup-html"].includes(source.kind)) {
    errors.push('source.kind must be "live-route" or "mockup-html"');
  }
  if (!source || typeof source.path !== "string" || !source.path.trim()) {
    errors.push("source.path is required");
  }
  if (
    !source ||
    typeof source.viewport !== "string" ||
    !source.viewport.trim()
  ) {
    errors.push("source.viewport is required");
  }
  return errors.length ? [`${option.id}: ${errors.join(", ")}`] : [];
});
if (provenanceErrors.length) {
  throw new Error(
    `Every option needs screenshot and source provenance. ${provenanceErrors.join("; ")}`,
  );
}

const missingScreenshots = config.options
  .filter((option) => !fs.existsSync(path.join(sessionDir, option.image)))
  .map((option) => `${option.id}: ${option.image}`);
if (missingScreenshots.length) {
  throw new Error(
    `Missing option screenshots: ${missingScreenshots.join(", ")}`,
  );
}
const recommended = config.recommended || config.options[0]?.id || "A";
const variantMetadata = Object.fromEntries(
  config.options.map((option) => [
    option.id,
    {
      id: option.id,
      label: option.label,
      category: option.category,
      image: option.image,
      source: option.source,
    },
  ]),
);

const optionCards = config.options
  .map((opt) => {
    const isRec = opt.id === recommended;
    const categoryLabel =
      opt.category === "out-of-the-box"
        ? "Out of the box"
        : opt.category === "standard"
          ? "Standard"
          : "Current";
    let visual = "";
    if (opt.image) {
      const uri = toDataUri(path.join(sessionDir, opt.image));
      visual = uri
        ? `<img src="${uri}" alt="${escapeHtml(opt.label)}" class="shot" />`
        : `<div class="mockup-missing">Screenshot missing: ${escapeHtml(opt.image)}</div>`;
    } else if (opt.mockupHtml) {
      visual = readMockupFrame(sessionDir, opt.mockupHtml, opt.label);
    } else if (opt.mockupInline) {
      visual = `<div class="mockup-frame">${opt.mockupInline}</div>`;
    }

    const expandButton = opt.image
      ? `<button class="expand" type="button" data-label="${escapeHtml(opt.label)}" aria-label="Expand ${escapeHtml(opt.label)}">Expand</button>`
      : "";

    return `
    <article class="option-card" data-id="${escapeHtml(opt.id)}" role="radio" aria-checked="false" tabindex="0">
      <input type="radio" name="variant" value="${escapeHtml(opt.id)}" />
      <div class="option-inner">
        <div class="option-head">
          <span class="option-id">${escapeHtml(opt.id)}</span>
          <span class="option-label">${escapeHtml(opt.label)}${isRec ? ' <em class="rec">recommended</em>' : ""}</span>
          <span class="category category-${escapeHtml(opt.category)}">${categoryLabel}</span>
        </div>
        <p class="option-desc">${escapeHtml(opt.description || "")}</p>
        <div class="option-visual">${visual}${expandButton}</div>
      </div>
    </article>`;
  })
  .join("\n");

const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>UI/UX Grill — ${escapeHtml(args.branch)}</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,600;0,700;1,400&family=Fragment+Mono&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg: #0f1419;
      --surface: #1a222d;
      --border: rgba(255,255,255,0.08);
      --text: #e8edf4;
      --dim: rgba(232,237,244,0.65);
      --accent: #86efac;
      --accent-dim: rgba(134,239,172,0.12);
      --sky: #7dd3fc;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "DM Sans", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      background-image:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(134,239,172,0.08), transparent),
        linear-gradient(var(--border) 1px, transparent 1px),
        linear-gradient(90deg, var(--border) 1px, transparent 1px);
      background-size: auto, 48px 48px, 48px 48px;
    }
    .wrap { max-width: 1400px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
    .eyebrow {
      font-family: "Fragment Mono", monospace;
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--sky);
    }
    h1 { font-size: clamp(1.35rem, 3vw, 1.85rem); font-weight: 700; margin: 0.5rem 0 0.25rem; max-width: 720px; }
    .meta { color: var(--dim); font-size: 0.9rem; margin-bottom: 1.75rem; }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1rem;
    }
    @media (max-width: 1000px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
    .option-card { cursor: pointer; display: block; }
    .option-card input { position: absolute; opacity: 0; pointer-events: none; }
    .option-inner {
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--surface);
      overflow: hidden;
      transition: border-color 0.15s, box-shadow 0.15s;
      height: 100%;
      display: flex;
      flex-direction: column;
    }
    .option-card:hover .option-inner { border-color: rgba(255,255,255,0.18); }
    .option-card:has(input:checked) .option-inner {
      border-color: var(--accent);
      box-shadow: 0 0 0 1px var(--accent), 0 8px 32px rgba(0,0,0,0.35);
    }
    .option-head {
      display: flex;
      align-items: baseline;
      gap: 0.6rem;
      padding: 0.85rem 1rem 0;
    }
    .option-id {
      font-family: "Fragment Mono", monospace;
      font-size: 12px;
      color: var(--accent);
      background: var(--accent-dim);
      padding: 0.15rem 0.45rem;
      border-radius: 6px;
    }
    .option-label { font-weight: 600; font-size: 0.95rem; }
    .rec { font-weight: 400; color: var(--dim); font-style: normal; font-size: 0.8rem; }
    .category {
      margin-left: auto;
      padding: 0.18rem 0.45rem;
      border-radius: 999px;
      color: var(--dim);
      background: rgba(255,255,255,0.06);
      font-size: 0.7rem;
      white-space: nowrap;
    }
    .category-out-of-the-box { color: #f0abfc; background: rgba(240,171,252,0.11); }
    .option-desc { margin: 0.35rem 1rem 0.75rem; color: var(--dim); font-size: 0.85rem; line-height: 1.45; }
    .option-visual {
      flex: 1;
      margin: 0 0.75rem 0.75rem;
      border-radius: 10px;
      overflow: hidden;
      background: #050914;
      height: 320px;
      border: 1px solid var(--border);
      position: relative;
    }
    .shot {
      width: 100%;
      height: 100%;
      display: block;
      object-fit: contain;
      object-position: top center;
    }
    .mockup-iframe {
      width: 100%;
      height: 100%;
      border: 0;
      display: block;
      background: #050914;
    }
    .expand {
      position: absolute;
      right: 0.65rem;
      bottom: 0.65rem;
      padding: 0.45rem 0.7rem;
      border: 1px solid rgba(255,255,255,0.22);
      border-radius: 8px;
      background: rgba(5,9,20,0.84);
      color: var(--text);
      font-size: 0.78rem;
      backdrop-filter: blur(8px);
    }
    .mockup-missing { padding: 2rem; color: var(--dim); text-align: center; font-size: 0.85rem; }
    .actions {
      margin-top: 1.5rem;
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: flex-end;
    }
    .why { flex: 1; min-width: 240px; }
    .why label { display: block; font-size: 0.8rem; color: var(--dim); margin-bottom: 0.35rem; }
    .why textarea {
      width: 100%;
      min-height: 72px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      padding: 0.65rem 0.75rem;
      font-family: inherit;
      font-size: 0.9rem;
      resize: vertical;
    }
    .submit-button {
      font-family: inherit;
      font-weight: 600;
      font-size: 0.95rem;
      padding: 0.75rem 1.5rem;
      border: none;
      border-radius: 10px;
      background: var(--accent);
      color: #050914;
      cursor: pointer;
    }
    .submit-button:disabled { opacity: 0.45; cursor: not-allowed; }
    .clear-selection {
      display: none;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: transparent;
      color: var(--dim);
      padding: 0.75rem 1rem;
      cursor: pointer;
    }
    .clear-selection.visible { display: block; }
    dialog {
      width: min(96vw, 1600px);
      height: min(92vh, 1000px);
      padding: 0;
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 14px;
      background: #050914;
      color: var(--text);
      box-shadow: 0 24px 80px rgba(0,0,0,0.65);
    }
    dialog::backdrop { background: rgba(0,0,0,0.8); backdrop-filter: blur(4px); }
    .preview-head { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; }
    .preview-head strong { font-size: 0.95rem; }
    .preview-close { border: 0; background: transparent; color: var(--text); font-size: 1.4rem; cursor: pointer; }
    .preview-image { width: 100%; height: calc(100% - 52px); object-fit: contain; object-position: top center; display: block; }
    .status { margin-top: 1rem; font-size: 0.85rem; color: var(--dim); min-height: 1.25rem; }
    .status.ok { color: var(--accent); }
    .status.err { color: #f87171; }
  </style>
</head>
<body>
  <div class="wrap">
    <p class="eyebrow">ui-ux-grill-me · ${escapeHtml(args.session)} · ${escapeHtml(args.branch)}</p>
    <h1>${escapeHtml(args.question)}</h1>
    <p class="meta">Choose a variant, or leave all choices unselected and submit comments if none feel right.</p>
    <form id="form">
      <div class="grid" role="radiogroup" aria-label="Design directions">${optionCards}</div>
      <div class="actions">
        <div class="why">
          <label for="why">Comments (optional with a selection; required if none are selected)</label>
          <textarea id="why" name="why" placeholder="Choose a direction, refine an option, or tell us why none of these work…"></textarea>
        </div>
        <button type="button" class="clear-selection" id="clear-selection">Clear selection</button>
        <button type="submit" class="submit-button" id="confirm" disabled>Submit feedback</button>
      </div>
      <p class="status" id="status" role="status"></p>
    </form>
  </div>
  <dialog id="preview-dialog">
    <div class="preview-head"><strong id="preview-label"></strong><button type="button" class="preview-close" id="preview-close" aria-label="Close expanded preview">×</button></div>
    <img class="preview-image" id="preview-image" alt="" />
  </dialog>
  <script>
    const cards = document.querySelectorAll(".option-card");
    const confirm = document.getElementById("confirm");
    const status = document.getElementById("status");
    const why = document.getElementById("why");
    const clearSelection = document.getElementById("clear-selection");
    const previewDialog = document.getElementById("preview-dialog");
    const previewImage = document.getElementById("preview-image");
    const previewLabel = document.getElementById("preview-label");
    const variantMetadata = ${JSON.stringify(variantMetadata)};
    const labels = ${JSON.stringify(
      Object.fromEntries(config.options.map((o) => [o.id, o.label])),
    )};

    function updateSubmitState() {
      const selected = document.querySelector('input[name="variant"]:checked');
      confirm.disabled = !selected && !why.value.trim();
      clearSelection.classList.toggle("visible", Boolean(selected));
    }

    function selectCard(card) {
      cards.forEach((candidate) => candidate.setAttribute("aria-checked", "false"));
      card.setAttribute("aria-checked", "true");
      card.querySelector("input").checked = true;
      updateSubmitState();
      status.textContent = "";
      status.className = "status";
    }

    cards.forEach((card) => {
      card.addEventListener("click", (event) => {
        if (event.target.closest(".expand")) return;
        selectCard(card);
      });
      card.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        selectCard(card);
      });
    });

    document.querySelectorAll(".expand").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const cardImage = button.closest(".option-visual").querySelector(".shot");
        if (!cardImage) return;
        previewImage.src = cardImage.src;
        previewImage.alt = button.dataset.label + " expanded preview";
        previewLabel.textContent = button.dataset.label;
        previewDialog.showModal();
      });
    });

    document.getElementById("preview-close").addEventListener("click", () => previewDialog.close());
    previewDialog.addEventListener("click", (event) => {
      if (event.target === previewDialog) previewDialog.close();
    });

    why.addEventListener("input", updateSubmitState);
    clearSelection.addEventListener("click", () => {
      document.querySelectorAll('input[name="variant"]').forEach((input) => { input.checked = false; });
      cards.forEach((card) => card.setAttribute("aria-checked", "false"));
      updateSubmitState();
    });

    document.getElementById("form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const selected = document.querySelector('input[name="variant"]:checked');
      const comments = why.value.trim();
      if (!selected && !comments) return;
      const selectedOption = selected ? variantMetadata[selected.value] : null;
      confirm.disabled = true;
      status.textContent = "Saving…";
      const payload = {
        questionId: ${JSON.stringify(args.branch)},
        sessionSlug: ${JSON.stringify(args.session)},
        selected: selected?.value || null,
        label: selected ? (labels[selected.value] || selected.value) : null,
        submissionType: selected ? "selection" : "comments-only",
        why: comments,
        visualContract: selectedOption
          ? {
              branch: ${JSON.stringify(args.branch)},
              question: ${JSON.stringify(args.question)},
              variantId: selectedOption.id,
              label: selectedOption.label,
              category: selectedOption.category,
              screenshot: selectedOption.image,
              source: selectedOption.source,
            }
          : null,
        timestamp: new Date().toISOString(),
      };
      try {
        const res = await fetch("/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || "Save failed");
        status.textContent = "Saved — the agent has been notified and will continue automatically.";
        status.className = "status ok";
      } catch (err) {
        status.textContent = "Save failed: " + err.message + " (is save-server running?)";
        status.className = "status err";
        confirm.disabled = false;
      }
    });
  </script>
</body>
</html>`;

const outFile = path.join(comparisonsDir, `comparison-${args.branch}.html`);
fs.writeFileSync(outFile, html);
console.log(`Wrote ${outFile}`);
