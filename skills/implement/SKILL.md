---
name: implement
description: "Repository-agnostic recursive implementation conductor: maintain an atomic task/todo tree, route each child through the Pi-global model catalog, delegate bounded independent outcomes through Herdr-hosted Pi agents, verify the combined behavior, and close with independent review. Use when the user asks to implement or fix something."
compatibility: Requires a repository checkout, standard file and shell tools, Herdr, and Herdr-hosted Pi agents.
---

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
- Treat resolved `/grill-me` and `/ui-ux-grill-me` outputs as implementation contracts.
- Use the globally installed `agent-review` skill for every final closeout.
- Reference only globally installed skills from this workflow. Repository-specific behavior comes from instructions and documentation.

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
IMPLEMENT_TASK_CAPABILITY='<owner-token>' \
IMPLEMENT_COORDINATOR_LEASE_ID='<lease-id>' \
bash <skill-root>/scripts/init-state.sh <feature-name> --resume
```

Initialization captures the initial dirty-worktree snapshot and prints the root owner token, coordinator lease ID, and coordinator instance ID. Keep credentials out of state, artifacts, logs, process arguments, and user-facing replies. Set the token and lease as `IMPLEMENT_TASK_CAPABILITY` and `IMPLEMENT_COORDINATOR_LEASE_ID` for root updates. An expired lease takeover requires a fresh lease ID and creates a fresh coordinator instance, fencing the old coordinator. A persisted reconciliation gate blocks normal work until live slots and resources are checked against Herdr state.

Immediately record the user goal and create root todos through `scripts/state-store.py`. The first todos normally cover reading instructions, tracing current behavior, planning, implementation, automated checks, visual verification when applicable, a user test handoff, integration, and final review. Add agent-run live behavior verification only when the user's latest request explicitly asks for it. Keep todos current as work proceeds; do not reconstruct them at the end.

`state.json` is the only mutable state authority for the run and every descendant. Large reports, recordings, transcripts, and patches live under the same run folder and are referenced from the JSON. Agents must never edit the JSON directly; use the state helper so updates are locked, capability-authenticated, coordinator-leased, validated, revisioned, and atomic. State stores only capability hashes; raw task capabilities are runtime credentials.

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

A parent may have at most six immediate children. Root-wide defaults also limit depth to two levels below the root, total tasks to eighteen, active descendant agents to six, and launch attempts to one per task. The state helper enforces these limits atomically.

Sibling outcomes should almost always be independent. If a hidden dependency or overlapping behavior appears, record it and let the parent serialize, integrate, or replan the work. Never coordinate silently through concurrent edits.

## Recursive delegation contract

Every child agent:

1. is assigned a unique task ID;
2. is launched with the globally installed `implement` skill available;
3. receives the feature name, canonical state location, task ID, raw task capability, and immutable logical contract;
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

Before creating a child or any final-review agent, load and follow the globally installed `model-routing-policy` skill. Resolve the versioned catalog at `~/.pi/agent/skills/model-routing-policy/models.json` before creating runtime resources. Never select a repository copy, generated dependency, or remembered default.

Classify the task as one of:

- `coordination` (root only)
- `architecture`
- `implementation`
- `exploration`
- `focused-edit`
- `multimodal`
- `integration`
- `review`

Use the shared resolver's structured capability and thinking metadata. Do not implement natural-language phrase matching or hard-code model names. Persist its resolution artifact and record:

- Pi-global catalog path, catalog version, and verified SHA-256 digest;
- task class and required input types;
- current caller provider, model ID, and thinking level;
- selected provider, model ID, and thinking level;
- structured selection reason and derived review-capability rank;
- live Pi availability evidence;
- reviewer baselines, comparison rule, and verified stronger escalation.

Store the resolver's emitted `stateSelection` object without hand-converting fields, and bind it to the resolver artifact path and pre-launch digest. Every Pi launch passes provider, model, and thinking level explicitly. Save the complete runtime start response, record `launched_thinking_level`, and verify all three settings through the shared policy before prompting. If resolution or launch fails, clean up owned resources and stop with a blocker. Do not retry or select another model or runtime.

## Runtime selection

The policy applies independently at every task allowed to delegate. Herdr is the only runtime. It requires `HERDR_ENV=1`, the `herdr` command, and verified Pi-agent support. If any requirement is unavailable or a launch fails, clean up owned resources and stop with a blocker.

Every delegated coding agent must run through Pi in Herdr with the mandatory `--kind pi`; never launch or substitute another agent kind or runtime.

Before any Herdr control command, read and follow the global `herdr` skill. Verify the environment and installed CLI syntax rather than assuming flags. Read [references/phase-machine.md](references/phase-machine.md) for recursive launch, monitor, cleanup, cancellation, and resume rules.

## Herdr lifecycle for recursive waves

For every immediate child wave, the delegating task:

1. atomically adds ready children and reserves root-wide agent slots;
2. records the caller's repository directory and Herdr context;
3. records distinct, single-use tab and first-child root-pane intents before creating the tab, each with its own output artifact; injects only the first child's capability through `herdr tab create --env`, saves the full response for the tab intent, copies that same response to the root-pane intent artifact, and binds the returned tab and root-pane IDs separately;
4. treats the returned root pane as the first child's pane and never leaves an extra coordinator shell in the child tab;
5. for each remaining child only, records a pane intent and creates one split pane, injecting only that child's raw capability, until the tab has exactly one pane per child;
6. after every root or split pane ID is bound, uses `herdr pane rename` to assign a distinct name describing that child's outcome and records the name with the resource; pane names are mandatory;
7. starts every child concurrently in its named pane as a Pi agent using `--kind pi`, passing its recorded provider/model/thinking selection explicitly through Pi with a unique runtime name and bounded deadline;
8. records immutable agent-session provenance, verifies the complete launch against the preserved resolution digest, and records the digest-bound verification artifact before moving the runtime to working;
9. after all Pi agents start and every verification is preserved, launches one `herdr agent prompt ... --wait` process per child concurrently with its complete handoff; while those processes are still running, observes each agent enter working state and immediately records dispatch through the dedicated write-once productive-prompt event;
10. only after dispatch is durably recorded, joins the concurrent prompt-and-wait processes with bounded deadlines; overdue work follows timeout cancellation rather than successful settlement;
11. stores each complete child handoff under the run outputs folder and records its digest;
12. records observed runtime settlement, then atomically accepts successful blocker-free child tasks with parent verification evidence, which marks them done and releases their slots;
13. closes only exact recorded resources, saving and digesting each close response; preserved resources keep the task blocked until verified closure.

A child may create a separate tab for its descendants, but it must never control or close the tab containing itself. The resource creator owns cleanup. The root may reclaim descendant resources only during cancellation or recovery and only from exact recorded IDs.

If only part of a launch or prompt batch succeeds, never duplicate accepted work. Monitor productive children and block the failed roles after cleanup. `unknown`, missing output, and approval prompts are not completion.

Cancellation is two-phase. First request deepest-first cancellation while slots remain occupied. Confirm each runtime stopped, collect partial output, and close or preserve exact resources. Only then finalize cancellation and release slots. A cancellation request is never treated as settled work.

## Planning

After state initialization and root todo creation:

1. restate the requested outcome and acceptance criteria in root state;
2. read instructions and matching architecture or flow documentation;
3. trace current behavior, callers, contracts, tests, and owning boundaries;
4. state the invariant that must hold for equivalent requests;
5. identify risks, edge cases, compatibility, migration, and rollback concerns;
6. choose direct or recursive execution honestly;
7. move the root task into working state after its todos and plan exist;
8. create logical child contracts only for independent outcomes;
9. resolve and record model choices before launch;
10. validate the task tree:

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
7. Continue to integration and review.

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

Cover the happy path, expected failure, important edge case, compatibility or migration path, and relevant authorization, privacy, or destructive-action boundaries with established automated checks, safe fixtures, and required visual comparisons. Live interactive end-to-end checks in the real supported host are user-owned unless the latest request explicitly asks an agent to run them. In the normal user-owned case, provide exact manual steps and expected results, record verification as awaiting the user, and do not treat that pending handoff as an implementation blocker or claim it passed. If an explicitly requested agent-run test lacks required authentication, fixtures, hardware, credentials, or runtime, record the exact blocker instead of claiming success.

For resolved visual contracts, read [references/visual-contract.md](references/visual-contract.md), reproduce the exact selected state, compare the live result directly, and keep mismatches in rework.

## Final integration and review

Only the root performs final integration and review:

1. ensure every implementation descendant is done or cancelled with evidence;
2. ensure every active slot and run-owned runtime resource is settled;
3. inspect the combined change and adjacent callers;
4. resolve all changed-file and behavioral collisions;
5. rerun affected project checks;
6. record automated-check, visual-verification, and user-owned live-test-handoff verdicts separately against the combined fingerprint; include an agent-run real-behavior verdict only when explicitly requested;
7. record structured happy, error, edge, visual, and manual-test-handoff artifacts and build the evidence index;
8. run the global `agent-review` skill with three fresh read-only reviewer instances that differ from every implementation contributor and cannot delegate; each reviewer must be stronger than the combined caller and all-contributor ceiling, or the run is blocked;
9. bind every review report to its reviewer instance, wave, exact fingerprint, and structured finding IDs;
10. verify and fix accepted findings at the owning boundary;
11. rerun automated checks, required visual verification, and a fresh review until clean or blocked; do not wait for or perform user-owned live testing;
12. validate and certify final state:

```bash
bash <skill-root>/scripts/validate-integration-review.sh <feature-name> --certify
```

Apply `complete-run` immediately after certification. Any intervening state mutation clears certification. A user-owned live test is recorded as awaiting user verification, not skipped, passed, or blocked; an explicitly requested agent-run test that cannot be exercised remains blocked. Do not claim independent review when the runtime could not provide it, and do not mark completion while the fingerprint, evidence, collision ledger, reviewer provenance, or runtime cleanup is stale.

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
