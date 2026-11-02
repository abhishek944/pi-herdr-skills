---
name: ui-ux-grill-me
description: "Repository-agnostic visual UX interview: capture the current interface, present grounded design variants in a browser, run dependency-level parallel browser interviews with autonomous branch owners, and produce an implementation-ready visual contract."
compatibility: Requires Node.js, browser automation, a renderable target or mockup environment, Herdr Core (hc), the Herdr app, and Core-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry. Continue correcting and retrying while each failure is clearly non-mutating and provides actionable validation feedback; do not stop merely because an earlier correction revealed another issue. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, becomes ambiguous, or cannot be corrected from the documented interface. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless project instructions say otherwise.

## Owner task directory

Follow the global `implement` artifact contract for every retained file. Read your own `PI_SESSION_ID` with the shell tool and use the real Work/Todo IDs returned by tracking tools:

```text
var/<sessionId>/<workId>/<taskId>/
```

A delegated branch owner uses the exact `parentTaskDir` supplied in its assignment and appends its own session-local IDs, recursively:

```text
<parentTaskDir>/<childSessionId>/<childWorkId>/<childTaskId>/
```

`<taskDir>` in the examples below means that exact owner directory. Feature names, session slugs and owner labels are metadata for the DAG, visual decision tree, page titles and qualified IDs; they never select or name a directory. If your own full session ID or real Work/Todo IDs are unavailable, stop and report the blocker instead of inventing a path.

The helpers validate `--dir` before creating anything. They accept a canonical root or nested owner task directory inside the repository `var/` and reject feature-first or legacy folders, paths outside `var/`, `..` escapes, malformed IDs, and symlinked roots that resolve outside `var/`. Screenshots, mockups, comparisons, selections and provenance must resolve inside that same owner directory. Helper-owned write targets — generated comparisons, captures, saved selections and server pid/port/log files — are also resolved through existing aliases and rejected when they would escape the owner directory, before any directory or file is created. A rejected root is a usage error, not a reason to fall back to a feature folder.

Existing `var/<feature>/ui-ux-grill-me/...` folders are historical artifacts. Link them explicitly when a resolved decision needs them, but never use them as a new output root, and do not move or rename them without explicit user approval.

## User-facing language

Before every commentary or final response, read `../talk-human/SKILL.md`.

# UI/UX Grill Me

Help the user see and choose interface directions, then automatically implement the resolved visual contract. Production code remains read-only during the interview; the parent exits interview mode and starts the globally installed `implement` skill after verified final integration.

## Rules

- Read project instructions and discover the actual UI technology, startup process, design system, routes, supported themes, and target dimensions.
- Do not assume a framework, folder layout, package manager, port, browser tool, product type, or testing workflow.
- Capture the target surface at its real useful size. Do not use a full-page screenshot when the decision concerns a panel, modal, embedded view, mobile screen, or other constrained surface.
- Use viewport screenshots for comparable options.
- Ground variants in the current interface, project design tokens, user goal, and accessibility requirements.
- Change one primary design axis per decision branch.
- Include the current UI as a baseline when it exists.
- Offer enough distinct options to make the decision meaningful, usually three to six. Include at least one conservative and one unconventional direction when appropriate.
- Choose `selectionMode: "single"` (default) for mutually exclusive designs and `"multiple"` when compatible design choices or refinements can coexist. The AI should offer multiple when useful, not require combinations to be typed in comments. Do not combine incompatible alternatives as if they were additive.
- Comments-only rejection is valid; never force a selection.
- **Canonical owner directory** — write every comparison, screenshot, mockup, selection and visual-contract artifact inside your own owner task directory, passing it as `--dir`. Feature names, session slugs and owner labels are metadata only.
- **No implicit legacy resume** — never reopen or write into a feature-first `var/<feature>/ui-ux-grill-me/...` folder; treat existing ones as historical evidence and migrate only after explicit approval and only when the destination is absent.
- Keep one decision open per branch owner, not globally. Independent owners open separate concurrent browser interviews and collect their own responses with `wait-for-selection.mjs` in the same turn; never substitute a chat question for the wait script.
- Keep the save server alive on a Monitor — preflight starts the save server when needed. Immediately confirm it with `MonitorList`; if no monitor covers the save server, register it with `MonitorCreate` (with an `onDone` wake that re-checks the pending branch). Renew the inactivity timeout with `MonitorUpdate` during long waits. Never poll with shell sleep loops. Stop only the owner's server after its final response is recorded or before returning a blocker, followed by its server Monitor.
- Use an automatically assigned session port — never choose or reuse a fixed port. Omit `--port` from preflight so the operating system assigns an unoccupied loopback port. Preflight persists it in `<taskDir>/save-server.port`, reuses it only for later branches of that same owner directory, and rejects explicit occupied ports.
- Open human comparison pages through the operating system's visible browser (`open` on macOS), never through Browser Use. Browser Use remains valid for automated capture and inspection, but it must not present UI/UX interview choices.
- Preserve the selected image, source, viewport, interaction state, data fixture, and rationale. A label alone is not a visual contract.
- Never expose private data, internal identifiers, credentials, or sensitive environment details in screenshots.
- Global skill handoffs are allowed, but do not hard-code or require repository-only skill names or agent role names.
- Invoking this skill directly or through `grill-me` authorizes the parent to implement the resolved scope after every branch is verified resolved or explicitly deferred and final integration is complete. Start global `implement` in the same turn without asking for another design approval, implementation permission, or `continue`. Honor explicit planning-only or stop instructions, keep real blockers open, and do not implement deferred scope. If no resolved implementation scope remains, report that outcome rather than inventing work. Interview owners remain read-only on production code; other action permissions remain unchanged.

