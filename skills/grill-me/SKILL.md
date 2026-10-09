---
name: grill-me
description: Browser-based visual interview that stress-tests a plan or design in dependency levels with parallel browser branch owners, explains core concepts with diagrams when useful, records each submitted response automatically, and continues without asking the user to type "continue". Use when the user says "grill me", wants plan decisions challenged, or wants shared understanding before implementation.
compatibility: Requires Node.js, a browser, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry. Continue correcting and retrying while each failure is clearly non-mutating and provides actionable validation feedback; do not stop merely because an earlier correction revealed another issue. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, becomes ambiguous, or cannot be corrected from the documented interface. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Keep the shell working directory at the repository root unless a step says otherwise.

## User-facing language

Before every commentary or final response, read ../talk-human/SKILL.md. It is the required response style for this workflow.

# Grill Me

Stress-test a **plan or design** with the user before implementation. Act as conductor: plan a decision DAG, dispatch independent interview branches in parallel, and integrate each level before advancing. Grounding agents gather facts so questions ask only for genuine product or engineering judgment.

Use a browser interview page for every branch. Keep the interaction model consistent with `ui-ux-grill-me`: one decision at a time per branch owner, concurrent independent browser interviews, visible options plus free-form feedback, automatic save on Submit, and automatic same-turn progression.

**Not for:** production debugging (use the globally installed `research` skill), multi-perspective debate (use global `design-council`), visual mockup comparison (use global `ui-ux-grill-me`), or committing and releasing changes.

## Hard rules

- **Browser questions required** — do not use the client's terminal user-input feature when the local browser flow can run.
- **Visible system browser required** — open human interview pages through the operating system's browser (`open` on macOS), never through Browser Use. Browser Use may run automated checks elsewhere, but it must not present grill-me questions.
- **Parallel branches, sequential local follow-ups** — independent owners may open separate browser interviews concurrently. Each owner opens one question at a time, records its answer, and closes its follow-up tree before returning.
- **Keep the turn alive** — immediately run `wait-for-response.mjs` in the same turn after opening a question; never ask the user to type `continue`, and never substitute a chat question for the wait script.
- **Keep the save server alive on a Monitor** — preflight starts the save server when needed. Immediately confirm it with `MonitorList`; if no monitor covers the save server, register it with `MonitorCreate` (with an `onDone` wake that re-checks the pending branch). Renew the inactivity timeout with `MonitorUpdate` during long waits. Never poll with shell sleep loops. Run `MonitorStop` only for the owner's own server Monitor after `stop-server.mjs` has run, on closure or before returning a blocker.
- **Use an automatically assigned session port** — never choose or reuse a fixed port. Omit `--port` from preflight so the operating system assigns an unoccupied loopback port. Preflight persists it in `<session-dir>/save-server.port`, reuses it only for later branches of that same session, and rejects explicit occupied ports.
- **Automatic recording** — Submit must persist `response-B<n>.json`; record that response in the owner's local `decision-tree.md` before its next question; the parent merges verified results at the level gate.
- **Recommended answer required** — put the evidence-backed recommendation first and mark it recommended.
- **Visualize core concepts** — when relationships, state, sequence, hierarchy, or tradeoffs are materially clearer visually, include a Mermaid diagram, focused HTML visual, or image on the question page. Skip decoration-only visuals.
- **Ground before asking** — use evidence from the repository, schema, logs, runtime, and official external sources. Ask the user only for judgment calls or unresolved choices.
- **Feature-first state** — choose a stable lowercase feature name before the interview and write only under `var/<feature-name>/grill-me/<session-slug>/`.
- **No implicit legacy resume** — ignore `var/grill-me/` for new runs; migrate a session only after explicit approval and only when the destination is absent.
- **No fake consensus** — keep unresolved branches open or explicitly defer them.
- **Separate concept visuals from UI variants** — Mermaid, inline HTML, and images in this skill explain a plan; they are not implementation candidates. Send visual UI decisions to the globally installed `ui-ux-grill-me` skill.
- **Global handoffs only** — global skill handoffs are allowed, but do not hard-code or require repository-only skill names or agent role names.

## Browser question page

For each branch `B<n>`:

1. Create `var/<feature-name>/grill-me/<slug>/questions/B<n>-options.json`:

```json
{
  "context": "Why this choice matters, grounded in evidence.",
  "recommended": "A",
  "visual": {
    "type": "mermaid",
    "content": "flowchart LR\n  A[Current state] --> B{Decision}\n  B --> C[Option A]\n  B --> D[Option B]"
  },
  "options": [
    {
      "id": "A",
      "label": "Recommended direction",
      "description": "Main benefit and tradeoff."
    },
    {
      "id": "B",
      "label": "Alternative",
      "description": "When this is preferable."
    },
    {
      "id": "D",
      "label": "Defer",
      "description": "Dependency required before deciding."
    }
  ]
}
```

`visual` is optional. Supported types:

- `mermaid` — static architecture, flow, state, or sequence diagrams.
- `html` — a focused inline visual when Mermaid cannot express the concept.
- `image` — an existing PNG/JPG under the session directory.

Use 2–6 options. Free-form response is always available, including comments-only rejection.

2. Generate the page:

```bash
node <skill-root>/scripts/generate-question.mjs \
  --feature <feature-name> \
  --session <slug> \
  --branch B1 \
  --question "Which boundary should own this behavior?" \
  --options var/<feature-name>/grill-me/<slug>/questions/B1-options.json
```

3. Preflight and open it. Never open an unverified page:

```bash
node <skill-root>/scripts/preflight-question.mjs \
  --dir var/<feature-name>/grill-me/<slug> \
  --branch B1 \
  --reset-response \
  --open
```

Preflight must print the automatically assigned port and confirm HTTP 200. It starts the save server when needed and stores the port in `save-server.port`. Do not pass `--port` during normal use.

4. Immediately wait in the active turn (mandatory — this is how answers are collected):

```bash
node <skill-root>/scripts/wait-for-response.mjs \
  --dir var/<feature-name>/grill-me/<slug> \
  --branch B1 \
  --timeout 1800
```

This step is required, not optional. Do not replace it with a chat question: a browser Submit is the only thing that writes `response-B<n>.json`. Keep the save-server Monitor active while waiting. When the wait returns, parse `response-B1.json`, update the decision tree, and continue to the next branch automatically. On timeout, verify the server is still reachable (`MonitorList` + HTTP 200), renew with `MonitorUpdate`, and wait again — never treat a timeout as an answer and never skip to chat.

Do not open pages via `file://`; response saving requires the HTTP save server.

## DAG and parallel branch ownership

Before opening the first question, the parent creates `dag.md` beside `decision-tree.md`. Use Work/Todo tracking when available: one Todo per top-level decision branch and one integration Todo per level. Record **Branch ID, Todo ID, outcome/closure criteria, dependency IDs, level, owner, session slug/artifact boundary, status, and evidence paths**. Without Todo tools, use stable local IDs; never invent Todo IDs. Validate dependencies and cycles before dispatch. The parent alone edits the shared DAG, aggregate tree, contract, and parent Todos; children write only their assigned interview artifacts.

1. Group independent ready branches into levels. A branch is ready only when required decisions are verified resolved and the previous level's integration is complete. A deferred dependency does not satisfy a required decision: explicitly re-scope or defer its dependents. Shared choices must be dependencies, not parallel guesses.
2. Dispatch independent branches concurrently through the Herdr policy below. Delegate substantial follow-up trees; keep trivial clarifications with the parent without serializing independent owners. Each owner has authority to open its own visible browser pages and ask the user directly. Concurrent browser tabs/windows are intentional; no shared-browser bottleneck or extra parent approval for each follow-up.
3. Every interviewer, including the parent handling a trivial branch, gets a unique **flat session slug**, such as `<parent-slug>-b1`, under `var/<feature-name>/grill-me/`. Use that slug in the existing helpers; do not introduce unsupported nested session paths or branch-ID formats. Each owner gets its own save server, automatically assigned port, Monitor and artifact directory. Keep helper IDs `B<n>` local; use `<owner-slug>:B<n>` in the shared DAG/tree so parallel `B1` responses cannot collide. Show the owner/decision and level in question titles.
4. The owner runs the existing browser workflow, records every `response-B<n>.json`, then follows its answer-driven children sequentially within that owner (for example A → A1 → A2). Keep local IDs stable and record parent-child links in its local tree. No new agents or edits to other owners' files. If a child needs another owner's decision, return an explicit dependency/blocker rather than guessing or waiting on the sibling.
5. An owner returns only when its entire assigned tree is resolved or explicitly deferred, or a real blocker prevents closure. Return decisions/rationale, child links, acceptance criteria, original response/evidence paths, user-approved deferred reasons/revisit conditions, blockers/cross-branch dependencies, and resource cleanup status. Comments-only rejection requires rework, not resolution. A timeout or agent completion is not a user answer.
6. The parent reads each complete result and original artifacts before marking its DAG row/Todo completed. Record resolved/deferred disposition separately from task completion; deferred decisions are not implementation requirements. Mark partial/failed owners blocked and keep the next level pending. Merge child branches into the aggregate tree with qualified IDs and original artifact paths.
7. Reconcile the whole level for conflicting decisions, overlapping scope and missing evidence. Conflicts become explicit follow-up branches; do not silently choose an agent's answer. Reopen affected owners/dependents when a decision changes. Update DAG dependencies and Todos together, then finish the level's integration Todo before opening the next level.
8. Continue automatically until every branch is verified resolved or explicitly deferred and final integration is complete. Hand off the aggregate tree and DAG plus every owner session's original evidence paths, not just a summary.

