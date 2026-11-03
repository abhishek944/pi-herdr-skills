# Grill-me decision tree

The conductor maintains this artifact in the owning canonical task directory: `var/<sessionId>/<workId>/<taskId>/decision-tree.md` for a root owner, or the nested delegated triple beneath the exact parent task directory for a delegated owner. Feature names, owner labels and branch labels are descriptive metadata only and never select a directory.

## DAG template

Create `dag.md` in the parent's task directory before questions. The parent owns it and the aggregate tree; each owner's canonical task directory contains its local tree and original responses.

```markdown
# Interview DAG — <parent label>

Parent task directory: `<taskDir>` (root owner directory or its delegated nested triple).

| Branch | Todo/local ID | Outcome / closure criteria | Dependencies | Level | Owner | Owner task directory | Status | Evidence |
| ------ | ------------- | -------------------------- | ------------ | ----- | ----- | -------------------- | ------ | -------- |
| <owner-label>:B1 | <actual ID> | <decision plus all follow-ups closed> | — | 1 | <owner label> | <canonical owner task directory> | pending | — |
| integrate-L1 | <actual ID> | Verify artifacts and reconcile level | <level-1 branches> | 1 | parent | <parent task directory> | pending | — |

## Level gates

- L1: <independent branches>; integration: <pending/complete/blocked>
- L2: <branches requiring verified L1 decisions>
```

Dependency IDs must exist and the graph must be acyclic. Keep readiness/status here, not in a second scheduler. A completed interview Todo records a verified disposition, not necessarily a resolved decision: a deferred prerequisite requires re-scoping or deferring downstream branches. Record every owner's exact task directory and display label from its assignment; the label qualifies branch IDs, while the directory locates the original evidence. Each owner records local parent-child links and reports discovered dependencies; only the parent updates shared DAG/Todos. Preserve qualified IDs and original paths during merge and handoff; never rebuild an owner path from a feature name, slug or label.

## Template

```markdown
# Decision tree — <owner label>

Owner task directory: `var/<sessionId>/<workId>/<taskId>/` or the nested delegated triple beneath the exact parent task directory.

## Plan brief

- Question: …
- Scope: affected components or areas
- Constraints stated by user: …
- Success criteria: …

## Open branches

| Qualified ID | Branch | Level | Owner label | Owner task directory | Status | Depends on |
| ------------ | ------ | ----- | ----------- | -------------------- | ------ | ---------- |
| <owner-label>:B1 | … | 1 | <owner-label> | <canonical owner task directory> | open | — |

## Resolved branches

| ID  | Decision | Rationale | Evidence                   |
| --- | -------- | --------- | -------------------------- |
| <owner-label>:B1 | … | … | original owner response path / codebase / user / web / DB |

## Deferred

| ID | Reason | When |
| -- | ------ | ---- |

## Blocked (needs user)

| ID  | Blocker | Next question id |
| --- | ------- | ---------------- |

## Assumptions (explicit)

- A1: … — validated: yes | no | pending

## Shared understanding checklist

- [ ] Every level integration gate verified in dag.md
- [ ] Every owner tree merged with qualified IDs and original response paths, copied unchanged from each owner's canonical task directory
- [ ] Every owner answer archived and its question/watcher resources accounted for; no hosted evidence deleted before archival
- [ ] Every open branch closed or explicitly deferred
- [ ] No contradictory resolved decisions
- [ ] External claims grounded in official sources
- [ ] Repository claims grounded in direct evidence
```

## Traversal rules

1. **Level-based between owners, depth-first within an owner** — dispatch independent ready branches concurrently; resolve local parents before children and integrate the whole level before advancing.
2. **One question per owner** — separate visible browser interviews may run concurrently. Each owner calls WaitForAnswer, yields while pending, records the archived browser answer on wake, and advances its own follow-ups automatically.
3. **Ground before ask** — if the answer might live in the repository, logs, data store, runtime, or documentation, gather that evidence first; only ask the user what remains unknown. When using any independent agent, follow the parent skill's Herdr-first runtime policy.
4. **Mark disposition** — move an accepted decision from Open → Resolved with rationale and unchanged ID. Move only a user-approved deferral to Deferred with reason/revisit conditions. A rejection stays open/rework-needed; neither it nor a deferral satisfies a required decision dependency.
5. **Split on fork** — add child rows to the owner's local tree before continuing. Keep helper IDs B<n>; the parent merges them as <owner-label>:B<n>. Cross-owner dependencies return to the parent for re-planning. A child owner always writes inside its own canonical task directory, which for a delegated owner is its own session/Work/Task triple beneath the exact parent task directory it received.
6. **Deferral is explicit** — `deferred: <reason>` is allowed; do not silently skip branches.

## Question quality bar

Each branch question must use the browser interview page. A blocked browser flow blocks the interview.

Each browser question should:

- Use local branch ID `B<n>` and a safe session-unique tool question ID such as `<owner-label>-B1`; show level and owner/decision in the title. After consuming the validated answer, copy it unchanged from the returned `responsePath` into the owner's `response-B<n>.json` evidence file.
- State why the branch matters and include the evidence-backed recommendation.
- Provide **2–6 options** plus a free-form response; comments-only rejection is valid. Choose required `mode: "multiple"` for compatible additive options and `"single"` for mutually exclusive alternatives.
- Record all `selectedIds`/`selectedLabels` and the user's `response`; use `submissionType` and empty arrays for comments-only rejection. There are no scalar-answer fallbacks. Resolve conflicting selections through follow-up questions.
- Add a Mermaid or image content block when it materially clarifies a core concept. Use complete absolute paths for media and pass content directly, not an options file.
- Call `WaitForAnswer` immediately after sharing the `SubmitQuestion` URL; verify its background watcher so the user never needs to type `continue`. After reload, re-arm unresolved questions instead of republishing them.

## When to use independent agents

| Prompt responsibility                                     | Trigger                                                                |
| --------------------------------------------------------- | ---------------------------------------------------------------------- |
| Autonomous browser branch interview | Ready independent decision with substantial follow-ups; owner closes its whole local tree |
| Consistency and ownership critique                        | Branch touches queues, migrations, data flow, or consistency           |
| Adversarial failure-mode review                           | A resolved option needs unsafe assumptions or missing forks challenged |
| Repository, data, runtime, or external evidence gathering | A factual answer should be grounded before asking the user             |

Responsibilities are described in prompts; they are not repository-specific roles or skills. Interview owners are authorized to ask the user directly in their own browser sessions and return verified branch closure. Evidence/review agents remain read-only. No agent replaces user answers or spawns more agents. Core-hosted interactive Pi agents in dedicated visible Task-ID-named Herdr app tabs are the only runtime. Use the global herdr skill's real Core verification and continuous monitoring; do not require old TUI environment variables.
