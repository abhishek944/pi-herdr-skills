# Implement skill — recursive phase machine

The run and every descendant are represented in `state.json`. Every agent begins each turn by reading its task and current root-wide limits.

## Root phases

```text
bootstrap → plan → execute → integrate → review → complete
     ↘         ↘        ↘           ↘
                    blocked
```

Valid transitions are enforced by the state helper:

- `bootstrap → plan | blocked`
- `plan → execute | blocked`
- `execute → integrate | blocked`
- `integrate → review | execute | blocked`
- `review → complete | integrate | blocked`
- `blocked → plan | execute | integrate | review`

`complete` is reached only through the live-validated `complete-run` event.

## Task states and phases

```text
planning → queued → launching → working ↔ waiting ↔ integrating
    ↘          ↘          ↘          ↘           ↘
                          blocked → working
                             ↘
                         cancelling → cancelled

working/integrating → done (through parent acceptance)
```

Blocked work returns through `working` before integration. The helper enforces valid transitions and status/phase pairs. Settled tasks cannot be reopened. Create a new todo or replacement task when fresh work is required.

## Required task loop

```text
read state and own task
→ identify the immutable task ID
→ create/update todos before other work
→ inspect dependencies and root limits
→ work directly OR create independent logical children
→ bind each child to a catalog model
→ atomically reserve a root-wide slot
→ launch, prompt, and monitor children
→ collect structured results
→ close or preserve exact run-owned resources
→ inspect actual changed files and resolve collisions
→ complete todos and record evidence
→ return the result
→ parent records observed runtime settlement and atomically accepts the blocker-free task with verification evidence
```

Todos are maintained throughout the task, never reconstructed at the end.

## Task identity and coordinator lease

- The root uses the active coordinator lease ID from the Pi session recorded at initialization.
- Each child acts only as its immutable task ID under its parent-owned contract and recorded Pi session identity.
- Descendant state transitions remain constrained by lineage, task status, active slots, runtime ownership, and atomic validation.
- A different root coordinator cannot take over an unexpired lease.
- Root operations renew the matching lease. Resume refuses unreconciled live runtime state.

## Recursive launch rules

1. `allow_subagents` must be true on the parent.
2. Delegation uses independent outcomes, not folders. New files and folders are allowed.
3. A parent may create at most six immediate children. Immutable hard ceilings also cover depth, total tasks, and active agents. Safe automatic-model fallback has no fixed attempt-count ceiling; it advances the same task through an append-only attempt ledger while every runtime remains fresh, and ends when cumulative exclusions exhaust the routing zone.
4. Descendant contracts are parent-owned. Children cannot rewrite or widen them.
5. The parent follows the global `model-routing-policy`, chooses a task class, binds the Pi-global versioned model catalog by digest, verifies availability, and records the selected provider/model/thinking settings before launch. A confirmed model-specific automatic-routing failure with no usable contribution is stopped and cleaned up, then `prepare-fallback` atomically verifies its chained evidence and reserves the next fresh attempt on the same task. A newly created pane still finishing shell initialization first follows the Herdr skill's bounded pre-launch readiness recovery and does not consume an attempt. User pins, ambiguous failures, partial work, setup failures that remain after readiness recovery, and provenance failures block.
6. Adding a ready child and reserving its slot is one atomic event. Dependency-blocked children are queued without a slot.
7. If no slot is available, do not wait indefinitely while holding a parent slot. Keep work in the current task, reduce decomposition, or settle existing children first.
8. The child receives the global `implement` skill, feature name, state location, task ID, and logical contract. Its first mutation creates todos.
9. Small or cohesive children are leaves. Maximum-depth and review tasks are always leaves.
10. Only the root performs final combined integration and review.

## Herdr lifecycle at every level

Before controlling Herdr, read the global Herdr skill and verify eligibility.

For each wave, the delegating task:

1. reads its recorded resources and root-wide slots;
2. partitions ordered children into consecutive groups of at most four, records distinct tab and first-child root-pane intents, runtime names, and response artifacts for every group, and never plans a fifth pane in one tab;
3. creates one dedicated unfocused tab per group, saves the full Herdr JSON response for the matching tab intent, copies it to the distinct root-pane artifact, parses the returned IDs, and binds every tab and root pane separately;
4. assigns each returned root pane to its group's first child, then creates and binds the remaining panes in fixed 2x2 order: split root right for child two, split root down for child three, and split child two down for child four; every tab has at most four child panes and no unused coordinator pane;
5. creates each named pane and uses `herdr pane rename` to give every pane across every tab a distinct responsibility name before agent startup; pane names are mandatory, and every owned tab is tracked and cleaned up separately;
6. passes each pane's persisted pre-create intent timestamp to the Herdr readiness classifier and persists the canonical deadline it derives from that single clock anchor—never a second current-time calculation—records every process snapshot and classification through the typed `record-pane-readiness` state event, allows sequential startup helpers to turn over while the exact pane and shell stay stable, applies the Herdr skill's bounded readiness gate to every newly created pane without restarting the budget after resume, makes the complete batch ready before starting any agent, treats the deadline as the readiness-attainment bound rather than an expiry on a ready proof, and fails closed without retry if a certified pane becomes busy during start;
7. starts all agents concurrently through Pi in their named panes using Herdr's mandatory `--kind pi`, passes the recorded provider/model/thinking settings explicitly, and captures immutable agent-session provenance with a bounded deadline;
8. saves each complete start response, records the actual launched provider/model/thinking settings, and verifies all three against the preserved model-routing resolution before prompting;
9. after all Pi agents start, launches one `herdr agent prompt ... --wait` process per child concurrently with its complete handoff;
10. while those processes are still running, observes each agent enter working state and immediately records productive-prompt evidence through the dedicated write-once event;
11. only after dispatch is durably recorded, joins the concurrent prompt-and-wait processes with deadlines of at least `900000` milliseconds (15 minutes), while preserving the runtime schema's three-hour maximum; overdue work enters timeout cancellation and cannot settle successfully;
12. stores complete child output and digest, then reconciles it with real changes;
13. records the observed child runtime as settled, then applies `accept-task` with verification evidence; acceptance marks the child done and releases its slot atomically;
14. closes or preserves exact recorded resources after outputs and descendant state are durable.