### Branch-owner assignment

When invoked as an assigned branch owner, skip parent intake, shared DAG creation, dispatch and aggregate handoff. Run only your local question/follow-up loop and return its result; do not recursively invoke the full conductor workflow.

For human interviews, choose a prompt-and-wait deadline long enough for the browser waits and follow-ups; the 15-minute runtime minimum is not a completion budget. A deadline never resolves a branch: preserve pending evidence and resume it explicitly.

Include the decision scope, level/dependencies, inherited verified decisions, closure criteria, feature name, unique owner slug, owned/forbidden paths, helper interfaces and browser authority in the prompt. Authorize follow-up questions, local tree/response writes, and its own server/Monitor lifecycle, while keeping production code read-only. State that it must close only resources it created, preserve evidence, not update parent tracking, not spawn agents, and return the complete branch result above. Evidence-only agents remain read-only and do not interview the user.

## Independent-agent policy

Apply this policy whenever the workflow uses an explorer, researcher, critic, reviewer, or any other independent agent. These are prompt responsibilities, not repository-defined skill or role names.

Before launching subagents, read and follow the globally installed `model-routing-policy` skill for model, thinking level, and Fast settings. Keep routing defaults only in that skill. Check required input modalities before launch; report incompatible models rather than silently substituting. If the default Fast setting is unavailable, omit `--fast`; if the user explicitly requested Fast, report that it is unavailable. Pass provider, model, and thinking explicitly to Pi, and verify the launch and requested Fast status before prompting. Keep every independent agent recursion-disabled.

Herdr-hosted Pi agents are the only runtime. Require `HERDR_ENV=1` and the `herdr` command, then read and follow the globally installed `herdr` skill before issuing control commands. Record the caller workspace, tab, pane, working directory, and focus state. Create one dedicated task tab per agent in the caller's workspace and working directory with `--no-focus`. Use only that tab's root pane; never split agent tabs. Parse every created tab and root-pane ID from Herdr's JSON; never guess IDs. Before starting agents, name every root pane by its distinct responsibility, apply the Herdr skill's bounded readiness gate to each, and make all agents' panes ready. Start only Pi agents with unique names and explicit provider/model/thinking settings, adding `--fast` only when chosen and supported. Save and verify every start response before prompting. An `agent_pane_busy` response after readiness follows the Herdr skill's fail-closed cleanup path and is not model fallback. Run prompts concurrently, give every productive prompt-and-wait deadline at least `900000` milliseconds (15 minutes), and collect every complete result. Herdr setup that remains failed after bounded readiness recovery, ambiguous prompt/wait failure, output loss after work, or failed provenance blocks after owned-resource cleanup. If an agent produces no usable contribution, report the failure and retry only when a suitable model is available without contradicting the user's explicit choice.

For grounding/review prompts, give a read-only scope, evidence requirements, forbidden actions and expected output. For interview owners, use the branch-owner assignment above: they may write owned artifacts and ask browser questions directly, but may not edit production code. Use agents for independent branches or distinct evidence, not redundant copies of the same interview.

