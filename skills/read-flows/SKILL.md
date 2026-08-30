---
name: read-flows
description: Discover and read repository flow documentation when it is available. Check packages/flows/ and flows/ before planning or changing a documented workflow; continue normally when neither location exists or no flow matches.
---

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless repository instructions say otherwise.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# Read Flows

Use existing flow documentation as repository context when it is available. Do not require a repository to have flow docs.

## Discovery

1. Check for `packages/flows/` and `flows/` at the repository root.
2. Inspect whichever of those directories exist. If both exist, inspect both. Recursively list their Markdown files.
3. Match docs to the requested work using filenames, headings, and relevant repository terms.
4. Read every matching document in full before planning or editing the covered workflow.
5. Follow links to other flow documents when they are needed to understand the complete path.

If neither directory exists, or no document matches, state that briefly and continue with normal repository inspection. Missing flow documentation is not a blocker.

## How to use the docs

- Extract relevant components, files, routes, configuration, sequence steps, checks, and known pitfalls.
- Cross-check important claims against the current repository. Live code and configuration define current behavior when documentation is stale.
- Call out any mismatch that affects the requested work.
- Follow repository rules for updating stale documentation when the current task includes implementation. This skill itself does not require creating a flow document.
- Do not expose secrets or internal identifiers from flow docs in user-facing replies.

## Result

Return a short summary containing:

- flow documents read, or that none were available or relevant;
- constraints and affected areas;
- important sequence or safety requirements;
- stale or conflicting documentation that needs attention.
