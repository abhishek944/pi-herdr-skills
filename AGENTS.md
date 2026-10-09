# Required global skill installation

Changes to this repository's skills are not complete until the changed or new skills are installed globally into `~/.agents/skills/` and the installed contents are verified against the repository.

- Install updated skills as part of the same task; do not wait for a separate installation request.
- Synchronization is bidirectional: edits to global skills managed by this repository must also be applied to their repository copies during the same task. Verify both copies match and update the changed files' checksums in `skills-manifest.json`.
- Preserve unrelated global skills and local modifications. Inspect differences and back up conflicting installed contents before replacement.
- Keep global installation scoped to the requested changes unless a full installation is requested.
- If installation is blocked, report the blocker rather than declaring the task complete.
- Remind the user to run `/reload` or restart Pi when needed to discover updated skills.