## DAG and parallel branch ownership

Before opening the first question, the parent creates `dag.md` beside `visual-decision-tree.md`. Use Work/Todo tracking when available: one Todo per top-level decision branch and one integration Todo per level. Record **Branch ID, Todo ID, outcome/closure criteria, dependency IDs, level, owner, owner task directory/artifact boundary, status, and evidence paths**. Without Todo tools, use stable local IDs; never invent Todo IDs. Validate dependencies and cycles before dispatch. The parent alone edits the shared DAG, aggregate tree, contract, and parent Todos; children write only their assigned interview artifacts.

1. Group independent ready branches into levels. A branch is ready only when required decisions are verified resolved and the previous level's integration is complete. A deferred dependency does not satisfy a required decision: explicitly re-scope or defer its dependents. Shared choices must be dependencies, not parallel guesses.
2. Dispatch independent branches concurrently through the Herdr policy below. Delegate substantial follow-up trees; keep trivial clarifications with the parent without serializing independent owners. Each owner has authority to open its own visible browser pages and ask the user directly. Concurrent browser tabs/windows are intentional; no shared-browser bottleneck or extra parent approval for each follow-up.
3. Every interviewer, including the parent handling a trivial branch, works in one canonical owner task directory. The parent uses its own owner directory; a delegated owner uses its assignment's exact `parentTaskDir` plus its own `<sessionId>/<workId>/<taskId>` triple. Give every owner a short **label**, such as `b1`, used only in page titles and qualified IDs; a label never selects a directory. Each owner gets its own save server, automatically assigned port, Monitor and owner directory. Keep helper IDs `B<n>` local; use `<owner-label>:B<n>` in the shared DAG/tree so parallel `B1` responses cannot collide. Show the owner/decision and level in question titles.
4. The owner runs the existing browser workflow, records every `selection-B<n>.json`, then follows its answer-driven children sequentially within that owner (for example A → A1 → A2). Keep local IDs stable and record parent-child links in its local tree. No new agents or edits to other owners' files. If a child needs another owner's decision, return an explicit dependency/blocker rather than guessing or waiting on the sibling.
5. An owner returns only when its entire assigned tree is resolved or explicitly deferred, or a real blocker prevents closure. Return decisions/rationale, child links, acceptance criteria, its canonical task directory and session/Work/Task IDs, original response/evidence paths, user-approved deferred reasons/revisit conditions, blockers/cross-branch dependencies, and resource cleanup status. Comments-only rejection requires rework, not resolution. A timeout or agent completion is not a user answer.
6. The parent reads each complete result and original artifacts before marking its DAG row/Todo completed. Record resolved/deferred disposition separately from task completion; deferred decisions are not implementation requirements. Mark partial/failed owners blocked and keep the next level pending. Merge child branches into the aggregate tree with qualified IDs and original artifact paths.
7. Reconcile the whole level for conflicting decisions, overlapping scope and missing evidence. Conflicts become explicit follow-up branches; do not silently choose an agent's answer. Reopen affected owners/dependents when a decision changes. Update DAG dependencies and Todos together, then finish the level's integration Todo before opening the next level.
8. Continue automatically until every branch is verified resolved or explicitly deferred and final integration is complete. Hand off the aggregate tree and DAG plus every owner task directory's original evidence paths, not just a summary.

### Branch-owner assignment

When invoked as an assigned branch owner, skip parent intake, shared DAG creation, dispatch and aggregate handoff. Run only your local comparison/follow-up loop and return its result; do not recursively invoke the full conductor workflow.

For human interviews, choose a prompt-and-wait deadline long enough for the browser waits and follow-ups; the 15-minute runtime minimum is not a completion budget. A deadline never resolves a branch: preserve pending evidence and resume it explicitly.

