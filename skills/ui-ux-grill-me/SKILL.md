---
name: ui-ux-grill-me
description: "Repository-agnostic visual UX interview: capture the current interface, present grounded design variants in a browser, run dependency-level parallel browser interviews with autonomous branch owners, and produce an implementation-ready visual contract."
compatibility: Requires Node.js, browser automation, a renderable target or mockup environment, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry. Continue correcting and retrying while each failure is clearly non-mutating and provides actionable validation feedback; do not stop merely because an earlier correction revealed another issue. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, becomes ambiguous, or cannot be corrected from the documented interface. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless project instructions say otherwise.

## User-facing language

Before every commentary or final response, read `../talk-human/SKILL.md`.

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
- Keep one decision open per branch owner, not globally. Independent owners open separate concurrent browser interviews and collect their own responses with `wait-for-selection.mjs` in the same turn; never substitute a chat question for the wait script.
- Keep the save server alive on a Monitor — preflight starts the save server when needed. Immediately confirm it with `MonitorList`; if no monitor covers the save server, register it with `MonitorCreate` (with an `onDone` wake that re-checks the pending branch). Renew the inactivity timeout with `MonitorUpdate` during long waits. Never poll with shell sleep loops. Stop only the owner's server after its final response is recorded or before returning a blocker, followed by its server Monitor.
- Use an automatically assigned session port — never choose or reuse a fixed port. Omit `--port` from preflight so the operating system assigns an unoccupied loopback port. Preflight persists it in `<session-dir>/save-server.port`, reuses it only for later branches of that same session, and rejects explicit occupied ports.
- Open human comparison pages through the operating system's visible browser (`open` on macOS), never through Browser Use. Browser Use remains valid for automated capture and inspection, but it must not present UI/UX interview choices.
- Preserve the selected image, source, viewport, interaction state, data fixture, and rationale. A label alone is not a visual contract.
- Never expose private data, internal identifiers, credentials, or sensitive environment details in screenshots.
- Global skill handoffs are allowed, but do not hard-code or require repository-only skill names or agent role names.

## DAG and parallel branch ownership

Before opening the first question, the parent creates `dag.md` beside `visual-decision-tree.md`. Use Work/Todo tracking when available: one Todo per top-level decision branch and one integration Todo per level. Record **Branch ID, Todo ID, outcome/closure criteria, dependency IDs, level, owner, session slug/artifact boundary, status, and evidence paths**. Without Todo tools, use stable local IDs; never invent Todo IDs. Validate dependencies and cycles before dispatch. The parent alone edits the shared DAG, aggregate tree, contract, and parent Todos; children write only their assigned interview artifacts.

1. Group independent ready branches into levels. A branch is ready only when required decisions are verified resolved and the previous level's integration is complete. A deferred dependency does not satisfy a required decision: explicitly re-scope or defer its dependents. Shared choices must be dependencies, not parallel guesses.
2. Dispatch independent branches concurrently through the Herdr policy below. Delegate substantial follow-up trees; keep trivial clarifications with the parent without serializing independent owners. Each owner has authority to open its own visible browser pages and ask the user directly. Concurrent browser tabs/windows are intentional; no shared-browser bottleneck or extra parent approval for each follow-up.
3. Every interviewer, including the parent handling a trivial branch, gets a unique **flat session slug**, such as `<parent-slug>-b1`, under `var/<feature-name>/ui-ux-grill-me/`. Use that slug in the existing helpers; do not introduce unsupported nested session paths or branch-ID formats. Each owner gets its own save server, automatically assigned port, Monitor and artifact directory. Keep helper IDs `B<n>` local; use `<owner-slug>:B<n>` in the shared DAG/tree so parallel `B1` responses cannot collide. Show the owner/decision and level in question titles.
4. The owner runs the existing browser workflow, records every `selection-B<n>.json`, then follows its answer-driven children sequentially within that owner (for example A → A1 → A2). Keep local IDs stable and record parent-child links in its local tree. No new agents or edits to other owners' files. If a child needs another owner's decision, return an explicit dependency/blocker rather than guessing or waiting on the sibling.
5. An owner returns only when its entire assigned tree is resolved or explicitly deferred, or a real blocker prevents closure. Return decisions/rationale, child links, acceptance criteria, original response/evidence paths, user-approved deferred reasons/revisit conditions, blockers/cross-branch dependencies, and resource cleanup status. Comments-only rejection requires rework, not resolution. A timeout or agent completion is not a user answer.
6. The parent reads each complete result and original artifacts before marking its DAG row/Todo completed. Record resolved/deferred disposition separately from task completion; deferred decisions are not implementation requirements. Mark partial/failed owners blocked and keep the next level pending. Merge child branches into the aggregate tree with qualified IDs and original artifact paths.
7. Reconcile the whole level for conflicting decisions, overlapping scope and missing evidence. Conflicts become explicit follow-up branches; do not silently choose an agent's answer. Reopen affected owners/dependents when a decision changes. Update DAG dependencies and Todos together, then finish the level's integration Todo before opening the next level.
8. Continue automatically until every branch is verified resolved or explicitly deferred and final integration is complete. Hand off the aggregate tree and DAG plus every owner session's original evidence paths, not just a summary.

