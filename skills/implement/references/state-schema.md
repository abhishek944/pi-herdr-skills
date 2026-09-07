# Implement skill — recursive state schema

All mutable run state lives in one canonical JSON file:

```text
var/<feature-name>/implement/state.json
```

Large recordings, reports, transcripts, and patches remain under the same run folder and are referenced from the JSON. They are evidence, not competing state stores.

Agents must never edit `state.json` directly. Every mutation goes through `scripts/state-store.py`, which locks the file, authenticates the acting task, checks the coordinator lease when the root acts, validates root-wide limits and transitions, increments the revision, and replaces the JSON atomically.

## Run folder

```text
var/<feature-name>/implement/
  state.json
  .state.lock
  evidence/
  outputs/
  reviews/
  evidence-index.md
```

The folder and state file may not be symbolic links or escape the repository root. `var/` must be ignored by Git. The helper rejects copied state outside this exact canonical location.

## Credentials are not state

Each task has a capability hash in `state.json`. The raw capability is returned once when the task is created and passed only to that agent. The root capability is the owner token printed during initialization.

The root also needs the active coordinator lease ID. Raw capabilities are runtime credentials, not state or evidence. Never write them into `state.json`, prompts saved as artifacts, reports, logs, or user-facing output.

Root commands use:

```bash
export IMPLEMENT_TASK_CAPABILITY='<root-owner-token>'
export IMPLEMENT_COORDINATOR_LEASE_ID='<coordinator-lease-id>'
```

A child receives only its own task capability. It does not receive the root lease.

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
      "max_active_agents": 6,
      "max_retries_per_task": 31
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
      "capability_hash": "<sha256>",
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

Hard ceilings are depth 2, six immediate children, eighteen total tasks, six active descendant agents, and 32 candidate attempts per task. Editing the JSON cannot raise them. Maximum-depth and review tasks are always leaves. A confirmed no-contribution automatic-model failure advances the same immutable task through the atomic `prepare-fallback` event; the event appends the stopped attempt to `runtime_history`, validates cumulative routing and cleanup evidence, and reserves a fresh runtime slot without consuming a logical-child slot.

`add-child` returns the child task ID and raw child capability. Pass the raw capability to that child, then discard it from coordinator artifacts. If an inactive, unproductive child's capability is lost during recovery, its parent or the root may rotate it; the old hash remains in audit history.

## Model routing

The Pi-global model catalog is bound by its path and SHA-256 digest, and its validated version plus model contents are snapshotted into state. Bindings require the approved versioned object with `schemaVersion`, `catalogVersion`, and a non-empty `models` list. Each model requires structured `capabilities.inputTypes`, `capabilities.taskClasses`, `thinking.supportedLevels`, `thinking.recommendedLevel`, and `routing.reviewTier` metadata. New launches require the live catalog to match the complete snapshot. Later catalog drift blocks launches but does not prevent cleanup, cancellation, or recovery state updates.

Task classes are:

- `coordination`
- `architecture`
- `implementation`
- `exploration`
- `focused-edit`
- `multimodal`
- `review`
- `integration`

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

Every model selection is bound to the preserved resolver artifact and its pre-launch digest. The selected model and recorded caller must exist in the bound catalog and declare their thinking levels. The selected model must support the recorded `input_types` and task class. Review selections record the current caller and every contributor in `reviewer_escalation.baselines` and must select a strictly stronger reviewer. A selection is immutable within one attempt. A model-specific failure with no usable contribution may advance only through `prepare-fallback`, which requires the new resolution to bind the active prior resolution, verified launch, complete runtime output, exact closed-resource response, unchanged routing zone, and exactly the prior selected model added to cumulative exclusions. Prompt dispatch is recorded separately from usable contribution: an immediate provider failure may occur after dispatch, but any recorded tool/file/result contribution, side effect, ambiguous output, or unclosed/preserved resource forbids fallback. Every other resolution or launch failure blocks after cleanup. Before a runtime becomes working or receives a prompt, a digest-bound verifier artifact must match the active resolution, bound start response, catalog digest, and immutable session identity. Attempt history preserves every earlier selection, resolution, session, failure, output, and cleanup artifact.