Include the decision scope, level/dependencies, inherited verified decisions, closure criteria, feature name, owner label, real session/Work/Task IDs, the exact parent task directory, owned/forbidden paths, helper interfaces and browser authority in the prompt. Require the owner to create its own tracking and canonical nested task directory, and authorize follow-up questions, local tree/response writes, and its own server/Monitor lifecycle, while keeping production code read-only. State that it must close only resources it created, preserve evidence, not update parent tracking, not spawn agents, and return the complete branch result above. Evidence-only agents remain read-only and do not interview the user.

Resolve shared layout, navigation, design tokens and interaction foundations before dispatching independent visual axes. Give owners the same verified foundation and comparison constraints. Use isolated browser capture contexts and mockups; do not mutate a shared live fixture, theme or route state concurrently. Parent integration checks that selected designs fit together before the next level.

## Independent-agent policy

Apply this policy whenever the workflow uses an explorer, researcher, critic, reviewer, or any other independent agent. These are prompt responsibilities, not repository-defined skill or role names.

Before launching subagents, read and follow the globally installed `model-routing-policy` skill for model, thinking level, and Fast settings. Keep routing defaults only in that skill. Check required image or other input support before launch; report incompatible models rather than silently substituting. If the default Fast setting is unavailable, omit `--fast`; if the user explicitly requested Fast, report that it is unavailable. Pass provider, model, and thinking explicitly to Pi, and verify the launch and requested Fast status before prompting. Keep every independent agent recursion-disabled.

Core-hosted interactive Pi agents are the only runtime. Read and follow global herdr before control commands. Use hc for lifecycle and herdr-app for display; require a verified real HC_TERMINAL_ID parent, not HERDR_ENV or the retired herdr TUI CLI. A valid Core session must not be rejected because old TUI variables are absent. Prefer the updated Agent tools. Give every agent a dedicated visible tab in the parent's real app space, named exactly with its parent delegated Task ID, never a hidden child or a shared split. Read actual terminalId/tabId handles from results; task labels may repeat across sessions. Pass explicit model-routing-policy provider/model/thinking and supported optional fast settings, verify native Pi input readiness and the tab mapping, then confirm a continuous MonitorCreate hcTerminalId subscription is ready before sending assignments. Retain that monitor across follow-ups and dispatch ready independent branches concurrently. Give productive interview work at least 15 minutes; a deadline is not branch closure. Inspect real output and owned artifacts before accepting results. On partial startup, ambiguous delivery, lost output or monitoring failure, diagnose with actual handles and return a precise blocker without blindly relaunching or bypassing consent. Retry only after a verified correction and without contradicting model choices. Close only owned resources after results and follow-ups are collected. Unavailable Core/app/tools/monitoring is a tooling blocker, not permission to silently collapse required parallel branches.

For grounding/review prompts, give a read-only scope, evidence requirements, forbidden actions and expected output. Interview owners may create assigned mockups, screenshots and local trees and ask browser questions directly, but production code stays read-only. Use the branch-owner assignment above and avoid redundant interviews.

## Artifacts

Every retained artifact belongs to one canonical owner task directory: `var/<sessionId>/<workId>/<taskId>/` for a root owner, or the nested delegated triple beneath the exact parent task directory. The bundled helpers take that directory as `--dir` and keep every contained path (comparisons, screenshots, mockups, selections, logs) inside it. Do not use a feature-named folder as an output root.

Create in the owner directory:

- a parent-owned Todo-linked `dag.md` before the first comparison, plus an aggregate visual decision tree;
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

## Level workflow

1. Create the DAG and resolve shared foundations; assign each owner a canonical task directory and a display label.
2. Dispatch ready independent branches concurrently. Each owner runs the branch workflow below and closes all local follow-ups or returns an explicit blocker.
3. Verify original selections/screenshots/source, merge qualified child branches, and reconcile the level's visual consistency and accessibility.
4. Finish the level integration gate before opening the next level. Complete final integration before handing off the aggregate visual contract and all original owner artifact paths.

## Branch workflow

For each branch within its owner's task directory:

1. State the user need and one design axis being decided.
2. Capture the current target surface at the exact comparison viewport.
3. Create grounded variants as live states or self-contained browser-rendered mockups.
4. Screenshot every option at the same dimensions. The bundled capture helper keeps the output inside the owner directory:

```bash
node <skill-root>/scripts/capture-viewport.mjs \
  --url <target-url> \
  --dir <taskDir> \
  --out screenshots/B1-variant-B.png \
  --session <browser-session>
```
5. Record source kind, location, viewport, and route for every option. In the options JSON `contract`, record the shared route, fixture, interaction state, theme, container, required behavior, and accessibility constraints.
6. Put the evidence-backed recommendation first and explain its tradeoff.
7. Generate and preflight the comparison page.
8. Open it only after confirming it is reachable.
9. Wait for a selection or comments-only response in the same turn (mandatory — this is how answers are collected):

