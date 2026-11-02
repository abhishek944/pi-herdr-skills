---
name: implement
description: "Coordinate every tracked Work, including delegated work, with session/Work/Task artifact paths, explicit self-versus-delegate decisions, focused execution, and verification. Preserve specialized skill scope and user authorization."
compatibility: Requires a repository checkout, pi-tasks tracking tools, and a Pi shell tool exposing PI_SESSION_ID. Delegation requires Herdr Core, a visible app tab per worker, and continuous monitoring.
---

# Implement

Use this skill as the coordination workflow for every tracked Work, including each subagent's local Work. Reuse it when already active rather than recursively invoking it. Specialized skills still own their behavior: research and review remain read-only, interviews do not authorize implementation, and user-requested planning stays planning-only. Coordination never grants permission to edit, test, delegate, commit, or deploy beyond the owning skill and user request. Keep the process small, readable, and easy to resume.

Before replying to the user, follow the global `talk-human` skill. Also follow `no-unit-tests` unless the user's latest request explicitly asks for unit tests. Follow the global `no-arbitrary-limits` skill for every implementation, fix, refactor, migration, and maintenance task: do not add unrequested capacity caps or ask about optional limits during implementation; explain relevant optional controls only after completion.

## Session coordination

Before executing requested work, call `WorkList` and `TodoList`, create or resume the relevant Work, and create or update its Todos. Require a real `workId` and an active `taskId` for the current step; keep task status current with `TodoUpdate` and use `WorkUpdate` when shared scope or context changes. Reading instructions, obtaining identity, and establishing tracking are startup steps, not a reason to invent IDs. If tracking tools or required IDs are unavailable, report the blocker and do not begin execution. Use `MonitorCreate` for long-running background commands; `AgentCreate` establishes the mandatory continuous Herdr worker subscription through pi-loop-monitor when available. Use `LoopCreate` only for a future or repeated wake. Plain conversation does not require a Work. Never create or update tracking, execute this workflow, or launch agents during `/ask` or `/btw`.

Works are collections of tasks with shared context, not executable records. Never assign a Work its own active, blocked, completed, or cancelled status, and do not pass status to Work tools. Tasks alone own status. Track each executable step as a Todo; continuation considers active tasks across all Works on the current session branch. Empty Works and blocked, completed, or cancelled tasks do not trigger continuation. Keep Work progress derived from task progress rather than adding a parent lifecycle.

## Rules

- Read repository instructions and relevant flow or architecture documentation first.
- Preserve unrelated changes and existing staged work.
- Do not commit, push, publish, or deploy unless explicitly asked.
- Do not hard-code an answer for one example or bypass the owning boundary.
- Use resolved `grill-me` and `ui-ux-grill-me` decisions as requirements; deferred decisions are not requirements.
- For every task, choose `self` or `delegate` and record a short reason in `taskInfo` before execution, following the ownership decision below. A read-only review is not a substitute for considering implementation delegation.
- Leave live interactive end-to-end testing to the user unless they explicitly ask the agent to run it.

## Scope discipline

- Build only the current requested outcome and changes necessary to deliver it. State the smallest complete outcome and non-goals in the existing plan or taskInfo, not another document. Agent-written acceptance criteria cannot authorize extra requirements. Earlier authorization is not a standing instruction to resume unrelated unfinished work or paid verification; carry earlier work forward only when the current request continues it.
- Default to no additional runtime machinery. Estimators, reservation pools, repeated checksums, recovery systems and blocking gates require an explicit requirement or demonstrated failure that the approved task must address. Hypothetical robustness is not justification. Reuse platform and trusted-boundary guarantees; count false refusals, latency and recovery burden as costs. Omit optional or duplicate checks rather than implement them by default. Preserve essential authorization, untrusted-input validation and data-loss protection.
- Compose existing capabilities before creating infrastructure. New persistent state, recovery behavior, lifecycle ownership or public abstractions must be necessary for a concrete requirement or demonstrated failure within the approved scope. Generic robustness, production-readiness and hypothetical future cases do not expand that scope.
- Instructions governing how the agent coordinates work are not automatically requirements for runtime machinery in the code being built. Keep policy with its existing owner unless moving it is required by the task.
- If the smallest complete solution requires materially broader guarantees or scope, explain the tradeoff and obtain direction before expanding. Otherwise choose the smaller solution and proceed without unnecessary approval prompts.
- Keep essential validation, security, cancellation handling and data-loss protection. Simplicity means removing unnecessary guarantees and machinery, not hiding errors or leaving required behavior incomplete. Stop when the requested behavior and allowed verification are complete; optional hardening is not a new task.

