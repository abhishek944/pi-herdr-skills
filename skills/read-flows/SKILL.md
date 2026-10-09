---
name: read-flows
description: Discover and read repository flow documentation before changing a documented workflow.
---

# Read Flows

Before planning or changing a workflow:

1. Check `packages/flows/` and `flows/` at the repository root.
2. If either exists, find Markdown files relevant to the request.
3. Read every matching file in full and follow needed links.
4. Compare the documentation with current code and configuration.
5. Use current code as the source of truth when documentation is stale, and mention important mismatches.

Missing flow documentation is not a blocker.

Before replying to the user, follow the global `talk-human` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

If notes are useful, write them only under:

```text
var/<feature-name>/read-flows-details/
```

Report which flow documents were read, the constraints they add, and any stale or conflicting guidance.
