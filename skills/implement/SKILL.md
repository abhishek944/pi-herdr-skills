---
name: implement
description: "Implement or fix repository changes with a simple written plan, focused execution, verification, and proportionate review."
compatibility: Requires a repository checkout and standard file and shell tools.
---

# Implement

Make the requested production change at the boundary that owns the behavior. Keep the process small, readable, and easy to resume.

Before replying to the user, follow the global `talk-human` skill. Also follow `no-unit-tests` unless the user's latest request explicitly asks for unit tests.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` for long-running background commands and mandatory continuous Herdr worker subscriptions; use `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read repository instructions and relevant flow or architecture documentation first.
- Preserve unrelated changes and existing staged work.
- Do not commit, push, publish, or deploy unless explicitly asked.
- Do not hard-code an answer for one example or bypass the owning boundary.
- Use resolved `grill-me` and `ui-ux-grill-me` decisions as requirements; deferred decisions are not requirements.
- For substantial work across distinct areas, look for bounded coding tasks to delegate before implementing. Delegate independent outcomes when doing so clearly improves speed or confidence; keep tightly coupled changes with one owner when splitting adds coordination risk. A read-only review is not a substitute for considering implementation delegation.
- Leave live interactive end-to-end testing to the user unless they explicitly ask the agent to run it.

## Files

Create one simple working folder:

```text
var/<feature-name>/implement-details/
```

Use only the files that help, normally:

- `plan.md` — goal, constraints, affected areas, risks, and a short checklist;
- `dag.md` — Todo-linked task dependencies and assignments for substantial multi-area work only;
- `progress.md` — current status, delegated outcomes, and blockers;
- `summary.md` — changed files, verification, review result, and user test steps.

Edit these files directly and keep their contents readable.

## Workflow

1. Pick a stable feature name and write a short plan and checklist.
2. Read project instructions, matching flow documents, current behavior, and applicable decision files.
3. Identify the owning boundary, acceptance criteria, edge cases, compatibility concerns, and rollback risk.
4. For substantial multi-area work, map outcomes and dependencies in `dag.md` before assigning any coding agents; follow the DAG workflow below. For small or tightly coupled work, skip the DAG and record why direct work is simpler in `plan.md`.
5. Implement only the requested scope, follow ready DAG nodes when one exists, and keep the checklist current.
6. Inspect the combined change for overlapping or conflicting edits.
7. Run applicable non-unit checks such as formatting, linting, type checking, builds, or schema validation. Run unit tests only when the latest user request explicitly allows them.
8. Prepare exact user-owned live test steps when needed.
9. Review directly for simple changes. Use `agent-review` for complicated, risky, broad, uncertain, or explicitly requested review work.
10. Write the final summary and report the outcome.

## DAG and Todo workflow

For substantial multi-area work, the parent creates one Todo under the current Work for each concrete DAG node, including a final integration/verification node. Write `dag.md` in the working folder before dispatch. Use a small table with **Todo ID, outcome, dependency Todo IDs, owner, owned files/boundary, and status**; put acceptance criteria and important context in each Todo's `taskInfo`. Check that every dependency exists, the graph has no cycles, and parallel coding nodes have non-overlapping ownership. If Todo tools are unavailable, use stable local node IDs in the same table instead; never invent Todo IDs.

A node is ready only when every dependency is **verified completed**. Assign ready, independent nodes to the parent or Herdr Pi agents; start dependent nodes only after their prerequisites are checked. Give each worker its node's outcome, context, owned and forbidden files, acceptance criteria, allowed checks, and report format (changed files, checks, blockers). Do not edit worker-owned files concurrently. Keep shared interfaces and tightly coupled edits with one owner; use the global `herdr` skill for agent lifecycle, not a new script or worktree.

The parent owns the DAG and the session's Todos; workers do not update the parent's session records. Mark a node active in both places when work starts. Read the complete worker result and actual changed files before marking its Todo **and** DAG row completed; a worker's claim of completion alone does not unblock dependents. For partial or failed work, mark both blocked, keep dependents pending, and update the plan or assignment before resuming. When dependencies or scope change, update `dag.md` and the affected Todo details together. Finish the integration node only after the parent reviews the combined diff and runs applicable checks. `progress.md` may record extra notes, but must not be a competing task list.

## Delegation

Every delegated Herdr agent must have a continuous pane monitor before it is prompted. Follow the global `herdr` lifecycle: create `MonitorCreate` with the actual `herdrPaneId` and an `onSignal` wake, then confirm subscription readiness with `MonitorList`. If monitoring is unavailable or not ready, block dispatch; do not silently fall back to an unmonitored agent, a blocking `--wait`, or a one-shot monitored CLI wait. Keep the same subscription across working, blocked, idle, and done states, including follow-up prompts. The parent reads the complete result and actual changes before marking the Todo/DAG node complete, and stops its monitor when no further signals are needed.

When delegation is useful, give each coding agent one bounded outcome, owned files or boundaries, acceptance criteria, relevant inputs, forbidden actions, and expected output. Set the shared contract before parallel edits and avoid overlapping ownership. Use the global `herdr` skill when Herdr-hosted Pi agents are selected. Before launching subagents, read and follow the globally installed `model-routing-policy` skill for model, thinking level, and Fast settings. Keep routing defaults only in that skill. Children do not launch more agents unless the parent explicitly permits it. The parent integrates and reads the actual combined changes and reruns affected checks.

## Final response

Lead with complete or blocked. Summarize the main changes, actual files changed, checks run, user test steps, review result, remaining risks, delegated work status, and whether any commit or deployment occurred.
