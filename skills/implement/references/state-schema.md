# Implement skill — recursive state schema

All mutable run state lives in one canonical JSON file:

```text
var/<feature-name>/implement/state.json
```

Large recordings, reports, transcripts, and patches remain under the same run folder and are referenced from the JSON. They are evidence, not competing state stores.

Agents must never edit `state.json` directly. Every mutation goes through `scripts/state-store.py`, which locks the file, checks the immutable acting task ID, checks the coordinator lease when the root acts, validates root-wide limits and transitions, increments the revision, and replaces the JSON atomically.

## Run folder

```text
var/<feature-name>/implement/
  state.json
  .state.lock
  evidence/
  outputs/
var/<feature-name>/reviews/
```

The folder and state file may not be symbolic links or escape the repository root. `var/` must be ignored by Git. The helper rejects copied state outside this exact canonical location.

## Task identity and coordinator lease

Tasks are identified by immutable task IDs and constrained by their recorded lineage, status, parent-owned contract, recorded Pi session identity, and atomic transition rules. The state helper matches each descendant mutation to that task's launched Pi session.

The root also needs the active coordinator lease ID and must run from the Pi session recorded at initialization. Together they prevent another or stale coordinator session from taking over an active run. Root commands use:

```bash
export IMPLEMENT_COORDINATOR_LEASE_ID='<coordinator-lease-id>'
```

Children receive their task IDs but not the root lease. Their state updates must come from the Pi session recorded when their runtime launched. Root-only events require both the recorded coordinator session and matching unexpired lease.

## Version 4 shape

```json
{
  "version": 4,
  "feature_name": "example-feature",
  "revision": 12,
  "next_task_sequence": 4,
  "next_todo_sequence": 9,
  "run": {
    "status": "running",
    "phase": "execute",
    "repo_root": "/absolute/repository/root",
    "coordinator_instance_id": "immutable-root-instance",
    "coordinator_instance_history": [],
    "coordinator_model": {
      "instance_id": "immutable-root-instance",
      "provider": "example-provider",
      "model_id": "example-model",
      "thinking_level": "high"
    },
    "coordinator_model_history": [],
    "coordinator_lease": {
      "id": "opaque-lease-id",
      "expires_at": "2026-08-27T18:00:00Z"
    },
    "user_goal": "…",
    "root_task_id": "task-0001",
    "base_commit": "abc1234",
    "initial_worktree": {
      "already-modified.txt": "<sha256>"
    },
    "limits": {
      "max_depth": 2,
      "max_children_per_task": 6,
      "max_total_tasks": 18,
      "max_active_agents": 6
    },
    "active_agent_slots": ["task-0002"],
    "model_catalog": {
      "path": "~/.pi/agent/skills/model-routing-policy/models.json",
      "digest": "<sha256>",
      "schema_version": 1,
      "catalog_version": "2026-08-28",
      "models": [
        {
          "provider": "example-provider",
          "modelId": "example-model",
          "capabilities": {
            "inputTypes": ["text"],
            "taskClasses": ["implementation"]
          },
          "thinking": {
            "supportedLevels": ["low", "high"],
            "recommendedLevel": "high"
          },
          "routing": { "reviewTier": "standard" }
        }
      ]
    },
    "stop_reason": null
  },
  "tasks": {
    "task-0001": {
      "id": "task-0001",
      "parent_id": null,
      "root_id": "task-0001",
      "depth": 0,
      "title": "Coordinate the requested implementation",
      "outcome": "The requested behavior is implemented and verified",
      "acceptance_criteria": ["The real behavior passes"],
      "boundaries": ["Do not publish or deploy"],
      "inputs": [],
      "expected_result": "Integrated implementation and evidence",
      "task_class": "coordination",
      "allow_subagents": true,
      "status": "working",
      "phase": "work",
      "dependencies": [],
      "children": ["task-0002"],
      "todos": [],
      "model_selection": null,
      "model_resolution": null,
      "active_resolution": null,
      "attempts": 0,
      "runtime": {},
      "runtime_resources": [],
      "result": {
        "summary": null,
        "files_changed": [],
        "checks": [],
        "evidence": [],
        "blockers": []
      }
    }
  },
  "integration": {}
}
```

## Logical task contracts

Tasks are divided by independent outcomes, not preassigned folders. A task contract contains:

- one outcome;
- acceptance criteria;
- boundaries and inputs;
- expected result;
- dependencies, normally empty;
- a task class for model routing;
- whether the task may create children.

