---
name: commit-and-merge
description: "Manual-invoke only. Commit requested repository changes and merge the current branch into the default branch."
compatibility: Requires a Git repository.
disable-model-invocation: true
---

# Commit and Merge

Use only when the user explicitly asks to commit and merge.

Before replying to the user, follow the global `plainspoken-responses` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read repository instructions, status, diffs, branch information, and recent commit style first.
- Commit only the requested project work.
- Leave temporary artifacts and unrelated user changes untouched.
- Ask before excluding an ambiguous changed file.
- Never discard work, rewrite history, skip hooks, force-push, or contact a remote without permission.
- Do not guess through merge conflicts.

## Workflow

1. Identify the requested commit set and the repository's actual default branch.
2. Recheck the staged diff and run only required checks.
3. Commit with a concise message matching repository style.
4. If already on the default branch, report that no merge is needed.
5. Otherwise merge safely into the default branch without pulling or rebasing unless authorized.
6. If conflicts occur, stop, explain them, and wait for the user's decision.

## Files

If a written record is useful, write only under:

```text
var/<feature-name>/commit-and-merge-details/
```

Do not commit this folder unless the repository explicitly tracks `var/`.

## Final response

Report the commit identifier and message, merge result, checks run, files left uncommitted, and any next action.