## Atomic updates

List every supported event without reading helper source or changing state:

```bash
python3 <skill-root>/scripts/state-store.py events
```

### Exact root bootstrap sequence

After `init-state.sh` succeeds, export the printed root credentials and use these event names and payload shapes in order:

```bash
export IMPLEMENT_TASK_CAPABILITY='<root-owner-token>'
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

`apply` writes the state file only after the complete event validates. If it rejects an unknown event, malformed payload, or invalid transition, the state file remains unchanged. For those clearly non-mutating usage errors, consult `events`, correct the invocation, and retry once. Do not retry credential or authorization failures, malformed existing state, ambiguous failures, or any command that may have produced an external side effect.

Read state:

```bash
python3 <skill-root>/scripts/state-store.py show \
  var/<feature-name>/implement/state.json --task task-0002
```

Apply a child update:

```bash
IMPLEMENT_TASK_CAPABILITY='<child-capability>' \
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

Event families cover run configuration and phase transitions, root contract updates, parent-owned child replanning, todos, children, frozen model selection, agent slots, runtime records, typed `record-pane-readiness` evidence, resources, results, task transitions, two-phase cancellation, typed integration updates, final certification, and completion.

## Runtime ownership

Before an external create, the delegating task records a unique runtime intent, target task, runtime name, and output artifact under `outputs/`. The Herdr JSON create response is redirected to that artifact before IDs are parsed. Binding rechecks output-folder containment, verifies its digest, parses the saved JSON at the intent's declared response-ID path, and requires that ID and resource kind to match. For a pane, the persisted pre-create intent timestamp is also the conservative anchor for its immutable 30-second readiness deadline; every process snapshot and classifier result is preserved as evidence, and resume never restarts that budget. Agent intents are single-use per attempt and may launch only their declared direct-child target. A proven pre-launch `agent_pane_busy` shell warm-up before any agent session exists is not a consumed launch: after `record-pane-readiness` binds the exact pane, immutable deadline, digest-bound snapshots, classifications, and complete busy response, the same agent intent remains planned and unconsumed and may retry once within its original readiness deadline. This typed evidence is the only planned-intent exception that reconciliation may carry forward; a repeated busy response and every other failed, ambiguous, expired, or partial start fail the intent and require the normal cleanup path. This leaves durable recovery evidence even if the coordinator stops between create and state binding.

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

Before reviewer launch, the root writes `contract-review-pack.json` and `evidence/contract-preflight.json` in the canonical run folder. The global Agent Review validator recomputes discovery, exact resolved/deferred branch coverage, current evidence, feature name, and review fingerprint. Both files are digest-bound certification artifacts.

The root records the complete final contract:

```json
{
  "test_verdict": "pass",
  "skipped_reason": null,
  "test_target_fingerprint": "…",
  "behavior_verdict": "user-pending",
  "behavior_reason": "The user owns live interactive end-to-end testing.",
  "behavior_target_fingerprint": "…",
  "behavior_evidence": [
    {
      "case_type": "user-handoff",
      "artifact": "evidence/manual-live-test.md",
      "fingerprint": "…"
    }
  ],
  "evidence_target_fingerprint": "…",
  "evidence_index": "var/example-feature/implement/evidence-index.md",
  "changed_files": ["src/example.ts"],
  "collisions": [
    {
      "tasks": ["task-0002", "task-0003"],
      "files": ["src/shared.ts"],
      "status": "resolved",
      "resolution": "Root integrated both behaviors",
      "rerun_evidence": ["Combined check passed"]
    }
  ],
  "review_verdict": "pass",
  "review_execution": "independent",
  "review_wave": 2,
  "review_scope": {
    "base_sha": "…",
    "target_ref": "WORKTREE",
    "target_sha": null,
    "paths": ["src"]
  },
  "review_target_fingerprint": "…",
  "review_wave_fingerprint": "…",
  "review_waves": [
    {
      "wave": 2,
      "fingerprint": "…",
      "status": "complete",
      "started_at": "…",
      "reviewer_instance_ids": [
        "immutable-session-a",
        "immutable-session-b",
        "immutable-session-c"
      ]
    }
  ],
  "review_perspectives": {
    "correctness_safety": {
      "agent_id": "reviewer-a",
      "agent_instance_id": "immutable-session-a",
      "provider": "example-provider",
      "model_id": "example-reviewer",
      "thinking_level": "high",
      "resolution_artifact": {
        "path": "outputs/reviewer-a-resolution.json",
        "digest": "<sha256>"
      },
      "start_response_artifact": {
        "path": "outputs/reviewer-a-start.json",
        "digest": "<sha256>"
      },
      "verification_artifact": {
        "path": "outputs/reviewer-a-verification.json",
        "digest": "<sha256>"
      },
      "status": "complete",
      "started_at": "…",
      "deadline_at": "…",
      "output_path": "reviews/wave-2-correctness.md"
    }
  },
  "review_findings": [
    {
      "id": "finding-1",
      "severity": "P2",
      "status": "resolved",
      "resolution": "Fixed and rechecked"
    }
  ],
  "combined_report_path": "reviews/wave-2-combined.md",
  "certification": null,
  "finished_at": null
}
```