Every contract requires a title, outcome, expected result, acceptance criteria, and list-shaped boundaries and inputs. Children cannot rewrite contracts or widen authority. A parent may replan a child before its first launch. After work starts, the parent may update only dependencies while the child is explicitly blocked. Boundary or input changes require cancellation and a replacement task. The combined lineage-plus-dependency graph must remain acyclic, so a child cannot depend on an ancestor that is waiting for it.

Agents discover the code they need to change. Actual changed files are recorded in results for integration and collision detection; they are evidence after work rather than advance restrictions.

## Task and todo IDs

The state helper allocates stable run-wide IDs:

- tasks: `task-0001`, `task-0002`, …
- todos: `todo-0001`, `todo-0002`, …

Lineage is explicit through `parent_id`, `root_id`, `depth`, and `children`. Herdr names, panes, and agent sessions are runtime records and never replace task identity.

## Todos before work

Every agent's first action is to read its task and create todos before repository investigation, editing, or delegation.

```json
{
  "id": "todo-0007",
  "title": "Verify the current behavior",
  "acceptance": "The owning boundary and current behavior are understood",
  "required": true,
  "status": "pending",
  "evidence": null
}
```

Statuses are `pending`, `working`, `done`, `blocked`, or `cancelled`. A done todo requires evidence. Settled todos cannot be reopened; create a new todo for rework.

## Recursive delegation

`allow_subagents` permits but never requires delegation. A child may be added only when:

- the parent is allowed to delegate;
- the outcome is genuinely independent;
- the model catalog and selection validate;
- depth, immediate-child, total-task, and active-agent limits permit it;
- ready dependencies are done;
- an active slot is reserved atomically for immediate launch, or the child is explicitly queued.

Hard ceilings are depth 2, six immediate children, eighteen total tasks, and six active descendant agents. Editing the JSON cannot raise them. Automatic fallback has no fixed retry-count ceiling; cumulative exclusions and routing-zone exhaustion determine when no candidate remains. Maximum-depth and review tasks are always leaves. A confirmed no-contribution automatic-model failure advances the same immutable task through the atomic `prepare-fallback` event; the event appends the stopped attempt to `runtime_history`, validates cumulative routing and cleanup evidence, and reserves a fresh runtime slot without consuming a logical-child slot.

`add-child` returns the child task ID and slot-reservation result. Pass the immutable task ID and parent-owned contract to the child. Recovery uses recorded task, runtime, session, intent, and resource identities.

## Model routing

The Pi-global model catalog is bound by its path and SHA-256 digest, and its validated version plus model contents are snapshotted into state. Bindings require the approved versioned object with `schemaVersion`, `catalogVersion`, and a non-empty `models` list. Each model requires structured `capabilities.inputTypes`, `capabilities.taskClasses`, `thinking.supportedLevels`, `thinking.recommendedLevel`, and `routing.reviewTier` metadata. Review-capable delegated models also declare `routing.reviewComplexities` and optional `routing.reviewThinking`. New launches require the live catalog to match the complete snapshot. Later catalog drift blocks launches but does not prevent cleanup, cancellation, or recovery state updates.

Routing honors the catalog's optional `routing.delegation` field: `routine`
(Sol/Terra), `review-or-exceptional-debugging` (Astra), `exceptional-debugging`
(exploration-only), or `baseline-only` (the default for other catalog entries).
Caller and contributor entries remain valid baselines even when they cannot be
delegated. `request.exceptionalDebuggingReason` is normally null; an
evidence-backed exception is exploration-only and must remain unchanged through
fallback and launch verification. Routing artifacts are validated directly from their content and bound catalog
evidence.
Astra reviews need no debugging exception, are limited to complicated review, and
use exactly high thinking. Availability failures do not unlock Astra for other
routine work.

Task classes are:

- `coordination`
- `architecture`
- `implementation`
- `exploration`
- `focused-edit`
- `multimodal`
- `review`
- `integration`

Review routing also records `request.reviewComplexity` as `simple` or
`complicated`. Catalog metadata routes simple review only to Sol and complicated review only to
Astra, both at exactly `high` thinking.

A model selection records:

```json
{
  "provider": "example-provider",
  "model_id": "example-model",
  "task_class": "implementation",
  "input_types": ["text"],
  "reason": "Matches normal multi-step implementation",
  "thinking_level": "high",
  "caller": {
    "provider": "caller-provider",
    "model_id": "caller-model",
    "thinking_level": "medium"
  },
  "availability_evidence": "Present in the runtime model list"
}
```

