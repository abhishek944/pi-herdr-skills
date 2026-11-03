---
name: grill-me
description: Browser-based visual interview that stress-tests a plan or design in dependency levels with parallel browser branch owners, explains core concepts with diagrams when useful, records each submitted response automatically, and continues without asking the user to type "continue". Use when the user says "grill me", wants plan decisions challenged, or wants shared understanding before implementation.
compatibility: Requires Pi 1.4-compatible pi-decisions and pi-loop-monitor extensions, Node.js, a browser, Herdr Core (hc), the Herdr app, and Core-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry. Continue correcting and retrying while each failure is clearly non-mutating and provides actionable validation feedback; do not stop merely because an earlier correction revealed another issue. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, becomes ambiguous, or cannot be corrected from the documented interface. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Keep the shell working directory at the repository root unless a step says otherwise.

Interview delivery uses only the direct `SubmitQuestion` and `WaitForAnswer` tools from `@abhishek944/pi-decisions`. If either tool is unavailable, report the installation or reload blocker rather than using another interface or starting a server.

## Owner task directory

Follow the global `implement` artifact contract for every retained file. Read your own `PI_SESSION_ID` with the shell tool and use the real Work/Todo IDs returned by tracking tools:

```text
var/<sessionId>/<workId>/<taskId>/
```

A delegated branch owner uses the exact `parentTaskDir` supplied in its assignment and appends its own session-local IDs, recursively:

```text
<parentTaskDir>/<childSessionId>/<childWorkId>/<childTaskId>/
```

`<taskDir>` in the examples below means that exact owner directory. Feature names, owner labels and branch labels are metadata for the DAG, decision tree, page titles and qualified IDs; they never select or name a directory. If your own full session ID or real Work/Todo IDs are unavailable, stop and report the blocker instead of inventing a path.

Skill-owned evidence and any helper outputs follow this artifact boundary. This is agent coordination, not a question-tool input requirement: SubmitQuestion receives content directly and resolves explicit media using complete absolute paths; it never receives or looks up the active task folder.

Existing `var/<feature>/grill-me/...` folders are historical artifacts. Link them explicitly when a resolved decision needs them, but never use them as a new output root, and do not move or rename them without explicit user approval.

## User-facing language

Before every commentary or final response, read ../talk-human/SKILL.md. It is the required response style for this workflow.

# Grill Me

Stress-test a **plan or design** with the user before implementation. Act as conductor: plan a decision DAG, dispatch independent interview branches in parallel, and integrate each level before advancing. Grounding agents gather facts so questions ask only for genuine product or engineering judgment.

Use a browser interview page for every branch. Keep the interaction model consistent with `ui-ux-grill-me`: one decision at a time per branch owner, concurrent independent browser interviews, visible options plus free-form feedback, automatic save on Submit, and automatic progression when the answer watcher wakes Pi.

**Not for:** production debugging (use the globally installed `research` skill), multi-perspective debate (use global `design-council`), visual mockup comparison (use global `ui-ux-grill-me`), or committing and releasing changes.

## Hard rules