## Diagnose failures and recover

A failure, timeout, or retry limit is a diagnosis checkpoint, not an automatic reason to hand off unfinished work. Actively investigate the cause and pursue the authorized outcome while a safe, evidence-backed next step remains.

1. Inspect the actual error, available full logs, exit/stop reason, failed stage and relevant process/tool state. Preserve useful evidence. Distinguish application defects, tooling failures, missing prerequisites and unknown outcomes; do not invent a root cause.
2. Form a specific hypothesis and use the smallest safe diagnostic to test it. For a stalled build, identify the unfinished task and inspect or rerun that task alone with useful output rather than restarting the whole build blindly.
3. Apply the smallest supported correction or documented fallback, then retry the affected step and verify its result. Record what changed and why it addresses the evidence. A retry must test a concrete hypothesis or follow a verified correction; repeating an unchanged attempt is not recovery.
4. Keep attempts and waits bounded. Increase a timeout only with evidence of legitimate progress or a known expected duration, never merely to hide a stall. Do not manufacture monitor progress, spin indefinitely, or build recovery infrastructure for a one-off failure.
5. Preserve authorization, resource ownership and specialized fail-closed limits. Check the actual outcome before retrying any operation with possible side effects; never replay an uncertain write, submission, paid action or destructive operation. Do not bypass consent, credentials, helper boundaries or explicit refusals.
6. Continue diagnosis, safe recovery and independent authorized work without asking the user to approve already-authorized actions. Keep the task active while doing that work; use blocked when its next step genuinely depends on something unavailable, not merely because a previous attempt failed.
7. Before stopping with incomplete verification, establish the concrete blocker: evidence inspected, causes confirmed or still unknown, recovery attempted, safe alternatives evaluated, and the exact dependency or condition needed to resume. If no supported safe path remains, report that limit honestly; neither claim success nor promise guaranteed root-cause discovery. A bare timeout or attempt count is not enough.

## Files

Use repository-relative `var/`, never the system `/var/`. Read the current session ID from the agent's own shell tool:

```bash
printf '%s\n' "$PI_SESSION_ID"
```

Use the full value as `sessionId`, not a Herdr pane ID, an invented agent name, or an inherited parent identity. Require a nonempty single directory component matching `[A-Za-z0-9][A-Za-z0-9_-]*`, and real tool-returned `W<number>` / `T<number>` IDs. If identity is missing or unsafe, stop and report the blocker; do not guess, truncate, or silently sanitize it.

The root agent's task directory is:

```text
var/<sessionId>/<workId>/<taskId>/
```

A delegated agent uses the exact parent task directory supplied in its assignment as `parentTaskDir`, then appends its own session-local IDs:

```text
<parentTaskDir>/<childSessionId>/<childWorkId>/<childTaskId>/
```

Apply this recursively at every allowed delegation depth. Resolve paths against the target repository root and keep resolved destinations, including symlinks, inside that repository's `var/`. Record the canonical artifact directory and any parent session/Work/Task IDs in `taskInfo`; pass them unchanged in handoffs and return them with results. On resume, verify that the recorded directory belongs to the current assignment before reusing it. Session branches can restore different tracking records, so matching numeric IDs alone do not authorize overwriting existing artifacts.

