---
name: agent-review
description: "Independent review of repository changes when risk, complexity, uncertainty, or an explicit user request justifies it."
compatibility: Requires a Git repository and support for independent reviewers.
---

# Agent Review

Review changes without editing them. Use this skill when the user asks for review or when an implementation has meaningful risk, breadth, or uncertainty. Skip it for straightforward changes that can be checked confidently by direct inspection.

Before replying to the user, follow the global `talk-human` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read the original user request and explicit decisions before the implementation plan, then repository instructions, the current diff, nearby callers and relevant documentation. Flag unnecessary scope; an implementer's plan is not independent authorization for its guarantees.
- For changes to interfaces, abstractions, or module responsibilities, read the global `codebase-design` skill fully and give reviewers the agreed design contract. Apply only checks relevant to the changed behavior and actual callers, not the entire checklist as new acceptance criteria. Review does not reopen approved design decisions without a concrete defect or authorize test changes.
- Reviewers are read-only. They do not edit files, run tests, or launch more agents.
- Preserve unrelated work. Never commit, push, publish, or deploy.
- When independent review is warranted, default to one reviewer covering the relevant lenses below. Add a specialist only for a named, distinct material risk whose benefit outweighs coordination cost. These are lenses, not three mandatory agents. Do not increase reviewer count merely because the implementation introduced unnecessary complexity.
- Verify every finding against the current files and supported behavior before accepting it. A blocking finding must identify a violated user requirement or existing contract, a concrete supported failure scenario, code evidence, and the smallest complete fix. An executable reproduction is not required when the failure follows clearly from the code. Severity labels alone do not make a finding blocking.
- Separate required fixes from optional cleanup/hardening and out-of-scope scenarios. Optional suggestions must not block completion or become implementation tasks without user authorization. Omit speculative improvements rather than create a backlog for the implementer.
- Before recommending more machinery, consider removing the unnecessary guarantee or abstraction that caused the finding. Preserve required behavior, security, cancellation handling and data-loss protection; simplification is not permission to ignore real bugs.

## Review lenses

- **Correctness/safety:** Does the change deliver the original request without breaking required behavior, authorization, cancellation handling, or data-loss protection? Do not invent new guarantees for hypothetical failures.
- **Architecture/integration:** Do affected callers still work, and does behavior stay with its existing owner? Look first for unnecessary machinery that can be removed. Do not redesign working code or add abstractions for future flexibility.
- **Regression:** Trace existing supported behavior through changed code and affected callers. Do not turn a feature review into a repository-wide compatibility audit or require support for new scenarios.

## Workflow

1. Define the review base, target and scope from the original request and explicit decisions, including non-goals. Include that scope in reviewer assignments, not only the implementer's plan.
2. Read the decision trees, visual contracts and original evidence at the exact paths supplied by the parent or caller. Do not reconstruct interview paths from a feature name, branch label or another task's numeric IDs.
3. Before launching an independent read-only reviewer, read and follow the globally installed `model-routing-policy` skill for model, thinking level, and Fast settings. Keep routing defaults only in that skill. Use one reviewer by default; record the distinct risk before adding a specialist.
4. Include this contract in each assignment: "Review whether this change delivers the original request and preserves affected existing behavior. Report concrete defects, not opportunities to improve the system. Prefer deletion or a local correction over new machinery. No actionable findings is a valid result." Ask for severity, the violated requirement or contract, supported failure scenario, code evidence, scope classification, and the smallest complete recommendation. Do not invent findings to fill a review.
5. Combine duplicates by root cause.
6. Accept, reject, or leave each finding unresolved with a short reason. Reviewer output is advice, not authorization to expand the task. Only accepted in-scope defects require fixes; keep optional suggestions outside the task unless the user requests them.
7. After fixes, recheck accepted defects and directly affected code when warranted. Do not restart the full review or reopen settled design decisions unless the fixes introduce a new material risk. Stop when accepted defects are resolved and allowed verification is complete.

## Files

Follow the global `implement` skill for canonical task ownership. Retain reports only inside the reviewer's own task directory (`taskDir`); a delegated reviewer appends its own session/Work/Task IDs below the exact supplied parent task directory. Reuse the current task when review is part of that assignment, and establish real tracking before standalone work. Never construct an output root from a feature name.

```text
<taskDir>/summary.md
```

A single `summary.md` is normally enough. Use separate lens reports only when distinct specialist reviews justify them. Do not create launch logs, state files, checksums, or machine-only evidence.

## Final response

State the reviewed scope, accepted and rejected findings, unresolved risks, checks performed by the parent, and the final verdict: `clean`, `pass`, or `blocked`.
