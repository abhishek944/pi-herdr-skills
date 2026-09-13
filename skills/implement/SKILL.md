---
name: implement
description: "Repository-agnostic recursive implementation conductor: maintain an atomic task/todo tree, delegate bounded outcomes through Herdr-hosted Pi agents when useful, verify combined behavior, and apply independent review only when complexity, risk, breadth, uncertainty, or an explicit user request justifies it. Use when the user asks to implement or fix something."
compatibility: Requires a repository checkout, standard file and shell tools, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry. Continue correcting and retrying while each failure is clearly non-mutating and provides actionable validation feedback; do not stop merely because an earlier correction revealed another issue. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, becomes ambiguous, or cannot be corrected from the documented interface. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless project instructions say otherwise.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# Implement

Apply production changes through the repository's real ownership boundaries. Maintain one resumable recursive task tree, delegate only independent outcomes, verify the combined behavior, and preserve unrelated work.

## Core rules

- Read all applicable repository instructions and architecture or workflow documentation.
- Discover the actual languages, package manager, layout, quality commands, testing policy, artifact rules, and release rules. Do not assume them.
- Preserve unrelated user changes and existing staged work.
- Do not commit, push, publish, or deploy unless the user's latest request explicitly asks.
- Follow the project's testing policy. Run established automated checks and required visual comparisons, but leave live interactive end-to-end product testing to the user unless their latest request explicitly asks an agent to run it. Prepare a clear manual test handoff and never claim that a user-owned test passed.
- Do not hard-code answers, phrase-match requests, bypass an owning boundary, or add one-off behavior for one example.
- Treat resolved `/grill-me` and `/ui-ux-grill-me` outputs as implementation contracts. Discover applicable sessions before editing, implement every resolved decision, and never treat deferred decisions as requirements.
- Use the globally installed `agent-review` skill only when the review-requirement gate finds meaningful complexity, risk, breadth, or uncertainty, or when the user explicitly requests independent review. Keep its human-readable reports as review history.
- Reference only globally installed skills from this workflow. Repository-specific behavior comes from instructions and documentation.

## Review-requirement gate

Classify the integrated change from repository evidence before creating reviewer runtime resources:

- **simple** — straightforward, low-risk work whose behavior and rollback are easy to understand. It may include a localized user-visible change when it follows an established pattern, stays within one owning boundary, introduces no API/data/workflow/product contract, has few interacting states, and is confidently covered by direct inspection plus normal checks;
- **feature** — a substantial behavior or product-capability change whose combined behavior is not obvious from local inspection, such as a new workflow, broad UI behavior, or a changed API, data model, or product contract;
- **complicated** — work that crosses meaningful owning boundaries or involves architecture, authorization, security, privacy, destructive actions, migrations, concurrency, compatibility-sensitive behavior, resolved visual contracts, several interacting failure modes, or material implementation uncertainty.

Feature and complicated changes require the full independent `agent-review` workflow and use `--review-complexity complicated`. Simple changes do not launch reviewers. Record `review_requirement` with `classification: simple`, `source: automatic`, `required: false`, and a concrete evidence-based reason; set `review_verdict` and `review_execution` to `not-required`, keep reviewer waves and reports empty, and still run applicable project checks plus direct coordinator inspection.

Use judgment proportionately. A user-visible change, several touched files, or a large diff is a signal to inspect—not an automatic reason to review. Skip independent review when the coordinator is confident the change is straightforward and the evidence above supports that decision. Require review when interactions, breadth, risk, uncertainty, or higher-reasoning demands make direct inspection insufficient. Never classify from request wording alone or a desire to save time. When genuinely uncertain after inspection, classify as complicated. An explicit user request for independent review always runs it; record `source: user-request`, set `required: true`, and use `--review-complexity simple` only when the inspected change meets the simple criteria.

## State and todos come first

Every implementation, including small direct work, uses one canonical state tree. The repository must ignore `var/` so state and evidence cannot contaminate the product diff:

```text
var/<feature-name>/implement/state.json
```

Initialize it before repository investigation or editing:

```bash
bash <skill-root>/scripts/init-state.sh <feature-name>
```

Resume only the same version 4 run after reading and validating its state:

