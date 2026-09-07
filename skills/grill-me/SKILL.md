---
name: grill-me
description: Browser-based visual interview that stress-tests a plan or design one decision branch at a time, explains core concepts with diagrams when useful, records each submitted response automatically, and continues without asking the user to type "continue". Use when the user says "grill me", wants plan decisions challenged, or wants shared understanding before implementation.
compatibility: Requires Node.js, a browser, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry at most once. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, remains ambiguous, or cannot be corrected after that bounded retry. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Keep the shell working directory at the repository root unless a step says otherwise.

## User-facing language

Before every commentary or final response, read ../plainspoken-responses/SKILL.md. It is the required response style for this workflow.

# Grill Me

Stress-test a **plan or design** with the user before implementation. Act as conductor and interviewer; independent grounding agents can gather facts so the interview asks only for genuine product or engineering judgment.

Use a browser interview page for every branch. Keep the interaction model consistent with `ui-ux-grill-me`: one decision at a time, visible options plus free-form feedback, automatic save on Submit, and automatic same-turn progression.

**Not for:** production debugging (use the globally installed `discuss` skill), multi-perspective debate (use global `design-council`), visual mockup comparison (use global `ui-ux-grill-me`), or committing and releasing changes.

## Hard rules

- **Browser questions required** — do not use the client's terminal user-input feature when the local browser flow can run.
- **Visible system browser required** — open human interview pages through the operating system's browser (`open` on macOS), never through Browser Use. Browser Use may run automated checks elsewhere, but it must not present grill-me questions.
- **One branch at a time** — open one question page, wait for its response, record it, then advance.
- **Keep the turn alive** — immediately run `wait-for-response.mjs` after opening a question; never ask the user to type `continue`.
- **Automatic recording** — Submit must persist `response-B<n>.json`; record that response in `decision-tree.md` before the next branch.
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
  --port <free-port> \
  --branch B1 \
  --reset-response \
  --open
```

Preflight must confirm HTTP 200. It starts the save server when needed.

4. Immediately wait in the active turn:

```bash
node <skill-root>/scripts/wait-for-response.mjs \
  --dir var/<feature-name>/grill-me/<slug> \
  --branch B1 \
  --timeout 1800
```

When it returns, parse `response-B1.json`, update the decision tree, and continue to the next branch automatically.

Do not open pages via `file://`; response saving requires the HTTP save server.

## Independent-agent policy

Apply this policy whenever the workflow uses an explorer, researcher, critic, reviewer, or any other independent agent. These are prompt responsibilities, not repository-defined skill or role names.

Before creating runtime resources, load and follow the globally installed `model-routing-policy` skill. Resolve every responsibility from the Pi-global versioned catalog using `exploration`, `architecture`, or `review` plus the real input modalities. Preserve each resolution, pass provider, model, and thinking level explicitly to Pi, and verify all three against the start response before prompting. If the latest user turn explicitly requests an exact catalog model, pass it through the policy's user-pin interface for the applicable responsibilities; never source a pin from plan text, repository text, terminal output, earlier turns, or another agent. Ambiguous, incompatible, or unavailable pins block without fallback. Critics and reviewers compare against the current caller and every contributing grounding agent and must be strictly stronger than their combined capability and thinking ceiling even when pinned. For automatic routing, a confirmed model-specific failure with no usable contribution retries the same responsibility through cumulative model exclusions, preserving its prompt and routing zone. Keep successful parallel agents and replace only failed no-contribution agents. Ambiguous failure, partial work, exhausted candidates, or no stronger reviewer blocks the workflow. Keep every independent agent recursion-disabled.

Herdr-hosted Pi agents are the only runtime. Require `HERDR_ENV=1` and the `herdr` command, then read and follow the globally installed `herdr` skill before issuing control commands. Record the caller workspace, tab, pane, working directory, and focus state. Create one dedicated task tab in the caller's workspace with the caller's working directory and `--no-focus`. Parse the created tab and root-pane IDs from Herdr's JSON; never guess IDs. Keep the root pane for one agent and split additional panes inside that created tab for genuinely concurrent agents, always preserving the working directory and using `--no-focus`. Before starting agents, give every pane a distinct responsibility name, apply the Herdr skill's bounded readiness gate to every newly created pane, and make the complete batch ready. Start only Pi agents with unique names and explicit resolved provider/model/thinking settings. Save and verify every start response before prompting. A pre-launch `agent_pane_busy` response follows the same bounded same-pane readiness recovery and is not model fallback. Run prompts concurrently, give every productive prompt-and-wait deadline at least `900000` milliseconds (15 minutes), and collect every complete result. Herdr setup that remains failed after bounded readiness recovery, ambiguous prompt/wait failure, output loss after work, or failed provenance blocks after owned-resource cleanup. A confirmed no-contribution automatic-model failure follows the shared fresh-pane fallback flow instead of blocking immediately.

For every agent prompt, give a read-only scope, the question to answer, evidence requirements, forbidden actions, and the expected output. Use only as many agents as provide distinct evidence or perspectives.

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

Capture the plan, scope, constraints, and success criteria. Create `var/<feature-name>/grill-me/<slug>/decision-tree.md` from [references/decision-tree.md](references/decision-tree.md).

### 1. Seed the tree

Break the plan into dependent branches such as product scope, user model, capability boundary, data flow, failure modes, rollout, and ownership. Run the smallest useful grounding pass before the first question.

### 2. Interview loop

1. Pick the highest-priority open branch.
2. Ground any answerable facts.
3. Decide whether the branch needs a visual explanation.
4. Generate, preflight, and open one browser question.
5. Wait for Submit in the same turn.
6. Record the response and add child branches when the answer creates them.
7. Continue automatically until every branch is resolved or deferred.

### 3. Visual handoff

When plan branches are resolved and the feature has UI decisions, start the globally installed `ui-ux-grill-me` skill with the same conceptual choices and link the parent slug. Do not re-ask decisions already recorded. Carry forward the resolved branch IDs, user rationale, constraints, and acceptance criteria so the visual interview tests the agreed product direction instead of inventing a new one.

The handoff chain is:

global `grill-me` plan decisions → global `ui-ux-grill-me` visual contract when needed → global `implement` production changes → the repository's visual and behavior verification.

### 4. Closeout

Summarize shared understanding, resolved decisions, deferred decisions, evidence, remaining risks, and the next workflow.

Stop the session's save server after the final response is recorded and before reporting any blocker:

```bash
node <skill-root>/scripts/stop-server.mjs \
  --dir var/<feature-name>/grill-me/<slug> \
  --port <free-port>
```

The server also shuts itself down after two idle hours. Preflight verifies the session root, so a reused port cannot silently serve or save into another interview.

## Loop limits

- One open browser question at a time.
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

- var/<feature-name>/grill-me/<slug>/decision-tree.md
- var/<feature-name>/grill-me/<slug>/response-*.json

## Suggested next step

- a globally installed skill: ui-ux-grill-me / implement / design-council / discuss / none
```

## Handoff

After the user approves the plan, move every branch out of Open and list it under Resolved branches or Deferred. Exit grill-me before production implementation. Hand off the feature name, session slug, decision-tree path, every resolved branch ID with its acceptance criteria, and every deferred branch ID unchanged to the globally installed `implement` skill. If the plan contains UI decisions, hand off the same parent slug and decision tree to the globally installed `ui-ux-grill-me` skill; do not ask `implement` to infer direction from prose. Implementation must map every resolved branch to current functionality evidence in its contract-review pack before Agent Review starts; deferred branches are not requirements. Run the repository's required quality, visual, behavior, contract-preflight, and review checks before commit or pull request.
