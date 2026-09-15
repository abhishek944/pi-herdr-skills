---
name: discuss
description: "Read-only repository investigation, debugging, root-cause analysis, and planning before implementation."
compatibility: Requires a repository checkout and normal code-reading tools.
---

# Discuss

Investigate without changing project files. Leave this mode before implementing a fix.

Before replying to the user, follow the global `plainspoken-responses` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read repository instructions and discover the real structure before forming conclusions.
- Treat production files as read-only.
- Use the local environment by default. Shared or production systems require explicit permission.
- Never expose secrets, credentials, private data, or raw environment values.
- Use official sources for third-party behavior.
- Separate confirmed facts, likely explanations, open hypotheses, and blocked checks.
- Propose a fix at the boundary that owns the behavior; avoid one-off workarounds.

## Workflow

1. Restate the question and known evidence.
2. Trace the relevant callers, configuration, storage, integrations, and outputs.
3. Rank plausible causes and identify what would distinguish them.
4. Run only safe, bounded, non-mutating checks.
5. Use separate read-only specialists for logs or databases when those systems are involved; minimize and redact their results.
6. Confirm the leading cause when possible and look for sibling instances.
7. Propose the fix, verification plan, risks, and rollout concerns without applying it.

## Files

When investigation notes are useful, write only under:

```text
var/<feature-name>/discuss-details/
```

Suggested files are `evidence.md` and `proposed-fix.md`. Do not create machine state or launch logs.

## Final response

Give the summary, evidence, root cause confidence, proposed fix, verification plan, related candidates, open questions, and next step.
