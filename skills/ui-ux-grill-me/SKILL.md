---
name: ui-ux-grill-me
description: "Repository-agnostic visual UX interview: capture the current interface, present grounded design variants in a browser, record user feedback one decision at a time, and produce an implementation-ready visual contract."
compatibility: Requires Node.js, browser automation, a renderable target or mockup environment, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry. Continue correcting and retrying while each failure is clearly non-mutating and provides actionable validation feedback; do not stop merely because an earlier correction revealed another issue. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, becomes ambiguous, or cannot be corrected from the documented interface. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless project instructions say otherwise.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# UI/UX Grill Me

Help the user see and choose interface directions before implementation. This workflow is read-only on production code unless the user separately enters implementation mode.

## Rules

- Read project instructions and discover the actual UI technology, startup process, design system, routes, supported themes, and target dimensions.
- Do not assume a framework, folder layout, package manager, port, browser tool, product type, or testing workflow.
- Capture the target surface at its real useful size. Do not use a full-page screenshot when the decision concerns a panel, modal, embedded view, mobile screen, or other constrained surface.
- Use viewport screenshots for comparable options.
- Ground variants in the current interface, project design tokens, user goal, and accessibility requirements.
- Change one primary design axis per decision branch.
- Include the current UI as a baseline when it exists.
- Offer enough distinct options to make the decision meaningful, usually three to six. Include at least one conservative and one unconventional direction when appropriate.
- Comments-only rejection is valid; never force a selection.
- Keep one decision open at a time and collect its response with `wait-for-selection.mjs` in the same turn before advancing; never substitute a chat question for the wait script.
- Keep the save server alive on a Monitor — preflight starts the save server when needed. Immediately confirm it with `MonitorList`; if no monitor covers the save server, register it with `MonitorCreate` (with an `onDone` wake that re-checks the pending branch). Renew the inactivity timeout with `MonitorUpdate` during long waits. Never poll with shell sleep loops. Stop the server only after the final branch response is recorded.
- Use an automatically assigned session port — never choose or reuse a fixed port. Omit `--port` from preflight so the operating system assigns an unoccupied loopback port. Preflight persists it in `<session-dir>/save-server.port`, reuses it only for later branches of that same session, and rejects explicit occupied ports.
- Open human comparison pages through the operating system's visible browser (`open` on macOS), never through Browser Use. Browser Use remains valid for automated capture and inspection, but it must not present UI/UX interview choices.
- Preserve the selected image, source, viewport, interaction state, data fixture, and rationale. A label alone is not a visual contract.
- Never expose private data, internal identifiers, credentials, or sensitive environment details in screenshots.
- Global skill handoffs are allowed, but do not hard-code or require repository-only skill names or agent role names.

## Independent-agent policy

Apply this policy whenever the workflow uses an explorer, researcher, critic, reviewer, or any other independent agent. These are prompt responsibilities, not repository-defined skill or role names.

Use optional Pi subagent defaults: `openai-codex/gpt-6-luna` at `max` thinking with `--fast` for exploration, design grounding, and other non-review responsibilities; `openai-codex/gpt-6-sol` at `high` thinking without `--fast` for critics and reviewers. If the current user explicitly asks for another model, use their choice instead for the applicable agents, honoring any requested provider, thinking level, or speed setting. Check availability and required image or other input support before launch. If the optional default Fast setting is unavailable, omit `--fast` rather than blocking; if the user explicitly requested Fast, report that it is unavailable. Pass provider, model, and thinking explicitly to Pi, and verify the launch and requested Fast status before prompting. If an explicitly requested model is unavailable or incompatible, explain the issue rather than silently replacing it. Keep every independent agent recursion-disabled.

Herdr-hosted Pi agents are the only runtime. Require `HERDR_ENV=1` and the `herdr` command, then read and follow the globally installed `herdr` skill before issuing control commands. Record the caller workspace, tab, pane, working directory, and focus state. Create one dedicated unfocused task tab per agent in the caller's workspace and working directory. Use only its root pane; never split agent tabs. Parse all returned tab and root-pane IDs; never guess them. Name each root pane by responsibility and apply the Herdr skill's bounded readiness gate to each before starting only Pi agents with explicit provider/model/thinking settings, adding `--fast` only when chosen and supported. Verify every start response, prompt concurrently with productive prompt-and-wait deadlines of at least `900000` milliseconds (15 minutes), and collect every complete result. An `agent_pane_busy` response after readiness follows the Herdr skill's fail-closed cleanup path and is not model fallback. Herdr setup that remains failed after bounded readiness recovery, ambiguous prompt/wait failure, output loss after work, or failed provenance blocks after owned-resource cleanup. If an agent produces no usable contribution, report the failure and retry only when a suitable model is available without contradicting the user's explicit choice.

For every agent prompt, give a read-only scope, the question to answer, evidence requirements, forbidden actions, and the expected output. Use only as many agents as provide distinct evidence or perspectives.