A child may create a separate tab for descendants, but never controls or closes the tab containing itself. The resource creator owns normal cleanup. The root may settle an exact descendant resource during recovery.

## Partial launch and prompt recovery

- If no child contributes usable work, close recorded resources and confirm each runtime stopped. Advance only confirmed no-contribution automatic-model failures through `prepare-fallback`; block failures that do not qualify.
- If some children contribute, never reset or duplicate them. Monitor those children and retry only qualifying failed roles after cleanup.
- `unknown`, missing output after possible work, and approval prompts are neither completion nor safe fallback evidence.
- Never reuse a failed pane, session, intent, or model. An `agent_pane_busy` response after readiness proves the process state changed after the readiness proof; preserve it as failure evidence, clean up, and block without retry. A fallback preserves the logical task contract but creates a fresh runtime after exact cleanup.

## Dependencies and collisions

Dependencies are uncommon and explicit. A queued task launches only after dependencies are done. Cycles are checked across dependency and parent-waits-for-child edges, so a child cannot depend on an ancestor waiting for it.

If overlap is discovered after launch, the child becomes blocked. Its parent may then add dependencies, narrow inputs or boundaries, serialize work, or integrate directly.

Tasks are not assigned folders in advance. After children settle, the parent compares their reported changed files and the real combined changes. Every file or behavioral collision is recorded as open, resolved with evidence, and rechecked. Last-writer-wins is never accepted silently.

## Two-phase cancellation

Cancellation proceeds deepest-first without freeing capacity early:

1. `cancel-subtree` records a reason and parent disposition, moves unfinished tasks to `cancelling`, and requests runtime cancellation.
2. Slots remain occupied.
3. Stop descendants and record confirmed stopped/settled runtime state.
4. Collect partial output.
5. Close resources or preserve them with a blocker reason.
6. `finalize-cancellation` releases one task's slot and marks it cancelled.
7. Finalize the parent only after every child settles.

A cancellation request alone is not a settled task.

## Resume and recovery

Validate the state, match the current Pi session and coordinator lease to the recorded owner, and compare every active slot and live resource with Herdr runtime state.

Resume healthy agents. If an agent is unhealthy or runtime ownership cannot be proven, preserve owned evidence and block; never replace the agent. The root can settle descendant resources only by exact recorded task and resource IDs.

An expired takeover uses a fresh lease and coordinator instance. If active slots, live resources, or planned intents remain, state persists a reconciliation gate. Intent binding/failure, runtime inspection, cleanup, and cancellation remain available; launches and ordinary work stay disabled until every intent is bound or failed, every slot/runtime is classified, and reconciliation evidence is recorded.

## Root integration and review

Before reviewer creation, the root uses the proportionate review gate to classify the change as simple, complicated, or feature and records `review_requirement`. Localized user-visible behavior and multiple touched files may still be simple when the work follows an established pattern, stays low risk, and is confidently covered by direct inspection plus normal checks.

The root:

1. waits for every implementation descendant to settle or records how cancelled outcomes were covered;
2. requires task-reported changed files to equal the live worktree delta from the initial snapshot;
3. derives sibling overlaps and resolves every collision with rerun evidence;
4. runs combined automated checks and required visual verification, then writes a user-owned live-test handoff when appropriate;
5. records short check and behavior summaries plus the review requirement;
6. directly inspects automatic simple changes and records review as not required;
7. for substantial features, complicated changes, or explicit review requests, runs three fresh read-only reviewers through the global Agent Review workflow;
8. saves only the readable correctness, architecture, regression, and summary reports for each review wave;
9. records reviewer identity, model, report paths, and structured finding status;
10. fixes accepted findings, reruns affected checks, and starts a fresh review wave whenever implementation changed;
11. runs `validate-integration-review.sh <feature-name>`;
12. applies `complete-run`, which repeats the live changed-file, report, task, and resource checks while holding the state lock.

Prior review waves remain readable history. The newest required wave must be clean, every finding and collision must be resolved, and all runtime resources must be closed before completion.
