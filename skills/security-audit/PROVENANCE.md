# Security audit provenance

- Upstream: https://github.com/cloudflare/security-audit-skill
- Revision: `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`
- Source directory: `skills/security-audit/`
- License: MIT; Copyright (c) 2025-2026 Cloudflare, Inc. The upstream license is bundled in `LICENSE`.

## Local adaptations

- Add a Pi integration section for existing tracking, delegation, model routing, read-only scope, communication, and unit-test permissions.
- Preserve upstream companion documents and schema. Adapt the zero-dependency coverage validator only for canonical task-path ownership; keep its bounds and safe-path checks.
- Omit upstream `validate-findings.test.cjs` and `validate-coverage-ledger.test.cjs`; this installation does not add or run unit tests.
- Full-audit output follows Pi coordination: the parent task directory is the run directory, each worker uses its canonical nested session/Work/Task root for `scratch/` and parent-promoted `artifacts/`, and every local ledger check records that root as `task_root`. The coverage validator enforces the canonical root shape and the `<task_root>/artifacts/` prefix. Historical external `~/security-audit-skill/**` and `agents/<agent-id>/**` artifacts are not moved, rewritten, or inferred. Guidance mode remains available without run artifacts.

Update from a reviewed pinned upstream revision, preserve the license, reapply the integration section and canonical task-path adaptation, refresh the added files' manifest checksums, and synchronize the skill to `~/.agents/skills/security-audit/`. Do not execute target code without the upstream sandbox controls.