Every model selection is bound to the preserved resolver artifact and its pre-launch digest. The selected model and recorded caller must exist in the bound catalog and declare their thinking levels. The selected model must support the recorded `input_types` and task class. Required independent-review selections record the current caller and every contributor in `reviewer_escalation.baselines`. Complicated review must select an Astra-high reviewer that is strictly stronger than the combined baseline. Simple changes normally create no reviewer selections; an explicitly requested simple review records simple complexity and resolves to a fresh, no-weaker Sol-high peer. A selection is immutable within one attempt. A model-specific failure with no usable contribution may advance only through `prepare-fallback`, which requires the new resolution to bind the active prior resolution, verified launch, complete runtime output, exact closed-resource response, unchanged routing zone, and exactly the prior selected model added to cumulative exclusions. Prompt dispatch is recorded separately from usable contribution: an immediate provider failure may occur after dispatch, but any recorded tool/file/result contribution, side effect, ambiguous output, or unclosed/preserved resource forbids fallback. Every other resolution or launch failure blocks after cleanup. Before a runtime becomes working or receives a prompt, a digest-bound verifier artifact must match the active resolution, bound start response, catalog digest, and immutable session identity. Attempt history preserves every earlier selection, resolution, session, failure, output, and cleanup artifact.

## Atomic updates

List every supported event without reading helper source or changing state:

```bash
python3 <skill-root>/scripts/state-store.py events
```

### Exact root bootstrap sequence

After `init-state.sh` succeeds, export the printed coordinator lease and use these event names and payload shapes in order:

```bash
export IMPLEMENT_COORDINATOR_LEASE_ID='<coordinator-lease-id>'
STATE='var/<feature-name>/implement/state.json'
STORE='<skill-root>/scripts/state-store.py'

python3 "$STORE" apply "$STATE" --actor task-0001 \
  --event-json '{"type":"set-run","updates":{"user_goal":"<requested outcome>"}}'

python3 "$STORE" apply "$STATE" --actor task-0001 \
  --event-json '{"type":"update-contract","updates":{"title":"<title>","outcome":"<one outcome>","acceptance_criteria":["<criterion>"],"boundaries":["<boundary>"],"inputs":["<input>"],"expected_result":"<result>"}}'

python3 "$STORE" apply "$STATE" --actor task-0001 \
  --event-json '{"type":"add-todo","title":"Read project instructions","acceptance":"Applicable rules are understood"}'

# Add the remaining root todos before advancing.
python3 "$STORE" apply "$STATE" --actor task-0001 \
  --event-json '{"type":"set-run-phase","phase":"plan"}'

bash <skill-root>/scripts/validate-plan.sh <feature-name>

python3 "$STORE" apply "$STATE" --actor task-0001 \
  --event-json '{"type":"set-task-status","status":"working"}'
python3 "$STORE" apply "$STATE" --actor task-0001 \
  --event-json '{"type":"set-run-phase","phase":"execute"}'
```

`set-run` owns `run.user_goal`; `update-contract` owns the root task's title, outcome, acceptance criteria, boundaries, inputs, and expected result. There is no `set-root-contract` event.

`apply` writes the state file only after the complete event validates. If it rejects an unknown event, malformed payload, or invalid transition, the state file remains unchanged. For those clearly non-mutating usage errors, consult `events`, correct the invocation, and retry. Continue correcting and retrying while each rejection remains clearly non-mutating and actionable. Do not retry credential or authorization failures, malformed existing state, ambiguous failures, or any command that may have produced an external side effect.

Read state:

```bash
python3 <skill-root>/scripts/state-store.py show \
  var/<feature-name>/implement/state.json --task task-0002
```

Apply a child update using its immutable task ID:

```bash
python3 <skill-root>/scripts/state-store.py apply \
  var/<feature-name>/implement/state.json \
  --actor task-0002 \
  --event-json '{"type":"add-todo","title":"Inspect current behavior","acceptance":"Current behavior is understood"}'
```

Validate without mutation:

```bash
python3 <skill-root>/scripts/state-store.py validate \
  var/<feature-name>/implement/state.json
```

Event families cover run configuration and phase transitions, root contract updates, parent-owned child replanning, todos, children, frozen model selection, agent slots, runtime records, typed `record-pane-readiness` evidence, resources, results, task transitions, two-phase cancellation, typed integration updates and completion.

## Runtime ownership

