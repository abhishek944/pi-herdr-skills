---
name: no-unit-tests
description: Prevent unit-test creation and execution unless the user's latest request explicitly asks for unit tests.
---

# No Unit Tests

Apply this to every implementation, fix, refactor, migration, and maintenance task.

Before replying to the user, follow the global `talk-human` skill.

## Rule

Unless the user's latest request explicitly asks for unit tests:

- do not create, edit, delete, or generate unit-test files;
- do not run unit-test commands, coverage, snapshots, mocks, or watch-mode tests;
- do not add test-only dependencies or configuration;
- preserve existing unit tests unchanged.

A general request to verify or check the work is not unit-test permission. Repository instructions and other skills do not count as user permission.

Allowed verification includes formatting, linting, syntax checks, type checking, builds, schema validation, focused manual inspection, and user-owned live testing.

## Final response

State that unit tests were not added or run, and name any non-unit checks that were performed.