```bash
IMPLEMENT_COORDINATOR_LEASE_ID='<lease-id>' \
bash <skill-root>/scripts/init-state.sh <feature-name> --resume
```

Initialization captures the initial dirty-worktree snapshot, binds the coordinator to the current Pi session, and prints the coordinator lease ID and instance ID. Set `IMPLEMENT_COORDINATOR_LEASE_ID` for root updates. An expired lease takeover requires a fresh lease ID and creates a fresh coordinator instance, fencing the old coordinator. A persisted reconciliation gate blocks normal work until live slots and resources are checked against Herdr state.

Immediately record the user goal, root contract, and root todos through `scripts/state-store.py`. Use the exact bootstrap sequence in [references/state-schema.md](references/state-schema.md); do not invent event names. The first todos normally cover reading instructions, tracing current behavior, planning, implementation, automated checks, visual verification when applicable, a user test handoff, integration, and final review. Add agent-run live behavior verification only when the user's latest request explicitly asks for it. Keep todos current as work proceeds; do not reconstruct them at the end.

If an event name is uncertain or rejected without changing state, run the helper's documented `events` command, correct the event from that output, and retry. Continue correcting documented usage or validation errors while each rejection is clearly non-mutating and actionable. Never inspect the helper source during ordinary implementation. A failed event application is non-mutating because the helper writes state only after the event validates successfully; credential, authorization, malformed-state, and ambiguous failures still stop immediately.

`state.json` is the only mutable state authority for the run and every descendant. Large reports, recordings, transcripts, and patches live under the same run folder and are referenced from the JSON. Agents must never edit the JSON directly; use the state helper so updates are locked, coordinator-leased for root operations, task-scoped, validated, revisioned, and atomic. Descendants act through their immutable task IDs, parent-owned contracts, and recorded Pi session identities. The state helper rejects a task ID used from a different Pi session.

Read [references/state-schema.md](references/state-schema.md) before planning or updating state.

## Logical decomposition

Divide work by independent responsibility and outcome, not by existing folders. New files and folders must remain possible.

Each task has:

- a stable task ID and explicit parent/root lineage;
- one outcome and acceptance criteria;
- boundaries, inputs, and expected result;
- dependencies, normally none;
- a task class and recorded model decision;
- todos, children, runtime state, result, and evidence;
- `allow_subagents`, which permits but never requires further delegation.

Do not invent children merely to create parallelism. Keep cohesive work in the current task. Delegate when a separate context, specialist model, or parallel independent outcome materially improves quality or speed.

A parent may have at most six immediate children. Root-wide defaults also limit depth to two levels below the root, total tasks to eighteen, and active descendant agents to six. Automatic fallback has no fixed attempt-count ceiling; the resolver's cumulative exclusions and routing-zone exhaustion determine when no candidate remains. The same logical task keeps an append-only attempt ledger, but every attempt uses a fresh intent, pane, Pi session, model resolution, and launch verification. The state helper enforces the topology and concurrency limits atomically.

Sibling outcomes should almost always be independent. If a hidden dependency or overlapping behavior appears, record it and let the parent serialize, integrate, or replan the work. Never coordinate silently through concurrent edits.

## Recursive delegation contract

Every child agent:

1. is assigned a unique task ID;
2. is launched with the globally installed `implement` skill available;
3. receives the feature name, canonical state location, task ID, and immutable logical contract;
4. creates its own todos before investigation, editing, or delegation;
5. reads the Pi-global model catalog and its recorded model selection;
6. decides whether its work is a leaf;
7. uses `allow_subagents: false` for small or cohesive leaf work;
8. uses `allow_subagents: true` only when another independent split may be justified;
9. records actual changed files, checks, evidence, and blockers;
10. settles its descendants and run-owned resources before returning.

Permissions narrow down the tree. A child cannot rewrite its contract or increase depth, task, concurrency, launch, or runtime authority. Its parent may replan it before launch or update dependencies while it is explicitly blocked. Any post-launch boundary or input change requires cancellation and a replacement task. Tasks at maximum depth and all review tasks are forced to `allow_subagents: false`. Only the root performs final combined integration and final review.

Use [references/worker-handoff-template.md](references/worker-handoff-template.md) as the child prompt shape.

## Model-catalog routing