| Prompt focus         | Use when                                                                 |
| -------------------- | ------------------------------------------------------------------------ |
| Repository evidence  | Existing patterns, call chains, configuration, and project documentation |
| Data evidence        | Schema and stored-data facts, using read-only access                     |
| Runtime evidence     | Logs, traces, and observed behavior                                      |
| External evidence    | Third-party behavior, preferring official sources                        |
| Consistency critique | Ownership, data flow, migration, queue, or failure-mode pressure-testing |
| Adversarial review   | Finding missing branches, unsafe assumptions, and rollout risks          |

If options still need a multi-perspective debate after the interview, hand off to the globally installed `design-council` skill.

## Workflow

### 0. Intake

Capture the plan, scope, constraints, and success criteria. Create `var/<feature-name>/grill-me/<slug>/dag.md` and `decision-tree.md` from [references/decision-tree.md](references/decision-tree.md) before opening questions.

### 1. Seed the tree

Break the plan into branches such as product scope, user model, capability boundary, data flow, failure modes, rollout, and ownership. Record dependencies, levels, closure criteria and owner boundaries in the DAG; run the smallest useful grounding pass before dispatch.

### 2. Interview loop

1. Select the current ready level and dispatch independent owners concurrently.
2. Each owner grounds facts, adds useful concept visuals, and runs its own browser question/Submit/wait loop.
3. Each owner records answers, follows answer-driven children, and returns a closed tree or explicit blocker.
4. The parent verifies original responses, merges branch results, and resolves contradictions.
5. Complete the level integration gate, then continue automatically to the next ready level until the whole DAG is resolved or explicitly deferred.

### 3. Visual handoff

When plan branches are resolved and the feature has UI decisions, start the globally installed `ui-ux-grill-me` skill with the same conceptual choices and link the parent slug. Do not re-ask decisions already recorded. Carry forward the resolved branch IDs, user rationale, constraints, and acceptance criteria so the visual interview tests the agreed product direction instead of inventing a new one.

The handoff chain is:

global `grill-me` plan decisions → global `ui-ux-grill-me` visual contract when needed → global `implement` production changes → the repository's visual and behavior verification.

### 4. Closeout

Summarize shared understanding, resolved decisions, deferred decisions, evidence, remaining risks, and the next workflow.

Each owner stops only its own save server after its final response is recorded or before returning a blocker. The parent verifies every owner session's cleanup and closes only its owned Herdr resources after collecting results. If an owner exits without cleanup, recover only its assigned session through `stop-server.mjs`, then stop its server Monitor; never kill an unrelated or guessed process:

```bash
node <skill-root>/scripts/stop-server.mjs \
  --dir var/<feature-name>/grill-me/<slug>
```

The server also shuts itself down after two idle hours. Port `0` lets the operating system atomically assign an unoccupied port for each new session. Preflight verifies the persisted port still serves the same session root, so another interview cannot silently reuse it.

## Loop limits

- One open browser question per owner, not globally; independent owner browsers run concurrently.
- No artificial question cap — interview until every branch of the design tree is resolved or explicitly deferred; nothing left silently assumed.

If the browser page cannot run, stop the save server and block the interview.

## External grounding

For every third-party claim, use official-source research through the required Herdr-hosted agent and reconcile it with repository evidence before presenting it as confirmed.

## Final report

```markdown
## Shared understanding

<what was agreed>

## Resolved decisions

| Branch | Decision | Rationale |

## Deferred

| Branch | Reason | When to revisit |

## Evidence

| Source | Finding |

## Risks still open

- …

## Artifact

- var/<feature-name>/grill-me/<slug>/dag.md
- var/<feature-name>/grill-me/<slug>/decision-tree.md
- each owner session's tree and response-*.json, linked by qualified branch ID

## Suggested next step

- a globally installed skill: ui-ux-grill-me / implement / design-council / research / none
```

## Handoff

After the user approves the plan, move every branch out of Open and list it under Resolved branches or Deferred. Exit grill-me before production implementation. Hand off the feature name, parent and owner session slugs, DAG, aggregate decision-tree path, qualified-ID-to-original-evidence paths, every resolved branch ID with its acceptance criteria, and every deferred branch ID unchanged to the globally installed `implement` skill. If the plan contains UI decisions, hand off the same parent slug, DAG, aggregate decision tree and original owner artifact paths to the globally installed `ui-ux-grill-me` skill; do not ask `implement` to infer direction from prose. Implementation must verify every resolved branch before Agent Review starts; deferred branches are not requirements. Give reviewers the decision tree and current implementation evidence directly, then run the repository's required quality, visual, behavior, and review checks before commit or pull request.