Before an external create, the delegating task partitions ordered child assignments into groups of at most four and records one owned tab per group. Each group uses the Herdr skill's fixed 2x2 split order. The coordinator validates the live pane count and layout before accepting each create response; a fifth pane or out-of-order split is a workflow failure and must not proceed to launch. Additional children require another tab; for example, a six-child wave uses a four-pane tab and a two-pane tab. Every tab remains a separate owned resource with its own create and cleanup evidence. Pane geometry is live Herdr evidence governed by the Herdr workflow contract; the durable state store tracks ownership and lifecycle, not terminal geometry. Every newly bound pane or agent resource records its exact owned `parent_tab_id`. When an owned tab close cascade-deletes those resources, settle the tab first, then settle each child resource with the same digest-bound `cli:tab:close` artifact and reason `cascade-deleted-with-owned-tab`; validation requires the matching closed parent tab and digest.

During bounded pane warm-up, startup helpers may appear, exit, or replace one another while the pane ID and shell PID remain stable. These transitions remain `busy`; only a sole-shell snapshot becomes `ready`. The 300-second deadline limits readiness attainment and does not expire a ready proof while synchronized agent launches are being bound. Herdr's live `agent start` busy-pane check remains authoritative after readiness.

Before an external create, the delegating task records a unique runtime intent, target task, runtime name, and output artifact under `outputs/`. The Herdr JSON create response is redirected to that artifact before IDs are parsed. Binding rechecks output-folder containment, verifies its digest, parses the saved JSON at the intent's declared response-ID path, and requires that ID and resource kind to match. For a pane, pass the persisted pre-create intent timestamp to the Herdr readiness classifier and persist the canonical 300-second deadline it derives from that single clock anchor; never calculate the deadline from a second clock read. Every valid process snapshot and classifier result is preserved as readiness evidence, including the classifier's `observedAt`; observations must be monotonic across rechecks, and resume never restarts that budget. Helper validation failures that cannot provide a valid deadline are preserved as generic failure artifacts and cleaned up before any readiness-state event. A `ready`, `expired`, or `ambiguous` probe is terminal; validation rejects every historical or new probe that follows it. If deadline derivation exceeds the timestamp range, the classifier returns `ambiguous` with the maximum representable deadline; record that terminal probe, then clean up instead of launching. Agent intents are single-use per attempt and may launch only their declared direct-child target. An `agent_pane_busy` response after a ready proof means the certified process state changed before launch. Preserve it as a digest-bound artifact under `outputs/` and reference it from task result/blocker evidence, but fail closed without retry: do not submit another readiness probe or reuse the pane or intent, and follow the normal cleanup path. This leaves durable recovery evidence even if the coordinator stops between create and state binding.

Runtime records bind the task to:

- runtime agent name or handle;
- immutable agent-instance/session ID;
- selected and launched provider/model/thinking level;
- pane and tab IDs;
- productive-prompt state;
- a future deadline no more than three hours away;
- a collected output location and SHA-256 digest.

Resources have globally unique IDs and statuses `live`, `closed`, or `preserved`. Preserved resources require a blocker reason. Closing requires a digest-bound runtime close-response artifact under `outputs/`. A task cannot settle until every resource is closed. Preserved resources keep the task and run blocked until verified closure.

A successful child records its blocker-free result and returns after its required todos are done and its descendants and resources settle. The parent first records observed runtime settlement, then applies `accept-task` with verification evidence. Acceptance validates the result, marks the child done, and releases its slot atomically. Blocked tasks cannot be accepted. This avoids freeing capacity while a child still runs.

## Two-phase cancellation

Cancellation never frees capacity before shutdown:

1. `cancel-subtree` records a reason and parent disposition, moves unfinished tasks to `cancelling`, and requests runtime cancellation without releasing slots.
2. Descendants are stopped deepest-first.
3. Partial output is collected and resources are closed or preserved.
4. Runtime status is recorded as stopped, settled, or cancelled.
5. `finalize-cancellation` releases the slot and marks one task cancelled.
6. Parents are finalized only after descendants settle.

A cancelling task is not complete and its slot cannot be reused. Successful tasks require all required todos to be done; cancellation never silently satisfies required work. Cancelling the whole run uses the separate terminal `cancel-run` event after descendants and resources settle.

## Integration state

The root records a small final integration summary:

```json
{
  "test_verdict": "pass",
  "skipped_reason": null,
  "test_evidence": ["npm run check passed"],
  "behavior_verdict": "user-pending",
  "behavior_reason": "The user owns the live interactive check.",
  "behavior_evidence": ["evidence/manual-live-test.md"],
  "changed_files": ["src/example.ts"],
  "collisions": [],
  "review_requirement": {
    "classification": "complicated",
    "source": "automatic",
    "required": true,
    "reason": "The change crosses a security-sensitive workflow boundary."
  },
  "review_verdict": "pass",
  "review_execution": "independent",
  "review_wave": 2,
  "minimum_review_wave": 2,
  "review_resources": [
    {"kind": "tab", "id": "workspace:tab", "status": "closed"}
  ],
  "review_perspectives": {
    "correctness_safety": {
      "agent_id": "reviewer-a",
      "agent_instance_id": "pi-session-a",
      "provider": "example-provider",
      "model_id": "example-reviewer",
      "thinking_level": "high",
      "status": "complete",
      "output_path": "var/example-feature/reviews/wave-2-correctness.md"
    },
    "architecture_integration": {
      "agent_id": "reviewer-b",
      "agent_instance_id": "pi-session-b",
      "provider": "example-provider",
      "model_id": "example-reviewer",
      "thinking_level": "high",
      "status": "complete",
      "output_path": "var/example-feature/reviews/wave-2-architecture.md"
    },
    "regression_fix_quality": {
      "agent_id": "reviewer-c",
      "agent_instance_id": "pi-session-c",
      "provider": "example-provider",
      "model_id": "example-reviewer",
      "thinking_level": "high",
      "status": "complete",
      "output_path": "var/example-feature/reviews/wave-2-regression.md"
    }
  },
  "review_findings": [],
  "combined_report_path": "var/example-feature/reviews/wave-2-summary.md",
  "finished_at": null
}
```

`review_requirement` records why review ran or why it was unnecessary. An automatically classified simple change uses `review_execution: not-required`, `review_verdict: not-required`, wave zero, and no review reports. Simple may include localized user-visible work across several closely related files when it follows an established pattern, remains low risk, and direct inspection plus normal checks are sufficient. Substantial features, complicated changes, and explicit review requests use three fresh read-only perspectives.

The helper-owned, non-decreasing `minimum_review_wave` prevents a reviewed wave from being reused after rework. `review_resources` retains only owned review-tab IDs and open/closed cleanup status; it does not retain model-resolution or launch-check output. Record the tab immediately after creation and close it in state only after Herdr confirms absence. Resource IDs cannot be removed or reopened; recovery permits closure-only updates.

Review reports are deliberately human-readable history. Each perspective report ends with the exact reviewer instance, provider/model, thinking level, `Finding IDs`, and verdict lines. The current reviewers must be three different fresh Pi sessions and must not be coordinators, implementation contributors, or reviewers from an earlier wave. The summary ends with `Finding IDs` and verdict lines after recording accepted, rejected, and unresolved findings. If implementation changes after a review, preserve the old wave, return through execution so review state is invalidated, and run a new wave.

`changed_files` must match the root's surviving worktree delta from the initial snapshot. Every sibling overlap requires a collision entry, and every collision must be resolved with rerun evidence before completion.

Checks and behavior evidence may be short descriptions or paths to readable, nonempty supporting files. Path-shaped strings and declared `path` or `artifact` fields must resolve inside the repository. A passing check or behavior verdict requires at least one readable entry. A skipped check requires a reason. User-owned live verification requires both a reason and a usable handoff entry; it remains pending honestly and is not treated as passed.

## Validation and completion

Validate the final state directly:

```bash
bash <skill-root>/scripts/validate-integration-review.sh <feature-name>
```

The validator checks current state, the live changed-file list, settled checks and behavior status, resolved collisions, and the required readable review files.

After validation, apply `complete-run`. Completion performs the same live checks while holding the state lock, requires all todos and descendants to be settled, requires all runtime resources to be closed, and then marks the root and run complete.

## Resume

Resume reads the coordinator lease ID from the environment. Ordinary root updates require an unexpired matching lease. Expired takeover requires a fresh lease ID, creates a new coordinator instance, and fences the old one. When live implementation runtime or an open final-review tab exists, takeover persists `reconciliation_required`; only recovery and cleanup events are accepted until the root closes recorded review tabs and records reconciliation evidence. Descendant recovery remains bound to recorded task and runtime identities.

A version 4 state created before Pi-session ownership was introduced may bind its still-active matching lease to the current Pi session once during resume; later mismatches fail closed. Version 3 state is never migrated or resumed automatically. Finish it with the earlier workflow or start a separately named version 4 run.