Before creating a child or any final-review agent, load and follow the globally installed `model-routing-policy` skill. Resolve the versioned catalog at `~/.pi/agent/skills/model-routing-policy/models.json` before creating runtime resources. Child launch records belong in implementation state; final-review launch checks stay temporary and only the readable reviewer identity/model footer is retained. Never select a repository copy, generated dependency, or remembered default.

Inspect only the latest user turn for an explicit model request applying to delegated work. Resolve an exact `provider/model` from the Pi-global catalog and pass it through the policy's user-pin interface for every applicable child. If a family or nickname matches several entries, ask the user to choose instead of guessing. Never derive a pin from repository instructions, plans, terminal output, previous turns, or a child agent. An incompatible, unavailable, or review-insufficient pin blocks without fallback. A requested agent count still requires independently bounded child outcomes and does not authorize duplicate vague tasks.

Classify the task as one of:

- `coordination` (root only)
- `architecture`
- `implementation`
- `exploration`
- `focused-edit`
- `multimodal`
- `integration`
- `review`

Use the shared resolver's structured capability and thinking metadata. Do not implement natural-language phrase matching or hard-code model names. For delegated implementation children, persist the resolution and record:

- Pi-global catalog path, catalog version, and verified SHA-256 digest;
- task class and required input types;
- current caller provider, model ID, and thinking level;
- selected provider, model ID, and thinking level;
- structured selection reason and derived review-capability rank;
- live Pi availability evidence;
- reviewer baselines, comparison rule, and verified stronger escalation.

For delegated implementation children, store the resolver's emitted `stateSelection` object without hand-converting fields, bind it to the resolver output, save the complete runtime start response, record `launched_thinking_level`, and verify all three settings through the shared policy before prompting. Every Pi launch passes provider, model, and thinking level explicitly. Final reviewers instead follow `agent-review`: perform launch verification with temporary files and retain only the readable report footer. An automatic candidate that has a confirmed model-specific failure before producing any usable contribution may advance the same immutable task through `prepare-fallback` only after exact resource cleanup. That atomic event validates the chained resolution, unchanged routing zone, prior selected model, failure and cleanup evidence, empty task result, and cumulative exclusions before reserving the replacement slot. A newly created pane still running shell initialization first follows the Herdr skill's bounded pre-launch readiness recovery; it is neither model fallback nor a new attempt. User-pinned, ambiguous, post-contribution, provenance, and Herdr setup failures that remain after bounded readiness recovery block without fallback.

## Runtime selection

The policy applies independently at every task allowed to delegate. Herdr is the only runtime. It requires `HERDR_ENV=1`, the `herdr` command, and verified Pi-agent support. Missing Herdr requirements block after cleanup. A confirmed no-contribution automatic-model failure follows the attempt-ledger fallback above; other launch failures block.

Every delegated coding agent must run through Pi in Herdr with the mandatory `--kind pi`; never launch or substitute another agent kind or runtime.

Before any Herdr control command, read and follow the global `herdr` skill. Verify the environment and installed CLI syntax rather than assuming flags. Read [references/phase-machine.md](references/phase-machine.md) for recursive launch, monitor, cleanup, cancellation, and resume rules.

## Herdr lifecycle for recursive waves

For every immediate child wave, the delegating task:

1. atomically adds ready children and reserves root-wide agent slots;
2. records the caller's repository directory and Herdr context;
3. partitions ordered immediate children into consecutive groups of at most four; a six-child wave therefore uses two tabs with four and two panes, and no implementation tab may ever contain a fifth pane;
4. for each group, records distinct, single-use tab and first-child root-pane intents before creating that group's dedicated unfocused tab, each with its own output artifact; saves the full response for the tab intent, copies that same response to the root-pane intent artifact, and binds the returned tab and root-pane IDs separately;
5. treats each returned root pane as that group's first child pane and never leaves an extra coordinator shell in any child tab; creates the other group panes in the Herdr skill's fixed grid order—root split right for child two, root split down for child three, then split child two down for child four—preserving `--no-focus` plus the repository directory;
6. after every root or split pane ID across all groups is bound, uses `herdr pane rename` to assign a distinct name describing that child's outcome and records the name with the resource; pane names are mandatory, four-child groups must be 2x2, and cleanup tracks every owned tab separately;
7. uses each pane intent's state-helper-generated RFC 3339 creation time as the readiness anchor—never an agent-authored timestamp or shell `date` result—passes it to the Herdr classifier, preserves the classifier's canonical deadline for every recheck, records every process snapshot and classification through the typed `record-pane-readiness` state event, allows sequential startup helpers to turn over while the exact pane and shell stay stable, applies the Herdr skill's bounded five-minute gate without restarting it after resume, treats the deadline as the readiness-attainment bound rather than an expiry on a ready proof, makes the complete batch ready before starting any child, and fails closed without retry when `agent start` returns `agent_pane_busy` for the certified pane;
8. starts every child concurrently in its named pane as a Pi agent using `--kind pi`, passing its recorded provider/model/thinking selection explicitly through Pi with a unique runtime name and bounded deadline;
9. records immutable agent-session provenance, verifies the complete child launch against its recorded resolution, and records the child launch verification before moving the runtime to working;
10. after all Pi agents start and every verification is preserved, launches one `herdr agent prompt ... --wait` process per child concurrently with its complete handoff; while those processes are still running, observes each agent enter working state and immediately records dispatch through the dedicated write-once productive-prompt event;
11. only after dispatch is durably recorded, joins the concurrent prompt-and-wait processes with deadlines of at least `900000` milliseconds (15 minutes), while preserving the runtime schema's three-hour maximum; overdue work follows timeout cancellation rather than successful settlement;
12. stores each complete child handoff under the run outputs folder and records its digest;
13. records observed runtime settlement, then atomically accepts successful blocker-free child tasks with parent verification evidence, which marks them done and releases their slots;
14. closes only exact recorded resources, saving and digesting each close response; preserved resources keep the task blocked until verified closure.

A child may create a separate tab for its descendants, but it must never control or close the tab containing itself. The resource creator owns cleanup. The root may reclaim descendant resources only during cancellation or recovery and only from exact recorded IDs.

If only part of a launch or prompt batch succeeds, never duplicate accepted work. Monitor productive children. Replace only roles with confirmed no-contribution automatic-model failures, keeping their contracts unchanged and exclusions cumulative; block the other failed roles after cleanup. `unknown`, missing output after possible work, and approval prompts are not safe fallback evidence or completion.

Cancellation is two-phase. First request deepest-first cancellation while slots remain occupied. Confirm each runtime stopped, collect partial output, and close or preserve exact resources. Only then finalize cancellation and release slots. A cancellation request is never treated as settled work.

## Planning

After state initialization and root todo creation:

1. restate the requested outcome and acceptance criteria in root state;
2. read instructions and matching architecture or flow documentation;
3. discover `var/<feature-name>/grill-me/*/decision-tree.md` and `var/<feature-name>/ui-ux-grill-me/*/visual-decision-tree.md`; bind a single candidate of each kind, require explicit user selection when several candidates exist, and record an explicit no-contract result when none exist;
4. trace current behavior, callers, resolved Grill Me decisions, selected UI/UX branches, tests, and owning boundaries;
5. state the invariant that must hold for equivalent requests;
6. identify risks, edge cases, compatibility, migration, and rollback concerns;
7. choose direct or recursive execution honestly;
8. move the root task into working state after its todos and plan exist;
9. create logical child contracts only for independent outcomes and include the bound Grill Me and UI/UX contract artifacts unchanged in every applicable handoff;
10. resolve and record model choices before launch;
11. validate the task tree:

```bash
bash <skill-root>/scripts/validate-plan.sh <feature-name>
```

Revalidate whenever contracts, dependencies, permissions, or limits change.

## Direct execution

1. Keep the root task's todos current.
2. Implement only the requested scope at the owning boundary.
3. Follow existing architecture unless the user approved a deliberate change.
4. Run applicable formatting, lint, type, build, and test commands.
5. Run required visual comparisons and non-interactive behavior checks. If the latest request explicitly asks for agent-run live end-to-end testing, run it; otherwise prepare the user's live-test checklist and record that verification as user-owned without treating it as an implementation blocker.
6. Record actual changed files, checks, evidence, user-test handoff, and blockers in root state.
7. Continue to integration and the review-requirement gate.

## Descendant execution

A child follows this same skill rather than a reduced worker-only workflow. It owns one task and may recursively delegate only when its contract allows it and root-wide permits are available.