- **Browser questions required** — do not use the client's terminal user-input feature when the local browser flow can run.
- **Human-visible URL required** — share the URL returned by `SubmitQuestion`. For local delivery, open it through the operating system's visible browser (`open` on macOS); for here.now, the user opens the shared HTTPS link on their own device. Browser Use is for automated checks, never a substitute for presenting human choices.
- **Parallel branches, sequential local follow-ups** — independent owners may open separate browser interviews concurrently. Each owner opens one question at a time, records its answer, and closes its follow-up tree before returning.
- **Automatic continuation required** — immediately call `WaitForAnswer` after presenting a question. If it returns waiting, verify its watcher is registered and yield while the owning task is blocked on user input; the monitor wakes Pi when an answer or actionable error arrives. Never ask the user to type `continue` and never resolve a branch from a waiting receipt.
- **One delivery owner** — pi-decisions owns the local server or here.now Site Data mapping, answer archive, and question watcher; pi-loop-monitor owns background execution and wake delivery. Do not start legacy save servers or model-facing polling loops alongside these tools. Check `MonitorList` for actual watcher state; a failed monitor is not a user response.
- **Configured backend** — global Pi settings select `"pi-decisions": {"backend":"local"}` (the default) or explicitly `"here.now"`. Local mode assigns a loopback port automatically. Do not override the user's choice or silently fall back between local and hosted delivery. Hosted pages must contain only the intended non-sensitive interview assets, never the whole task directory.
- **Automatic recording** — the tool archives the answer at its returned `responsePath`. After collecting it, archive an unchanged skill-owned copy as `response-B<n>.json` in the owner artifact directory and record it in the local decision tree before the next question; the parent verifies these copies at the level gate.
- **Recommended answer required** — put the evidence-backed recommendation first and mark it recommended.
- **Visualize core concepts** — when relationships, state, sequence, hierarchy, or tradeoffs are materially clearer visually, include a Mermaid diagram or image content block on the question page. Skip decoration-only visuals.
- **Ground before asking** — use evidence from the repository, schema, logs, runtime, and official external sources. Ask the user only for judgment calls or unresolved choices.
- **Canonical owner directory** — write skill-owned interview evidence only inside your own owner task directory (see [Owner task directory](#owner-task-directory)). Do not pass it to the question tools. Referenced media uses complete absolute paths. Feature names, owner labels and branch labels are metadata only.
- **No implicit legacy resume** — never reopen or write into `var/grill-me/` or any feature-first session folder; treat existing ones as historical evidence and migrate a session only after explicit approval and only when the destination is absent.
- **No fake consensus** — keep unresolved branches open or explicitly defer them.
- **Separate concept visuals from UI variants** — Mermaid and image content blocks in this skill explain a plan; they are not implementation candidates. Send visual UI decisions to the globally installed `ui-ux-grill-me` skill.
- **Global handoffs only** — global skill handoffs are allowed, but do not hard-code or require repository-only skill names or agent role names.
- **Automatic implementation handoff** — invoking this skill authorizes the parent to continue into implementation of the resolved scope after every branch is verified resolved or explicitly deferred and final integration is complete. Do not ask for another plan approval, implementation permission, or `continue`. Start global `ui-ux-grill-me` first when visual decisions are needed; otherwise start global `implement` in the same turn. Honor explicit planning-only or stop instructions, keep real blockers open, and do not implement deferred scope. Interview owners remain read-only on production code; the parent exits interview mode before implementation. Other action permissions remain unchanged.

## Browser question page

For each branch `B<n>`, submit the content directly. Use a session-unique safe question ID such as `<owner-label>-B1`; display-qualified branch IDs such as `<owner-label>:B1` remain decision-tree metadata, not filenames.

```json
{
  "questionId": "<owner-label>-B1",
  "mode": "single",
  "question": "Which boundary should own this behavior?",
  "label": "<owner-label>",
  "content": [
    { "type": "text", "text": "Why this choice matters, grounded in evidence." },
    { "type": "mermaid", "code": "flowchart LR\nA[Current state] --> B{Decision}\nB --> C[Option A]\nB --> D[Option B]" }
  ],
  "recommended": "A",
  "options": [
    { "id": "A", "label": "Recommended direction", "content": [{ "type": "text", "text": "Main benefit and tradeoff." }] },
    { "id": "B", "label": "Alternative", "content": [{ "type": "text", "text": "When this is preferable." }] },
    { "id": "D", "label": "Defer", "content": [{ "type": "text", "text": "Dependency required before deciding." }] }
  ]
}
```

Use 2–6 options as this skill's interview policy, not a tool quota. Set `mode: "single"` for mutually exclusive alternatives and `"multiple"` for compatible choices that can coexist; it is required, not inferred. Keep incompatible alternatives or a mutually exclusive Defer choice in a separate single-choice question. Use `mode: "review"` without options/recommendation only when open-ended feedback is the intended interaction.

General and option-level `content` use the same ordered blocks: `{type:"text",text}`, `{type:"image",path,alt,caption?}`, `{type:"video",path,caption?}`, or `{type:"mermaid",code,caption?}`. Media `path` values must be complete absolute filesystem paths. No task folder, options file, raw HTML, or delivery setting is passed to either tool. Use images or Mermaid for concept visuals; render an HTML explanation into an image if needed rather than submitting HTML.

1. Call `SubmitQuestion` with the direct object. It returns the actual URL, response path and state path. Save the returned `responsePath` as the answer location; do not infer it from a task directory. Identical immutable content reuses the question; revised content requires a fresh question ID.
2. Verify the returned page is reachable and share its URL. Open local URLs in the visible system browser. For hosted pages, send the URL to the user; opening a browser on the remote machine does not present it on the user's device.
3. Immediately call `WaitForAnswer`:

```json
{ "questionId": "<owner-label>-B1" }
```

An existing answer returns immediately. Otherwise verify the returned watcher through `MonitorList`, mark the interview task blocked awaiting the browser answer, and yield. On its wake, resume and call `WaitForAnswer` again to obtain the archived answer. A monitor exit or save acknowledgement is not itself an answer; do not poll with repeated model turns.
4. Use the validated returned answer or read the exact returned `responsePath`. Preserve `mode`, all `selectedIds`/`selectedLabels`, `submissionType`, and the user's `response`. Copy that normalized answer unchanged into the owner's `response-B<n>.json` as skill-owned evidence, record its original response path, and update the local decision tree before the next question. The extension does not write this skill evidence file on Submit.
5. Record every selected choice in displayed option order. Comments-only feedback has empty arrays and nonblank `response`; it keeps the branch open for rework. Resolve conflicting selections before closing the branch. There are no scalar-answer fallbacks.

Free-form feedback is always available. Clear selection removes choices without erasing comments. Choice-mode submission needs a choice or nonblank comments; review needs nonblank comments.

Runtime question state is internal to pi-decisions and independent of skill artifact directories. After reload/reopening, recheck/re-arm supported pending questions; classic monitors do not survive shutdown/session switching. Questions saved in a removed format must be resubmitted with fresh IDs; do not migrate or delete historical files implicitly. Keep Pi running while waiting; stopped machines cannot be woken.

Before any explicitly authorized hosted-site deletion, preserve the answer and required visuals independently. The extension owns local process/watcher cleanup; never run a separate server or stop unrelated monitors.

## DAG and parallel branch ownership

Before opening the first question, the parent creates `dag.md` beside `decision-tree.md`. Use Work/Todo tracking when available: one Todo per top-level decision branch and one integration Todo per level. Record **Branch ID, Todo ID, outcome/closure criteria, dependency IDs, level, owner, owner task directory/artifact boundary, status, and evidence paths**. Without Todo tools, use stable local IDs; never invent Todo IDs. Validate dependencies and cycles before dispatch. The parent alone edits the shared DAG, aggregate tree, contract, and parent Todos; children write only their assigned interview artifacts.

1. Group independent ready branches into levels. A branch is ready only when required decisions are verified resolved and the previous level's integration is complete. A deferred dependency does not satisfy a required decision: explicitly re-scope or defer its dependents. Shared choices must be dependencies, not parallel guesses.
2. Dispatch independent branches concurrently through the Herdr policy below. Delegate substantial follow-up trees; keep trivial clarifications with the parent without serializing independent owners. Each owner has authority to open its own visible browser pages and ask the user directly. Concurrent browser tabs/windows are intentional; no shared-browser bottleneck or extra parent approval for each follow-up.
3. Every interviewer, including the parent handling a trivial branch, works in one canonical owner task directory. The parent uses the grill-me owner directory; a delegated owner uses its assignment's exact `parentTaskDir` plus its own `<sessionId>/<workId>/<taskId>` triple. Give every owner a short **label**, such as `b1`, used only in page titles and qualified IDs; a label never selects a directory. Each owner uses its own task directory and pinned question records; pi-decisions handles the selected delivery backend and watcher lifecycle. Keep branch IDs `B<n>` local and use `<owner-label>:B<n>` in the shared DAG/tree. Use safe session-unique tool question IDs such as `<owner-label>-B1`; question storage is not scoped by task directory. Show the owner/decision and level in question titles.
4. The owner runs the existing browser workflow, records every `response-B<n>.json`, then follows its answer-driven children sequentially within that owner (for example A → A1 → A2). Keep local IDs stable and record parent-child links in its local tree. No new agents or edits to other owners' files. If a child needs another owner's decision, return an explicit dependency/blocker rather than guessing or waiting on the sibling.
5. An owner returns only when its entire assigned tree is resolved or explicitly deferred, or a real blocker prevents closure. Return decisions/rationale, child links, acceptance criteria, its canonical task directory and session/Work/Task IDs, original response/evidence paths, user-approved deferred reasons/revisit conditions, blockers/cross-branch dependencies, and resource cleanup status. Comments-only rejection requires rework, not resolution. A timeout or agent completion is not a user answer.
6. The parent reads each complete result and original artifacts before marking its DAG row/Todo completed. Record resolved/deferred disposition separately from task completion; deferred decisions are not implementation requirements. Mark partial/failed owners blocked and keep the next level pending. Merge child branches into the aggregate tree with qualified IDs and original artifact paths.
7. Reconcile the whole level for conflicting decisions, overlapping scope and missing evidence. Conflicts become explicit follow-up branches; do not silently choose an agent's answer. Reopen affected owners/dependents when a decision changes. Update DAG dependencies and Todos together, then finish the level's integration Todo before opening the next level.
8. Continue automatically until every branch is verified resolved or explicitly deferred and final integration is complete. Hand off the aggregate tree and DAG plus every owner task directory's original evidence paths, not just a summary.

### Branch-owner assignment

When invoked as an assigned branch owner, skip parent intake, shared DAG creation, dispatch and aggregate handoff. Run only your local question/follow-up loop and return its result; do not recursively invoke the full conductor workflow.

For human interviews, choose a prompt-and-wait deadline long enough for the browser waits and follow-ups; the 15-minute runtime minimum is not a completion budget. A deadline never resolves a branch: preserve pending evidence and resume it explicitly.

Include the decision scope, level/dependencies, inherited verified decisions, closure criteria, feature name, owner label, real session/Work/Task IDs, the exact parent task directory, owned/forbidden paths, helper interfaces and browser authority in the prompt. Require the owner to create its own tracking and canonical nested task directory, and authorize follow-up questions, local tree/response writes, and its own pi-decisions question/watcher lifecycle, while keeping production code read-only. State that it must close only resources it created, preserve evidence, not update parent tracking, not spawn agents, and return the complete branch result above. Evidence-only agents remain read-only and do not interview the user.

## Independent-agent policy

Apply this policy whenever the workflow uses an explorer, researcher, critic, reviewer, or any other independent agent. These are prompt responsibilities, not repository-defined skill or role names.

Before launching subagents, read and follow the globally installed `model-routing-policy` skill for model, thinking level, and Fast settings. Keep routing defaults only in that skill. Check required input modalities before launch; report incompatible models rather than silently substituting. If the default Fast setting is unavailable, omit `--fast`; if the user explicitly requested Fast, report that it is unavailable. Pass provider, model, and thinking explicitly to Pi, and verify the launch and requested Fast status before prompting. Keep every independent agent recursion-disabled.

Core-hosted interactive Pi agents are the only runtime. Read and follow global herdr before control commands. Use hc for lifecycle and herdr-app for display; require a verified real HC_TERMINAL_ID parent, not HERDR_ENV or the retired herdr TUI CLI. A valid Core session must not be rejected because old TUI variables are absent. Prefer the updated Agent tools. Give every agent a dedicated visible tab in the parent's real app space, named exactly with its parent delegated Task ID, never a hidden child or a shared split. Read actual terminalId/tabId handles from results; task labels may repeat across sessions. Pass explicit model-routing-policy provider/model/thinking and supported optional fast settings, verify native Pi input readiness and the tab mapping, then confirm a continuous MonitorCreate hcTerminalId subscription is ready before sending assignments. Retain that monitor across follow-ups and dispatch ready independent branches concurrently. Give productive interview work at least 15 minutes; a deadline is not branch closure. Inspect real output and owned artifacts before accepting results. On partial startup, ambiguous delivery, lost output or monitoring failure, diagnose with actual handles and return a precise blocker without blindly relaunching or bypassing consent. Retry only after a verified correction and without contradicting model choices. Close only owned resources after results and follow-ups are collected. Unavailable Core/app/tools/monitoring is a tooling blocker, not permission to silently collapse required parallel branches.

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

Capture the plan, scope, constraints, and success criteria. Create `<taskDir>/dag.md` and `decision-tree.md` from [references/decision-tree.md](references/decision-tree.md) before opening questions.

### 1. Seed the tree

Break the plan into branches such as product scope, user model, capability boundary, data flow, failure modes, rollout, and ownership. Record dependencies, levels, closure criteria and owner boundaries in the DAG; run the smallest useful grounding pass before dispatch.

### 2. Interview loop

1. Select the current ready level and dispatch independent owners concurrently.
2. Each owner grounds facts, adds useful concept visuals, and runs its own browser question/Submit/wait loop.
3. Each owner records answers, follows answer-driven children, and returns a closed tree or explicit blocker.
4. The parent verifies original responses, merges branch results, and resolves contradictions.
5. Complete the level integration gate, then continue automatically to the next ready level until the whole DAG is resolved or explicitly deferred.

### 3. Visual handoff

When plan branches are resolved and the feature has UI decisions, start the globally installed `ui-ux-grill-me` skill with the same conceptual choices and link the parent task directory, its DAG and aggregate decision tree. Do not re-ask decisions already recorded. Carry forward the resolved branch IDs, user rationale, constraints, and acceptance criteria so the visual interview tests the agreed product direction instead of inventing a new one. Hand off exact paths; never ask the visual owner to reconstruct them from a feature name or label.

The handoff chain is:

global `grill-me` plan decisions → global `ui-ux-grill-me` visual contract when needed → global `implement` production changes → the repository's visual and behavior verification.

### 4. Closeout

Record shared understanding, resolved decisions, deferred decisions, evidence, remaining risks, and the automatic handoff below. This closeout is not a stopping point: after cleanup, continue into the next skill in the same turn unless explicitly limited to planning or genuinely blocked.

Verify that every accepted answer is archived in its owning task directory and every pending interview is resolved, deferred, or explicitly blocked. pi-decisions owns local resource cleanup and watcher identity; stop only resources belonging to that owner. Keep hosted evidence until it has been archived and deletion is explicitly authorized. Do not run separate server cleanup helpers against a pi-decisions-owned process.

## Loop limits

- One open browser question per owner, not globally; independent owner browsers run concurrently.
- No artificial question cap — interview until every branch of the design tree is resolved or explicitly deferred; nothing left silently assumed.

If the returned interview URL or answer watcher cannot run, preserve pending artifacts and block the interview with the concrete error. Do not silently switch delivery backends.

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

- <taskDir>/dag.md
- <taskDir>/decision-tree.md
- each owner task directory's tree and response-*.json, linked by qualified branch ID and exact path

## Handoff status

- next global skill started automatically: ui-ux-grill-me / implement
- or explicit planning-only/stop instruction or unresolved blocker preventing handoff
```

## Handoff

After every branch is verified resolved or explicitly deferred and final integration is complete, list every branch under Resolved branches or Deferred. Exit grill-me and automatically start the next global skill in the same turn without requesting additional approval, unless the user explicitly requested planning only or stopped the workflow. If no resolved implementation scope remains, report that outcome rather than inventing work. Hand off the feature name, parent and owner task directory paths and labels, DAG, aggregate decision-tree path, qualified-ID-to-original-evidence paths, every resolved branch ID with its acceptance criteria, and every deferred branch ID unchanged to the globally installed `implement` skill. If the plan contains UI decisions, hand off the same parent task directory, DAG, aggregate decision tree and original owner artifact paths to the globally installed `ui-ux-grill-me` skill; do not ask `implement` to infer direction from prose. Implementation must verify every resolved branch before Agent Review starts; deferred branches are not requirements. Give reviewers the decision tree and current implementation evidence directly, then run the repository's required quality, visual, behavior, and review checks before commit or pull request.