`changed_files` must exactly match the root's surviving integrated-file result and the worktree delta from the initial snapshot, including file type and mode. Child file lists remain historical and drive collision derivation without forcing reverted edits into the final list. The review base must equal the run base, and every changed file must be inside scope. Every sibling file overlap requires a collision entry resolved with rerun evidence. Review-wave history is append-only and increasing. Reviewer instance IDs must be unique, distinct from all productive/file-changing contributors and coordinator instances, and unused by earlier waves. Current and historical coordinator model settings are preserved and required in every reviewer baseline. Every perspective must preserve its provider/model/thinking choice, stronger-baseline resolution, Herdr Pi start response, and launch-verification artifact with live SHA-256 digests. Certification rechecks those proofs and requires every implementation contributor in each resolution baseline. If independent review cannot run, completion is blocked.

Each reviewer report contains exact markers:

```text
Fingerprint: <current-fingerprint>
Contract pack: <contract-pack-sha256>
Contract preflight: <preflight-output-sha256>
Review wave: <number>
Reviewer: <agent-id>
Finding IDs: finding-1, finding-2
```

Use `Finding IDs: none` when clean. Structured `review_findings` must exactly match the IDs declared across reports, and every finding must be resolved or rejected with a reason. The combined report contains the fingerprint, contract-pack digest, preflight digest, and wave markers. Certification recomputes contract discovery and evidence validation before accepting these markers.

Automated tests may be skipped only with a reason. A passing test verdict requires current digest-bound test evidence under the run evidence folder. Live interactive behavior verification is separate and user-owned unless the latest request explicitly asks an agent to run it. Use `user-pending` with one current `user-handoff` artifact and a clear reason; this allows implementation closeout without claiming a live pass. An explicitly requested agent-run pass requires current happy, error, and edge artifacts inside the run evidence folder. `not-applicable` is accepted only for a documented documentation-only change whose surviving files are Markdown, text, or reStructuredText. Missing runtime, authentication, fixtures, or credentials blocks only an explicitly requested agent-run test—not a normal user-owned handoff.

## Certification and completion

After all integration fields and reports are current, run:

```bash
bash <skill-root>/scripts/validate-integration-review.sh <feature-name> --certify
```

Certification is bound to the exact state revision, live fingerprint, actual run-owned worktree delta, recomputed contract preflight, and SHA-256 digests of the contract pack, preflight output, distinct review, behavior, runtime-response, and productive-task-output artifacts. Any later state change clears it. `complete-run` recomputes the live fingerprint, worktree delta, contract preflight, and every artifact digest as its final gate before atomically completing the root and run.

## Resume

Resume reads the owner token and lease ID only from protected environment variables. Ordinary root updates require an unexpired matching lease. Expired takeover requires a fresh lease ID, creates a new coordinator instance, and fences the old one. When live runtime exists, takeover persists `reconciliation_required`; only recovery and cleanup events are accepted until the root records reconciliation evidence. Rotate lost child capabilities only for inactive, unproductive tasks.

Version 3 state is never migrated or resumed automatically. Finish it with the earlier one-level workflow or start a separately named version 4 run.
