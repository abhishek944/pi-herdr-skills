---
name: commit-and-merge
description: "Manual-invoke only. Commit requested repository changes and merge into the default branch, automatically handling version bumps and local release tags according to established repository conventions without a separate user request."
compatibility: Requires a Git repository.
disable-model-invocation: true
---

# Commit and Merge

Use only when the user explicitly asks to commit and merge or invokes this skill. That invocation authorizes applicable local version bumps and release tags as part of the workflow; do not require a separate request or confirmation for either. Honor explicit user instructions to skip them. Pushing, publishing, and other remote operations still require permission.

Before replying to the user, follow the global `talk-human` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read repository instructions, status, diffs, branch information, and recent commit style first.
- Commit only the requested project work.
- Leave temporary artifacts and unrelated user changes untouched.
- Ask before excluding an ambiguous changed file.
- Never discard work, rewrite history, skip hooks, force-push, or contact a remote without permission.
- Do not guess through merge conflicts.
- Handle version bumps and release tags independently: use repository instructions, release scripts/configuration, version files, and existing release tags as evidence. A version field alone does not establish a bump policy, and unrelated tags do not establish release tagging.
- Skip version bumping or release tagging when its convention is absent; never introduce either just for this workflow. If an existing convention leaves the release scope, next version, or tag unclear, ask before changing anything.
- Respect automation-owned releases: do not duplicate bumps or tags performed by CI or release tools. Inspect release commands for automatic commits, tags, publishing, or remote access before running them; existing permission rules still apply.
- Never replace, move, or delete an existing tag. Keep tags local unless pushing is explicitly authorized.

## Workflow

1. Identify the requested commit set and the repository's actual default branch. Inspect existing versioning and release-tag conventions; determine which steps apply, which are skipped, and which are automation-owned.
2. Automatically perform any version bump that is not automation-owned when the established convention calls for it; do not wait for the user to request a bump. Choose the next version using that policy and the requested changes, or ask only if the policy or release scope is unclear. Use the existing bump mechanism and update only the required version files, lockfiles, and release notes. Include these changes in the requested commit set. If the repository requires a different release order, follow it rather than inventing one.
3. Recheck the staged diff, including any version changes, and run only required checks.
4. Commit with a concise message matching repository style.
5. If already on the default branch, no merge is needed. Otherwise merge safely into the default branch without pulling or rebasing unless authorized.
6. If conflicts or required checks fail, stop, explain them, and wait for the user's decision; do not create a release tag.
7. After a successful merge (or commit on the default branch), automatically create the local release tag when the established convention calls for a tag that is not automation-owned; do not wait for a separate user request or confirmation. Verify that the final commit contains the intended release version, use the existing tag name, type, signing, and target conventions, and check for a local name collision. If tag availability requires contacting a remote, ask permission first. Stop on a collision or tag failure; do not undo the successful commit or merge, and report the remaining step.

## Files

If a written record is useful, write only under:

```text
var/<feature-name>/commit-and-merge-details/
```

Do not commit this folder unless the repository explicitly tracks `var/`.

## Final response

Report the commit identifier and message, merge result, version change and tag name/target (or why each was skipped or deferred to automation), checks run, files left uncommitted, and any next action. State whether the tag is local or was explicitly pushed.