### Branch-owner assignment

When invoked as an assigned branch owner, skip parent intake, shared DAG creation, dispatch and aggregate handoff. Run only your local comparison/follow-up loop and return its result; do not recursively invoke the full conductor workflow.

For human interviews, choose a prompt-and-wait deadline long enough for the browser waits and follow-ups; the 15-minute runtime minimum is not a completion budget. A deadline never resolves a branch: preserve pending evidence and resume it explicitly.

Include the decision scope, level/dependencies, inherited verified decisions, closure criteria, feature name, unique owner slug, owned/forbidden paths, helper interfaces and browser authority in the prompt. Authorize follow-up questions, local tree/response writes, and its own server/Monitor lifecycle, while keeping production code read-only. State that it must close only resources it created, preserve evidence, not update parent tracking, not spawn agents, and return the complete branch result above. Evidence-only agents remain read-only and do not interview the user.

Resolve shared layout, navigation, design tokens and interaction foundations before dispatching independent visual axes. Give owners the same verified foundation and comparison constraints. Use isolated browser capture contexts and mockups; do not mutate a shared live fixture, theme or route state concurrently. Parent integration checks that selected designs fit together before the next level.

## Independent-agent policy

Apply this policy whenever the workflow uses an explorer, researcher, critic, reviewer, or any other independent agent. These are prompt responsibilities, not repository-defined skill or role names.

Before launching subagents, read and follow the globally installed `model-routing-policy` skill for model, thinking level, and Fast settings. Keep routing defaults only in that skill. Check required image or other input support before launch; report incompatible models rather than silently substituting. If the default Fast setting is unavailable, omit `--fast`; if the user explicitly requested Fast, report that it is unavailable. Pass provider, model, and thinking explicitly to Pi, and verify the launch and requested Fast status before prompting. Keep every independent agent recursion-disabled.

Herdr-hosted Pi agents are the only runtime. Require `HERDR_ENV=1` and the `herdr` command, then read and follow the globally installed `herdr` skill before issuing control commands. Record the caller workspace, tab, pane, working directory, and focus state. Create one dedicated unfocused task tab per agent in the caller's workspace and working directory. Use only its root pane; never split agent tabs. Parse all returned tab and root-pane IDs; never guess them. Name each root pane by responsibility and apply the Herdr skill's bounded readiness gate to each before starting only Pi agents with explicit provider/model/thinking settings, adding `--fast` only when chosen and supported. Verify every start response, prompt concurrently with productive prompt-and-wait deadlines of at least `900000` milliseconds (15 minutes), and collect every complete result. An `agent_pane_busy` response after readiness follows the Herdr skill's fail-closed cleanup path and is not model fallback. Herdr setup that remains failed after bounded readiness recovery, ambiguous prompt/wait failure, output loss after work, or failed provenance blocks after owned-resource cleanup. If an agent produces no usable contribution, report the failure and retry only when a suitable model is available without contradicting the user's explicit choice.

For grounding/review prompts, give a read-only scope, evidence requirements, forbidden actions and expected output. Interview owners may create assigned mockups, screenshots and local trees and ask browser questions directly, but production code stays read-only. Use the branch-owner assignment above and avoid redundant interviews.

## Artifacts

Use the repository's documented ignored artifact location. The bundled helpers use:

`var/<feature-name>/ui-ux-grill-me/<session-slug>/`

If that location conflicts with project rules, use the approved location and adapt or skip the helpers rather than writing into a forbidden path.

Create:

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

1. Create the DAG and resolve shared foundations; assign unique owner sessions and artifact boundaries.
2. Dispatch ready independent branches concurrently. Each owner runs the branch workflow below and closes all local follow-ups or returns an explicit blocker.
3. Verify original selections/screenshots/source, merge qualified child branches, and reconcile the level's visual consistency and accessibility.
4. Finish the level integration gate before opening the next level. Complete final integration before handing off the aggregate visual contract and all original owner artifact paths.

## Branch workflow

For each branch within its owner's session:

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
10. Record the response in the owner's local visual decision tree. Rework comments-only rejection, follow answer-driven children, and continue until the assigned tree is resolved or explicitly deferred; return evidence to the parent for integration.

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

After the owner's final response is recorded, or before returning a blocker, stop only that owner's session server using its persisted port. The parent verifies cleanup for every owner and closes only its owned Herdr resources after collecting results. If an owner exits without cleanup, recover only its assigned session through `stop-server.mjs`, then stop its server Monitor; never kill an unrelated or guessed process:

```bash
node <skill-root>/scripts/stop-server.mjs \
  --dir var/<feature-name>/ui-ux-grill-me/<session-slug>
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
- aggregate decision-tree/DAG handoff, qualified branch IDs, original owner artifact paths, and required current visual evidence

## Next step

- the globally installed `implement` skill, revisit a branch, or stop
```
