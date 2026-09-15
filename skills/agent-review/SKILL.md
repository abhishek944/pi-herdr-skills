---
name: agent-review
description: "Independent review of repository changes when risk, complexity, uncertainty, or an explicit user request justifies it."
compatibility: Requires a Git repository and support for independent reviewers.
---

# Agent Review

Review changes without editing them. Use this skill when the user asks for review or when an implementation has meaningful risk, breadth, or uncertainty. Skip it for straightforward changes that can be checked confidently by direct inspection.

Before replying to the user, follow the global `plainspoken-responses` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read repository instructions, the current diff, nearby callers, and relevant documentation.
- Reviewers are read-only. They do not edit files, run tests, or launch more agents.
- Preserve unrelated work. Never commit, push, publish, or deploy.
- Use three independent perspectives for complicated work: correctness and safety, architecture and integration, and regression risk.
- A simple review may use one independent reviewer.
- Verify every finding against the current files before accepting it.

## Workflow

1. Define the review base, target, and scope.
2. Read any applicable decisions in `var/<feature-name>/grill-me-details/` and `var/<feature-name>/ui-ux-grill-me-details/`.
3. Launch independent read-only reviewers when available and useful.
4. Ask for actionable findings with severity, evidence, and a clear recommendation.
5. Combine duplicates by root cause.
6. Accept, reject, or leave each finding unresolved with a short reason.
7. After fixes, review the changed areas again when the risk warrants it.

## Files

When reports should be retained, write only under:

```text
var/<feature-name>/agent-review-details/
```

Suggested files are `correctness.md`, `architecture.md`, `regression.md`, and `summary.md`. Do not create launch logs, state files, checksums, or machine-only evidence.

## Final response

State the reviewed scope, accepted and rejected findings, unresolved risks, checks performed by the parent, and the final verdict: `clean`, `pass`, or `blocked`.
