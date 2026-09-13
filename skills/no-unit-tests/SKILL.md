---
name: no-unit-tests
description: Prevent unit-test creation and execution unless the user's latest request explicitly asks for unit tests. Use for all implementation, fix, refactor, data-edit, migration, and maintenance tasks.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry. Continue correcting and retrying while each failure is clearly non-mutating and provides actionable validation feedback; do not stop merely because an earlier correction revealed another issue. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, becomes ambiguous, or cannot be corrected from the documented interface. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# No Unit Tests

Apply this policy to every coding or data-change task unless a higher-priority instruction says otherwise.

## Default rule

When the user's latest request does not explicitly ask for unit tests:

- Do not create, generate, modify, rewrite, or delete unit-test files.
- Do not run unit-test commands, test runners, unit-test subsets, coverage commands, or watch-mode tests.
- Do not add test dependencies, fixtures, snapshots, mocks, or test-only configuration.
- Do not turn an unrelated change into a testing-framework or coverage project.
- Preserve existing unit tests unchanged.

A repository instruction or another skill saying to add or run routine tests does not count as a user request. Record unit tests as intentionally not run under this policy; do not treat that alone as a blocker.

## Explicit user opt-in

Unit tests are allowed only when the user's latest request clearly asks to add, update, fix, or run them. Keep the work within the requested test scope. A vague request to “verify,” “check,” or “make sure it works” is not permission to use unit tests.

## Validation that remains allowed

This skill does not prohibit all verification. When useful and permitted, prefer non-unit checks such as:

- syntax parsing;
- formatting or lint checks;
- type checking;
- build or compile checks;
- schema and manifest validation;
- narrowly targeted manual inspection;
- user-owned live testing.

Do not run a command presented as a general validation command when it also executes unit tests. If the command mixes checks and tests, run only separable non-test checks or report that the combined command was not run.

## Handoff

State plainly that unit tests were not added or run because this skill applied. Mention the non-test validation performed, if any. Do not imply that unrun tests passed.