## Artifacts

Use the repository's documented ignored artifact location. The bundled helpers use:

`var/<feature-name>/ui-ux-grill-me/<session-slug>/`

If that location conflicts with project rules, use the approved location and adapt or skip the helpers rather than writing into a forbidden path.

Create:

- a visual decision tree;
- baseline and variant screenshots;
- source mockups or live-route references;
- one saved response per branch;
- a final visual contract;
- an implementation comparison checklist.

Templates are in [references/visual-decision-tree.md](references/visual-decision-tree.md) and [references/visual-contract.md](references/visual-contract.md).

## Grounding

Before proposing variants:

1. inspect the current interface in every relevant theme and state;
2. read nearby components and design tokens;
3. identify real viewport or container dimensions;
4. identify interaction, loading, empty, error, and permission states;
5. research external UX claims when they influence the recommendation.

Use independent repository or design reviewers when they add distinct evidence or perspectives. Describe each responsibility in the prompt instead of naming a repository-specific role or skill, and follow the Herdr-first runtime policy above.

An AI-generated art-direction image is optional. If an image-generation tool is available and useful, treat its output only as inspiration. A selectable UI option must still come from a browser-rendered mockup or live implementation source.

## Branch workflow

For each branch:

1. State the user need and one design axis being decided.
2. Capture the current target surface at the exact comparison viewport.
3. Create grounded variants as live states or self-contained browser-rendered mockups.
4. Screenshot every option at the same dimensions.
5. Record source kind, location, viewport, and route for every option. In the options JSON `contract`, record the shared route, fixture, interaction state, theme, container, required behavior, and accessibility constraints.
6. Put the evidence-backed recommendation first and explain its tradeoff.
7. Generate and preflight the comparison page.
8. Open it only after confirming it is reachable.
9. Wait for a selection or comments-only response in the same turn (mandatory — this is how answers are collected):

```bash
node <skill-root>/scripts/wait-for-selection.mjs \
  --dir var/<feature-name>/ui-ux-grill-me/<session-slug> \
  --branch B1 \
  --timeout 1800
```

A browser Submit is the only thing that writes `selection-B<n>.json`. Keep the save-server Monitor active while waiting. On timeout, verify the server is still reachable (`MonitorList` + HTTP 200), renew with `MonitorUpdate`, and wait again — never treat a timeout as an answer and never skip to chat.
10. Save the response and continue to the next unresolved branch.

Start from `templates/example-options.json`; its top-level `contract` is required and is copied unchanged into the saved selection. The bundled helpers can be used as follows:

```bash
node <skill-root>/scripts/generate-comparison.mjs \
  --feature <feature-name> \
  --session <session-slug> \
  --branch B1 \
  --question "Which direction best supports this task?" \
  --options <options-json>

node <skill-root>/scripts/preflight-comparison.mjs \
  --dir var/<feature-name>/ui-ux-grill-me/<session-slug> \
  --branch B1 \
  --reset-selection \
  --open

node <skill-root>/scripts/wait-for-selection.mjs \
  --dir var/<feature-name>/ui-ux-grill-me/<session-slug> \
  --branch B1 \
  --timeout 1800
```

Preflight prints the automatically assigned port and stores it in `save-server.port`. Do not pass `--port` during normal use. Do not open comparison pages with `file://`; saved feedback requires the local HTTP server.

After the final response is recorded, stop only that session's server using its persisted port:

```bash
node <skill-root>/scripts/stop-server.mjs \
  --dir var/<feature-name>/ui-ux-grill-me/<session-slug>
```

The server also shuts itself down after two idle hours.

## Visual contract

The selected screenshot is authoritative for visible hierarchy, density, spacing, controls, copy, borders, radii, color treatment, and state. Record:

- selected screenshot and source;
- exact viewport or container size;
- route or entry point;
- theme;
- interaction state and fixture;
- required behavior;
- user modifications and rationale;
- accessibility constraints;
- deferred branches.

Implementation must reproduce and capture the same state, compare it directly, and rework material mismatches unless the user changes the contract. Hand off the feature name, UI/UX session slug, parent Grill Me slug, resolved and deferred branch IDs, selected screenshot and source, selection JSON, user modifications, route, exact viewport, fixture, and interaction state unchanged. Before Agent Review starts, hand the reviewers the decision tree, resolved decisions, selected screenshot, and current readable visual comparison directly.

## Final report

```markdown
## Shared visual understanding

<summary>

## Decisions

- <branch>: <choice and rationale>

## Deferred

- <branch and reason, or none>

## Evidence

- baseline, variants, and saved responses

## Implementation contract

- selected source and screenshot
- viewport, theme, state, and fixture
- behavior and accessibility requirements
- exact comparison checklist
- feature name, session slug, parent Grill Me slug, and resolved/deferred branch IDs
- decision-tree handoff and required current visual evidence

## Next step

- the globally installed `implement` skill, revisit a branch, or stop
```
