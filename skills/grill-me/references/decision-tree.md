# Grill-me decision tree

The conductor maintains this artifact at `var/<feature-name>/grill-me/<session-slug>/decision-tree.md`.

## DAG template

Create `dag.md` in the parent session before questions. The parent owns it and the aggregate tree; owner sessions contain local trees and original responses.

```markdown
# Interview DAG — <parent-slug>

| Branch | Todo/local ID | Outcome / closure criteria | Dependencies | Level | Owner | Session / owned boundary | Status | Evidence |
| ------ | ------------- | -------------------------- | ------------ | ----- | ----- | ------------------------ | ------ | -------- |
| <owner-slug>:B1 | <actual ID> | <decision plus all follow-ups closed> | — | 1 | <owner> | <unique flat owner session> | pending | — |
| integrate-L1 | <actual ID> | Verify artifacts and reconcile level | <level-1 branches> | 1 | parent | <aggregate files only> | pending | — |

## Level gates

- L1: <independent branches>; integration: <pending/complete/blocked>
- L2: <branches requiring verified L1 decisions>
```

Dependency IDs must exist and the graph must be acyclic. Keep readiness/status here, not in a second scheduler. A completed interview Todo records a verified disposition, not necessarily a resolved decision: a deferred prerequisite requires re-scoping or deferring downstream branches. Each owner records local parent-child links and reports discovered dependencies; only the parent updates shared DAG/Todos. Preserve qualified IDs and original paths during merge and handoff.

## Template

```markdown
# Decision tree — <session-slug>

## Plan brief

- Question: …
- Scope: affected components or areas
- Constraints stated by user: …
- Success criteria: …

## Open branches

| Qualified ID | Branch | Level | Owner session | Status | Depends on |
| ------------ | ------ | ----- | ------------- | ------ | ---------- |
| <owner-slug>:B1 | … | 1 | <owner-slug> | open | — |

## Resolved branches

| ID  | Decision | Rationale | Evidence                   |
| --- | -------- | --------- | -------------------------- |
| <owner-slug>:B1 | … | … | original owner response path / codebase / user / web / DB |

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
- [ ] Every owner tree merged with qualified IDs and original response paths
- [ ] Every owner save server/Monitor cleaned up
- [ ] Every open branch closed or explicitly deferred
- [ ] No contradictory resolved decisions
- [ ] External claims grounded in official sources
- [ ] Repository claims grounded in direct evidence
```

## Traversal rules

1. **Level-based between owners, depth-first within an owner** — dispatch independent ready branches concurrently; resolve local parents before children and integrate the whole level before advancing.
2. **One question per owner** — separate visible browser interviews may run concurrently. Each owner waits for Submit, records it, and advances its own follow-ups automatically in the same turn.
3. **Ground before ask** — if the answer might live in the repository, logs, data store, runtime, or documentation, gather that evidence first; only ask the user what remains unknown. When using any independent agent, follow the parent skill's Herdr-first runtime policy.
4. **Mark disposition** — move an accepted decision from Open → Resolved with rationale and unchanged ID. Move only a user-approved deferral to Deferred with reason/revisit conditions. A rejection stays open/rework-needed; neither it nor a deferral satisfies a required decision dependency.
5. **Split on fork** — add child rows to the owner's local tree before continuing. Keep helper IDs B<n>; the parent merges them as <owner-slug>:B<n>. Cross-owner dependencies return to the parent for re-planning.
6. **Deferral is explicit** — `deferred: <reason>` is allowed; do not silently skip branches.

## Question quality bar

Each branch question must use the browser interview page. A blocked browser flow blocks the interview.

Each browser question should:

- Use local helper branch id `B<n>` and write `response-B<n>.json` in its unique owner session on Submit; show the level and owner/decision in the title.
- State why the branch matters and include the evidence-backed recommendation.
- Provide **2–6 options** plus a free-form response; comments-only rejection is valid.
- Add a Mermaid, HTML, or image explanation when it materially clarifies a core concept.
- Run the waiter immediately so the user never needs to type `continue`.

## When to use independent agents

| Prompt responsibility                                     | Trigger                                                                |
| --------------------------------------------------------- | ---------------------------------------------------------------------- |
| Autonomous browser branch interview | Ready independent decision with substantial follow-ups; owner closes its whole local tree |
| Consistency and ownership critique                        | Branch touches queues, migrations, data flow, or consistency           |
| Adversarial failure-mode review                           | A resolved option needs unsafe assumptions or missing forks challenged |
| Repository, data, runtime, or external evidence gathering | A factual answer should be grounded before asking the user             |

Responsibilities are described in prompts; they are not repository-specific roles or skills. Interview owners are authorized to ask the user directly in their own browser sessions and return verified branch closure. Evidence/review agents remain read-only. No agent replaces user answers or spawns more agents. Herdr-hosted Pi agents are the only runtime.
