---
name: commit-and-merge
description: "Manual-invoke only. Commit the repository's real changes while leaving temporary artifacts uncommitted, then merge the current branch into the repository's default branch with user-guided conflict resolution. Never run unless the user explicitly asks to commit and merge."
compatibility: Requires a Git repository.
disable-model-invocation: true
---

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless the project says otherwise.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# Commit and Merge

Use only when the user explicitly asks to commit current work and merge it.

## Core rules

1. Read the repository's instructions and recent commit history before staging.
2. Commit all real project changes that belong to the requested work.
3. Leave logs, caches, generated previews, recordings, scratch scripts, and other temporary artifacts uncommitted unless the repository intentionally tracks them.
4. Ask before excluding any ambiguous file.
5. Never discard changes, rewrite history, skip hooks, force-push, or push at all unless the user explicitly asks.
6. Do not start unrelated testing during this workflow. Use existing verification evidence and allow normal commit hooks to run.
7. Preserve unrelated user changes and staged work.

## Procedure

### 1. Inspect

Run read-only Git checks:

- working-tree status;
- staged and unstaged diffs;
- diff summary;
- current branch and worktrees;
- recent commit messages;
- configured default branch, preferring the remote default and then common local names.

Read repository instructions that govern generated files, tests, commits, or release branches.

### 2. Choose the commit set

Classify every changed file as:

- requested project work;
- unrelated user work;
- temporary artifact;
- ambiguous.

Stage only requested project work. Do not disturb unrelated staged files. If the intended commit cannot be isolated safely, stop and ask the user.

### 3. Verify and commit

1. Recheck the staged diff.
2. Run only checks required by the repository or the user's request.
3. Draft a concise message that matches recent repository style.
4. Commit without bypassing hooks.
5. If hooks modify files, inspect those changes before staging them. Do not amend unless it is safe and clearly part of this same commit attempt.

### 4. Merge into the default branch

1. Determine the repository's actual default branch; do not assume it is named `main`.
2. If the current branch is already the default branch, report that no merge is needed.
3. If the default branch is checked out in another clean worktree, merge there.
4. Otherwise switch safely, update according to repository policy, and merge the committed branch.
5. Do not pull, rebase, or contact a remote when the repository or user has not authorized it.

## Conflicts

If a merge conflict occurs:

1. Stop and list the conflicted files.
2. Explain each behavioral conflict in plain language.
3. Recommend options when useful, but wait for the user's explicit decision.
4. Apply only the approved resolution.
5. Run the checks relevant to the resolved files, then finish the merge.

Never guess through a conflict or use a destructive command to make it disappear.

## Final report

Report:

- commit identifier and message;
- whether and where it was merged;
- checks that ran;
- files intentionally left uncommitted;
- any remaining action the user must take.