Create directories only when artifacts are useful. Feature names belong in descriptions, not path selection. Switching tasks switches to that task's directory. Keep shared plans and DAGs in the coordinating task's directory and link them from other tasks rather than duplicating them. Preserve existing feature-named artifacts; do not move or reinterpret them without explicit migration approval. Specialized skills keep their safety and file-format contracts; if a helper requires an incompatible legacy path, report the incompatibility rather than inventing unsupported arguments or silently reverting to a feature-named directory.

Use only the files that help, normally:

- `plan.md` — goal, constraints, affected areas, risks, and a short checklist;
- `dag.md` — Todo-linked task dependencies and assignments for substantial multi-area work only;
- `progress.md` — current status, delegated outcomes, and blockers;
- `summary.md` — changed files, verification, review result, and user test steps.

Edit these files directly and keep their contents readable.

## Workflow

1. Establish session identity, real Work/Task IDs, and the canonical task artifact directory. Write a short plan and checklist when useful; a small task needs only a concise plan.
2. Read project instructions, matching flow documents, current behavior, and applicable decision files.
3. Identify the owning boundary, acceptance criteria, edge cases, compatibility concerns, and rollback risk. Before non-trivial interface changes, new abstractions, or responsibility restructuring, read the global `codebase-design` skill fully and record its scaled design contract in `plan.md`. Reuse approved design decisions rather than reopening them without new evidence; a straightforward local fix needs only a brief ownership/contract check.
4. Record each task's `self` or `delegate` decision and reason in `taskInfo`. For substantial multi-area work, map outcomes and dependencies in `dag.md` before assigning any coding agents; follow the DAG workflow below. For small or tightly coupled work, skip the DAG; the recorded ownership reason is sufficient.
5. Execute only the authorized assignment through its owning specialized skill, follow ready DAG nodes when one exists, and keep the checklist current. Change production files only when implementation is authorized.
6. Inspect the combined change for overlapping or conflicting edits.
7. Run only checks allowed by the user and the owning skill. For implementation, applicable non-unit checks include formatting, linting, type checking, builds, or schema validation. Run unit tests only when the latest user request explicitly allows them.
8. Prepare exact user-owned live test steps when needed.
9. Review directly for simple changes. Use `agent-review` for complicated, risky, broad, uncertain, or explicitly requested review work.
10. Write the final summary and report the outcome.

## DAG and Todo workflow

For substantial multi-area work, the parent creates one Todo under the current Work for each concrete DAG node, including a final integration/verification node. Write `dag.md` in the working folder before dispatch. Use a small table with **Todo ID, outcome, dependency Todo IDs, owner, owned files/boundary, and status**; put acceptance criteria and important context in each Todo's `taskInfo`. Check that every dependency exists, the graph has no cycles, and parallel coding nodes have non-overlapping ownership. Use real IDs returned by the tracking tools; never invent Work or Todo IDs. If tracking tools are unavailable, do not dispatch delegated work.

A node is ready only when every dependency is **verified completed**. Assign ready, independent nodes to the parent or Herdr Pi agents; start dependent nodes only after their prerequisites are checked. Give each worker its node's outcome, context, owned and forbidden files, acceptance criteria, allowed checks, and report format (changed files, checks, blockers). Do not edit worker-owned files concurrently. Keep shared interfaces and tightly coupled edits with one owner; use the global `herdr` skill for agent lifecycle, not a new script or worktree.

The parent owns the DAG and its session's Todos; workers do not update the parent's session records. Each worker creates or resumes its own session-local Work and Todos before assigned work, records the parent assignment in its details, and returns its local IDs with its results. IDs are session-scoped, so do not assume a parent's IDs identify records in a worker's session. Mark a node active in both places when work starts. Read the complete worker result and actual changed files before marking its Todo **and** DAG row completed; a worker's claim of completion alone does not unblock dependents. For partial or failed work, mark both blocked, mark dependent Todos blocked with their prerequisites and resume conditions, and update the plan or assignment before resuming. When dependencies or scope change, update `dag.md` and the affected Todo details together. Finish the integration node only after the parent reviews the combined diff and runs applicable checks. `progress.md` may record extra notes, but must not be a competing task list.

## Self or delegate

