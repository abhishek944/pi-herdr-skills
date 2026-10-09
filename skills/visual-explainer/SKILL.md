---
name: visual-explainer
description: Generate a self-contained HTML page that visually explains a system, code change, plan, comparison, or structured data.
license: MIT
compatibility: Requires a browser to view generated HTML files.
metadata:
  author: nicobailon
  version: 0.6.0
---

# Visual Explainer

Create one clear, self-contained HTML page when a visual explanation will be easier to understand than chat text. Also use it instead of a large ASCII table.

Before replying to the user, follow the global `talk-human` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Format routing

For a standalone architecture, workflow, sequence, data-flow, or lifecycle/state diagram, read and follow the global `archify` skill. It owns typed JSON authoring, rendering, validation, and diagram browser checks. Pass the question, feature name, inspected evidence, and any uncertainties; reuse the current work and todo. Archify artifacts belong under `var/<feature-name>/archify-details/`.

Keep this skill for narrative explanations, reports, tables, comparisons, dashboards, and mixed-content pages. Small embedded diagrams can stay Mermaid. If Archify is unavailable, use Mermaid/HTML and disclose that Archify validation was not performed. Do not treat a passing automated browser gate as perceptual visual review.

## Workflow

1. Identify the audience, question, and best format: cards, flowchart, sequence, table, timeline, dashboard, or slides when explicitly requested.
2. Read the relevant repository evidence and keep the content complete.
3. Choose one intentional visual style. Avoid generic purple gradients, neon dashboards, emoji headings, identical cards, and decorative animation.
4. Build semantic, responsive HTML with all CSS inline. Use Mermaid or Chart.js from a CDN only when they materially help.
5. Support narrow screens, readable contrast, reduced motion, and both light and dark mode when practical.
6. Open the file in a browser and check for clipping, broken layout, missing content, and console errors.

## Design guidance

- Make hierarchy obvious at a glance.
- Use distinctive, readable typography and a small coherent color palette.
- Use real `<table>` elements for structured rows and columns.
- Use Archify for standalone connected technical diagrams; use Mermaid for small embedded diagrams or unsupported diagram types.
- Prefer a simple overview plus detailed cards when one diagram becomes crowded.
- Keep animation limited to useful entrance or interaction feedback.
- Never sacrifice information completeness for appearance.

## Files

Write the page and any related assets only under:

```text
var/<feature-name>/visual-explainer-details/
```

Use a descriptive filename such as `architecture.html`, `plan.html`, or `comparison.html`. Do not write to a global diagrams folder.

## Final response

Give a short summary and the exact HTML path so the user can reopen it.
