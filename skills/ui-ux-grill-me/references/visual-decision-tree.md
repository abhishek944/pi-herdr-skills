# UI/UX grill-me visual decision tree

The conductor maintains this artifact at `var/<feature-name>/ui-ux-grill-me/<session-slug>/visual-decision-tree.md`.

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
# Visual decision tree — <session-slug>

## Brief

- Surface: <page or component>
- Scope: <hero | nav | full page | …>
- Parent grill-me slug: <slug or none>
- Constraints: …
- Success criteria: …

## Viewports captured

| Label   | Size     | Path                             |
| ------- | -------- | -------------------------------- |
| desktop | 1440×900 | screenshots/baseline-desktop.png |

## Image-generation reference

| Role          | Path                                  | Prompt record                        | Visual choices carried into variants |
| ------------- | ------------------------------------- | ------------------------------------ | ------------------------------------ |
| art direction | references/imagegen-art-direction.png | references/imagegen-art-direction.md | …                                    |

## Open branches

| Qualified ID | Branch | Axis | Level | Owner session | Status | Depends on |
| ------------ | ------ | ---- | ----- | ------------- | ------ | ---------- |
| <owner-slug>:B1 | Hero layout | layout | 1 | <owner-slug> | open | <verified foundations> |

## Resolved branches

| ID  | Choice | Variant id(s) | Why | Evidence          |
| --- | ------ | ---------- | --- | ----------------- |
| <owner-slug>:B1 | … | B or none | … | original owner selection-B1.json and screenshot/source paths |

## Deferred

| ID | Reason | When |

## Assumptions

- A1: … — validated: yes | no | pending

## Shared understanding checklist

- [ ] Shared design/interaction foundations resolved before independent axes
- [ ] Every level integration gate verified in dag.md
- [ ] Owner trees merged with qualified IDs and original screenshot/source/selection paths
- [ ] Every owner save server/Monitor cleaned up
- [ ] Every open branch closed or deferred
- [ ] No contradictory resolved decisions
- [ ] Current UI captured before variants shown
- [ ] Image-generation reference created and inspected before variants shown
- [ ] Each branch varied one primary axis
- [ ] Every option has screenshot and source provenance
- [ ] Selection JSON exists for each resolved branch
- [ ] Resolved branch records selected screenshot, source, viewport, and user modifications
- [ ] Exact-state implemented screenshot was compared against the selected screenshot
- [ ] Every visible mismatch was reworked or explicitly revised by the user
```

## Traversal rules

1. **Level-based between owners, depth-first within an owner** — resolve shared foundations, dispatch ready independent axes concurrently, then integrate the level before advancing.
2. **One comparison per owner** — each owner opens a separate visible browser interview, waits for feedback, and follows local children automatically. Browser tabs/windows across owners may compete; artifact directories, ports and mutable capture state must not.
3. **Current first** — option A is always the captured baseline unless user requests otherwise.
4. **One axis per branch** — e.g. layout OR CTA prominence, not both.
5. **Record feedback JSON** — keep local helper IDs `B<n>` and qualify them as `<owner-slug>:B<n>` in the aggregate tree. Read `selectedIds`, `selectedLabels`, `visualContracts`, and `why` from `selection-B<n>.json`, falling back to legacy scalar fields only when arrays are absent. Preserve all selections and source paths. Multiple selected variants keep the branch open for synthesis: clarify how parts combine and get acceptance of a coherent combined browser-rendered candidate in a single-select follow-up before moving it to Resolved. If `submissionType` is `comments-only`, keep the branch open/rework-needed with variant `none` until a revised choice is accepted or the user explicitly defers it. Only user-approved deferrals enter Deferred; they do not satisfy required decision dependencies.
6. **Deferral is explicit** — do not skip branches silently.

## Branch quality bar

Each comparison page should include:

- Clear `[question]` headline matching the branch
- Exactly 6 views: current baseline, 3 standard variants, and 2 out-of-the-box variants, each with a short label and one-line tradeoff
- Embedded or linked visuals — **viewport PNG for every option** (required); iframe-only output is not accepted
- Source provenance for every option: `live-route` or `mockup-html`, source path, viewport, and route when applicable
- Expand control for every viewport image
- Recommended variant noted in `generate-comparison` config (`recommended` field)
- Set `selectionMode: "multiple"` when compatible choices can coexist, otherwise `"single"` (default); record every selected variant rather than just the first
- Comments field that permits comments-only submission when no option is acceptable

## Suggested branch axes (landing page)

| Axis               | Example question                                         |
| ------------------ | -------------------------------------------------------- |
| Hero layout        | Split copy/preview vs centered stack vs preview-dominant |
| CTA pattern        | Dual buttons vs single primary + text link               |
| Above-fold density | Full viewport vs compact with scroll cue                 |
| Nav style          | Transparent over hero vs solid bar                       |
| Section rhythm     | Alternating dark/light vs continuous dark hero band      |
| Mobile hero        | Preview below copy vs preview as background              |