The child must inspect real code and project rules, maintain todos, implement the general solution, verify its subtree, collect every child result, and report actual changes before returning. The parent observes runtime settlement and uses `accept-task` to atomically mark the child done and release its slot. A child summary is not acceptance evidence; its parent reads the combined changes and reruns affected checks.

When no active slot is available, finish existing children before launching more. If capacity cannot be restored, block the task.

## Integration and changed-file collisions

Tasks are not assigned paths in advance. Every task records actual changed files when it settles.

After a child wave, the parent:

1. reads every child result and the real combined changes;
2. checks whether siblings touched the same files or implemented conflicting behavior;
3. marks collisions unresolved rather than accepting last-writer-wins behavior;
4. integrates directly or creates a dedicated integration task;
5. reruns affected checks against the combined subtree.

The root records the surviving integrated files and compares them with the worktree delta from the initialization snapshot, including file mode changes. Child file lists remain historical evidence, so reverted or cancelled edits do not pollute the final list. Every sibling file overlap requires a collision entry, and every collision stays open until the integration decision and rerun evidence are recorded. Cancelled work requires a reason and parent disposition proving how its outcome was replaced, absorbed, or intentionally removed. Final acceptance depends on the integrated live change, not independent child reports.

## Verification

Discover verification from repository evidence in this order:

1. instructions and contribution guidance;
2. package or build scripts;
3. CI configuration;
4. nearby tests and established end-to-end tools;
5. manual behavior checks for uncovered paths.

Cover the happy path, expected failure, important edge case, compatibility or migration path, and relevant authorization, privacy, or destructive-action boundaries with established automated checks, safe fixtures, and required visual comparisons. Map every resolved Grill Me decision to current passing functionality evidence. Map every resolved UI/UX branch to exact route, viewport, fixture, interaction state, selected screenshot, implemented screenshot, selection rationale and modifications, and a passing comparison report. Live interactive end-to-end checks in the real supported host are user-owned unless the latest request explicitly asks an agent to run them. In the normal user-owned case, provide exact manual steps and expected results, record verification as awaiting the user, and do not treat that pending handoff as an implementation blocker or claim it passed. If an explicitly requested agent-run test lacks required authentication, fixtures, hardware, credentials, or runtime, record the exact blocker instead of claiming success.

For resolved visual contracts, read [references/visual-contract.md](references/visual-contract.md), reproduce the exact selected state, compare the live result directly, and keep mismatches in rework. Visual contracts make the change complicated and require independent review. Give reviewers the selected decision tree and current visual evidence directly.

## Final integration and proportionate review

Only the root performs final integration and decides whether independent review is required:

1. ensure every implementation descendant is done or cancelled with evidence;
2. ensure every active slot and run-owned runtime resource is settled;
3. inspect the combined change and adjacent callers;
4. resolve all changed-file and behavioral collisions;
5. rerun affected project checks and record short, readable results;
6. record visual verification and the user-owned live-test handoff separately; include an agent-run real-behavior verdict only when explicitly requested;
7. classify the integrated change as `simple`, `complicated`, or `feature` using the review-requirement gate;
8. directly inspect automatic simple changes and record review as not required;
9. for required review, run three fresh read-only reviewers, record only each owned review tab's ID and open/closed cleanup status in state, and save the correctness, architecture, regression, and summary reports;
10. verify and fix accepted findings, then rerun affected checks and a fresh complete review wave whenever code changed;
11. validate final state:

```bash
bash <skill-root>/scripts/validate-integration-review.sh <feature-name>
```

Apply `complete-run` after validation. Completion repeats the live changed-file, report, task, collision, and resource checks while holding the state lock. A user-owned live test remains recorded as awaiting user verification, not passed. Report independent review only when it was required and completed.

## Final report

Report the practical outcome first, then include:

- complete or blocked;
- direct or recursively delegated execution;
- provider, model, and thinking level selected for delegated task classes and reviewer escalation;
- main changes and actual changed files;
- project checks, visual verification, and the user-owned live-test handoff; include live behavior results only when the user supplied them or explicitly requested agent-run testing;
- final review result;
- unresolved blockers or risks;
- confirmation that runtime resources settled;
- confirmation that no commit, push, publish, or deploy occurred unless explicitly requested;
- the next useful step.
