---
name: implement
description: "Implement or fix repository changes with a simple written plan, focused execution, verification, and proportionate review."
compatibility: Requires a repository checkout and standard file and shell tools.
---

# Implement

Make the requested production change at the boundary that owns the behavior. Keep the process small, readable, and easy to resume.

Before replying to the user, follow the global `plainspoken-responses` skill. Also follow `no-unit-tests` unless the user's latest request explicitly asks for unit tests.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read repository instructions and relevant flow or architecture documentation first.
- Preserve unrelated changes and existing staged work.
- Do not commit, push, publish, or deploy unless explicitly asked.
- Do not hard-code an answer for one example or bypass the owning boundary.
- Use resolved `grill-me` and `ui-ux-grill-me` decisions as requirements; deferred decisions are not requirements.
- Delegate only independent outcomes when doing so clearly improves speed or confidence.
- Leave live interactive end-to-end testing to the user unless they explicitly ask the agent to run it.

## Files

Create one simple working folder:

```text
var/<feature-name>/implement-details/
```

Use only the files that help, normally:

- `plan.md` — goal, constraints, affected areas, risks, and a short checklist;
- `progress.md` — current status, delegated outcomes, and blockers;
- `summary.md` — changed files, verification, review result, and user test steps.

Edit these files directly and keep their contents readable.

## Workflow

1. Pick a stable feature name and write a short plan and checklist.
2. Read project instructions, matching flow documents, current behavior, and applicable decision files.
3. Identify the owning boundary, acceptance criteria, edge cases, compatibility concerns, and rollback risk.
4. Decide whether to work directly or delegate truly independent pieces.
5. Implement only the requested scope and keep the checklist current.
6. Inspect the combined change for overlapping or conflicting edits.
7. Run applicable non-unit checks such as formatting, linting, type checking, builds, or schema validation. Run unit tests only when the latest user request explicitly allows them.
8. Prepare exact user-owned live test steps when needed.
9. Review directly for simple changes. Use `agent-review` for complicated, risky, broad, uncertain, or explicitly requested review work.
10. Write the final summary and report the outcome.

## Delegation

When delegation is useful, give each agent one bounded outcome, acceptance criteria, relevant inputs, forbidden actions, and expected output. Use the global `model-routing-policy` and `herdr` skills when Herdr-hosted Pi agents are selected. Children do not launch more agents unless the parent explicitly permits it. The parent reads the actual combined changes and reruns affected checks.

## Final response

Lead with complete or blocked. Summarize the main changes, actual files changed, checks run, user test steps, review result, remaining risks, delegated work status, and whether any commit or deployment occurred.
