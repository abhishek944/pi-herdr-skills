---
name: ui-ux-grill-me
description: "Show grounded interface options, collect one visual decision at a time, and produce an implementation-ready visual contract."
compatibility: Requires a renderable interface or browser mockup environment.
---

# UI/UX Grill Me

Help the user see and choose interface directions before implementation. Keep production code read-only.

Before replying to the user, follow the global `plainspoken-responses` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read project instructions and discover the real UI stack, routes, themes, design system, and target dimensions.
- Use the current interface as a baseline when it exists.
- Change one main design choice per question.
- Use the same viewport, content, theme, and interaction state for comparable options.
- Ground options in existing design tokens, accessibility, and the user's goal.
- Ask one question at a time in chat. Comments-only rejection is valid.
- Do not expose private data or credentials in screenshots.
- Preserve the chosen screenshot, source, viewport, state, rationale, and user modifications.

## Workflow

1. Capture the current target surface at its useful size.
2. Create a small set of distinct browser-rendered options, normally three to six.
3. Put the recommended option first and explain its tradeoff.
4. Open the comparison page or screenshots for the user.
5. Ask for one selection or free-form response in chat.
6. Record the answer and continue to the next unresolved visual decision.
7. Produce a concise visual contract for implementation.

## Files

Write all material only under:

```text
var/<feature-name>/ui-ux-grill-me-details/
```

Useful files include `decision-tree.md`, `comparison-<n>.html`, screenshots, `response-<n>.md`, and `visual-contract.md`.

## Visual contract

Record the selected source and screenshot, exact viewport or container, route, theme, interaction state, fixture, required behavior, accessibility constraints, user modifications, rationale, and deferred choices.

## Final response

Summarize the decisions, deferred items, saved evidence, implementation contract, and next step.