```bash
node <skill-root>/scripts/wait-for-selection.mjs \
  --dir <taskDir> \
  --branch B1 \
  --timeout 1800
```

A browser Submit is the only thing that writes `selection-B<n>.json`. Keep the save-server Monitor active while waiting. On timeout, verify the server is still reachable (`MonitorList` + HTTP 200), renew with `MonitorUpdate`, and wait again — never treat a timeout as an answer and never skip to chat.
10. Record the response in the owner's local visual decision tree. Rework comments-only rejection, follow answer-driven children, and continue until the assigned tree is resolved or explicitly deferred; return evidence to the parent for integration.

Start from `templates/example-options.json`; its top-level `contract` is required and is copied unchanged into each saved visual contract. Set top-level `selectionMode` to `"single"` or `"multiple"` per question; omission defaults to single, and other values are rejected. Multiple mode uses independently toggleable checkboxes/cards with mouse and keyboard support. Clear selection removes all choices without erasing comments; comments-only submission remains valid.

Saved responses include `selectionMode` plus `selectedIds`, `selectedLabels`, and `visualContracts` arrays in displayed option order, preserving every selected screenshot and source. Read arrays first, with legacy `selected`, `label`, and `visualContract` fallback only when arrays are absent. Compatibility scalar fields and singular visual contract are populated only for exactly one choice, otherwise null. `submissionType: "selection"` means one or more choices; comments-only has empty arrays. Responses also record provenance metadata: `taskDir` (the repository-relative owner directory), `ownerLabel`, and the optional descriptive `sessionSlug`; that metadata never selects a directory.

When several variants are selected, record every choice and its provenance, but keep the branch open for synthesis. Clarify which parts should combine, resolve conflicts, and present a coherent combined browser-rendered candidate for user acceptance in a single-select follow-up. Do not treat several different screenshots as one authoritative implementation contract or silently choose the first selection. Preserve original selections alongside the accepted combined screenshot/source and rationale.

The bundled helpers can be used as follows:

```bash
node <skill-root>/scripts/generate-comparison.mjs \
  --dir <taskDir> \
  --label <owner-label> \
  --branch B1 \
  --question "Which direction best supports this task?" \
  --options <taskDir>/questions/B1-options.json

node <skill-root>/scripts/preflight-comparison.mjs \
  --dir <taskDir> \
  --branch B1 \
  --reset-selection \
  --open

node <skill-root>/scripts/wait-for-selection.mjs \
  --dir <taskDir> \
  --branch B1 \
  --timeout 1800
```

Preflight prints the automatically assigned port and stores it in `<taskDir>/save-server.port`. Do not pass `--port` during normal use. Do not open comparison pages with `file://`; saved feedback requires the local HTTP server.

After the owner's final response is recorded, or before returning a blocker, stop only that owner's server using its persisted port. The parent verifies cleanup for every owner directory and closes only its owned Herdr resources after collecting results. If an owner exits without cleanup, recover only its assigned owner directory through `stop-server.mjs`, then stop its server Monitor; never kill an unrelated or guessed process:

```bash
node <skill-root>/scripts/stop-server.mjs \
  --dir <taskDir>
```

After `stop-server.mjs` returns, stop only the Monitor covering that owner's save server. The server also shuts itself down after two idle hours.

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

Implementation must reproduce and capture the same state, compare it directly, and rework material mismatches unless the user changes the contract. Hand off the feature name, the UI/UX parent and owner task directory paths and labels, the parent Grill Me task directory, resolved and deferred branch IDs, selected screenshot and source, selection JSON, user modifications, route, exact viewport, fixture, and interaction state unchanged. Hand off exact paths; do not ask a receiver to reconstruct them from a label. Before Agent Review starts, hand the reviewers the decision tree, resolved decisions, selected screenshot, and current readable visual comparison directly.

## Final report

Record this report before the automatic implementation handoff; it is not a stopping point unless the user explicitly requested planning only or stopped the workflow, or a real blocker remains. After owner cleanup, the parent exits interview mode and starts global `implement` in the same turn with the unchanged visual contract and evidence.

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
- feature name, UI/UX parent and owner task directory paths and labels, parent Grill Me task directory, and resolved/deferred branch IDs
- aggregate decision-tree/DAG handoff, qualified branch IDs, original owner artifact paths, and required current visual evidence

## Handoff status

- global implement started automatically with the verified visual contract
- or explicit planning-only/stop instruction or unresolved blocker preventing handoff
```
