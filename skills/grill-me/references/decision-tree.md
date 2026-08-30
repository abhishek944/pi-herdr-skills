# Grill-me decision tree

The conductor maintains this artifact at `var/<feature-name>/grill-me/<session-slug>/decision-tree.md`.

## Template

```markdown
# Decision tree — <session-slug>

## Plan brief

- Question: …
- Scope: affected components or areas
- Constraints stated by user: …
- Success criteria: …

## Open branches

| ID  | Branch | Status | Depends on |
| --- | ------ | ------ | ---------- |
| B1  | …      | open   | —          |

## Resolved branches

| ID  | Decision | Rationale | Evidence                   |
| --- | -------- | --------- | -------------------------- |
| R1  | …        | …         | codebase / user / web / DB |

## Blocked (needs user)

| ID  | Blocker | Next question id |
| --- | ------- | ---------------- |

## Assumptions (explicit)

- A1: … — validated: yes | no | pending

## Shared understanding checklist

- [ ] Every open branch closed or explicitly deferred
- [ ] No contradictory resolved decisions
- [ ] External claims grounded in official sources
- [ ] Repository claims grounded in direct evidence
```

## Traversal rules

1. **Depth-first on dependencies** — resolve parent branches before children.
2. **One browser question at a time** — wait for Submit, record the response, then advance automatically in the same turn.
3. **Ground before ask** — if the answer might live in the repository, logs, data store, runtime, or documentation, gather that evidence first; only ask the user what remains unknown. When using any independent agent, follow the parent skill's Herdr-first runtime policy.
4. **Mark resolution** — when the user answers, move the row from Open → Resolved and record rationale.
5. **Split on fork** — when the user picks an option that opens sub-branches, add child rows before continuing.
6. **Deferral is explicit** — `deferred: <reason>` is allowed; do not silently skip branches.

## Question quality bar

Each branch question must use the browser interview page. A blocked browser flow blocks the interview.

Each browser question should:

- Use branch id `B<n>` and write `response-B<n>.json` on Submit.
- State why the branch matters and include the evidence-backed recommendation.
- Provide **2–6 options** plus a free-form response; comments-only rejection is valid.
- Add a Mermaid, HTML, or image explanation when it materially clarifies a core concept.
- Run the waiter immediately so the user never needs to type `continue`.

## When to use independent agents (optional)

| Prompt responsibility                                     | Trigger                                                                |
| --------------------------------------------------------- | ---------------------------------------------------------------------- |
| Consistency and ownership critique                        | Branch touches queues, migrations, data flow, or consistency           |
| Adversarial failure-mode review                           | A resolved option needs unsafe assumptions or missing forks challenged |
| Repository, data, runtime, or external evidence gathering | A factual answer should be grounded before asking the user             |

Responsibilities are described in prompts; they are not repository-specific roles or skills. Independent agents do not replace user answers or spawn more agents. Herdr-hosted Pi agents are the only runtime.
