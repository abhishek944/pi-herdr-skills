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
- For substantial work across distinct areas, look for bounded coding tasks to delegate before implementing. Delegate independent outcomes when doing so clearly improves speed or confidence; keep tightly coupled changes with one owner when splitting adds coordination risk. A read-only review is not a substitute for considering implementation delegation.
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
4. For multi-area work, identify candidate independent coding pieces; decide what to delegate and record the reason for delegating or keeping the work direct in `plan.md` or `progress.md`.
5. Implement only the requested scope and keep the checklist current.
6. Inspect the combined change for overlapping or conflicting edits.
7. Run applicable non-unit checks such as formatting, linting, type checking, builds, or schema validation. Run unit tests only when the latest user request explicitly allows them.
8. Prepare exact user-owned live test steps when needed.
9. Review directly for simple changes. Use `agent-review` for complicated, risky, broad, uncertain, or explicitly requested review work.
10. Write the final summary and report the outcome.

## Delegation

When delegation is useful, give each coding agent one bounded outcome, owned files or boundaries, acceptance criteria, relevant inputs, forbidden actions, and expected output. Set the shared contract before parallel edits and avoid overlapping ownership. Use the global `herdr` skill when Herdr-hosted Pi agents are selected. As optional defaults, prefer `openai-codex/gpt-6-luna` at `max` thinking with `--fast` for implementation agents and `openai-codex/gpt-6-sol` at `high` thinking without `--fast` for review agents. If the current user requests another model, use their choice instead; honor requested thinking or speed settings. These suggestions never require a model catalog or override an explicit user choice. Children do not launch more agents unless the parent explicitly permits it. The parent integrates and reads the actual combined changes and reruns affected checks.

## Final response

Lead with complete or blocked. Summarize the main changes, actual files changed, checks run, user test steps, review result, remaining risks, delegated work status, and whether any commit or deployment occurred.