Evaluate each task before execution and whenever its scope changes. Record `owner: self` or `owner: delegate` and a brief evidence-based reason in `taskInfo`; use existing fields, not a second tracking system.

Delegate only when all of these hold:

- The bounded outcome, acceptance criteria, and allowed checks are clear.
- File ownership or read-only investigation scope can be isolated without concurrent conflicting edits.
- Required inputs and shared contracts are ready; prerequisites are verified.
- Useful parallel work or independent expertise outweighs startup, context transfer, monitoring, and integration costs.
- The owning skill permits delegation and required tracking and monitor tools are available.

Otherwise keep the task with the current agent. Small straightforward changes, tightly coupled edits, shared-interface design, and work whose boundaries cost more to explain than to complete normally stay with one owner. Size or risk alone does not justify parallel coding; an independent review may still be appropriate. Do not use arbitrary file-count, worker-count, or delegation-depth thresholds. Every coding child applies the same decision rule when further delegation is allowed, while its parent retains responsibility for integration and verification.

## Delegation

Every delegated Core agent must have its own visible Task-ID-named Herdr app tab and a continuous monitor before prompting. Follow global herdr and prefer AgentCreate with the parent Work/Task IDs, canonical taskDir, explicit model flags and onSignal/optional onDone. It verifies the real HC_TERMINAL_ID parent and native Pi readiness, starts Pi through hc, verifies its dedicated app tab, registers pi-loop-monitor with hcTerminalId, and returns terminalId/tabId/monitorId plus a prepared assignment without sending it. Confirm MonitorList shows Core subscription ready, then AgentSend that assignment; do not add another monitor. onSignal means worker state changed; onDone means the subscriber ended, not task completion. Use the herdr skill's manual Core bootstrap only for capabilities missing from installed tools; never fall back to the retired herdr TUI CLI or fake HERDR_ENV. If continuous monitoring is unavailable/not ready, block dispatch; do not substitute one-shot waits or unmonitored workers. Keep the same subscription across working/blocked/idle/done and follow-ups. Read complete results and actual changes before accepting work, import measured timing, then close only owned terminalId/monitorId resources when no further work/signals are needed. Core owns processes, the app owns visible tabs, and pi-loop-monitor owns wakes; no private registry or recovery runtime is added.

When delegation is useful, require each worker to read and follow this skill for its local Work, then the specialized skill that owns its assignment. Give it one bounded outcome, owned files or boundaries, acceptance criteria, relevant inputs, forbidden actions, expected output, parent session/Work/Task IDs, and the exact parent task artifact directory. Require the child to obtain its own session ID and tracking IDs and return its canonical nested artifact directory. Give every Core worker its own visible Herdr app tab named exactly with the parent's delegated Task ID, such as `T34`, without descriptions or other prefixes; the tab label does not replace worker-local identity or tracking. Set the shared contract before parallel edits and avoid overlapping ownership. Use the global `herdr` skill when Core-hosted Pi agents are selected. Before launching subagents, read and follow the globally installed `model-routing-policy` skill for model, thinking level, and Fast settings. Keep routing defaults only in that skill. Coding agents may delegate further when useful and remain responsible for their children's monitoring, verified results, integration, and cleanup. The parent integrates and reads the actual combined changes and reruns affected checks.

Every subagent assignment must require the worker to call `WorkList` and `TodoList`, create or resume a local Work with `WorkCreate`/`WorkUpdate`, and create or update its Todos with `TodoCreate`/`TodoUpdate` before doing assigned work. It must have a real `workId` and an active `taskId` for the current step, keep those records current, and report its IDs, checks, results, and blockers. This applies at every delegation depth. If tracking tools or IDs are unavailable, the worker must report the blocker and not begin assigned work; a parent-owned Todo or a Markdown checklist is not a substitute. Keep `/ask` and `/btw` side conversations outside tracking.

## Final response

Lead with complete or blocked. Summarize the session/Work/Task IDs and canonical artifact paths, authorized outcome, actual files changed if any, checks run, user test steps, review result, remaining risks, delegated work status, and whether any commit or deployment occurred.
