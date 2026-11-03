# UI/UX grill-me visual decision tree

The conductor maintains this artifact in the owning canonical task directory: `<taskDir>/visual-decision-tree.md`, where `<taskDir>` is `var/<sessionId>/<workId>/<taskId>/` for a root owner or the nested delegated triple beneath the exact parent task directory. Feature names, session slugs and owner labels are descriptive metadata only and never select a directory.

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
# Visual decision tree — <owner label>

Owner task directory: `<taskDir>`.

## Brief

- Surface: <page or component>
- Scope: <hero | nav | full page | …>
- Parent Grill Me task directory: <path or none>
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

| Qualified ID | Branch | Axis | Level | Owner label | Owner task directory | Status | Depends on |
| ------------ | ------ | ---- | ----- | ----------- | -------------------- | ------ | ---------- |
| <owner-label>:B1 | Hero layout | layout | 1 | <owner-label> | <canonical owner task directory> | open | <verified foundations> |

## Resolved branches

| ID  | Choice | Variant id(s) | Why | Evidence          |
| --- | ------ | ---------- | --- | ----------------- |
| <owner-label>:B1 | … | B or none | … | original owner selection-B1.json and screenshot/source paths |

## Deferred

| ID | Reason | When |

## Assumptions

- A1: … — validated: yes | no | pending

## Shared understanding checklist

- [ ] Shared design/interaction foundations resolved before independent axes
- [ ] Every level integration gate verified in dag.md
- [ ] Owner trees merged with qualified IDs and original screenshot/source/selection paths, copied unchanged from each owner's canonical task directory
- [ ] Every owner answer archived and question/watcher resources accounted for; no hosted evidence deleted before archival
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
2. **One comparison per owner** — each owner opens a separate visible browser interview, waits for feedback, and follows local children automatically. Owners call WaitForAnswer and yield while pending; the watcher resumes the owning session. Browser tabs/windows across owners may compete; task directories, question identities and mutable capture state must not.
3. **Current first** — option A is always the captured baseline unless user requests otherwise.
4. **One axis per branch** — e.g. layout OR CTA prominence, not both.
5. **Record feedback JSON** — keep local branch IDs `B<n>`, safe session-unique tool IDs such as `<owner-label>-B1`, and qualified tree IDs `<owner-label>:B<n>`. Consume the validated answer at the returned `responsePath`, archive its unchanged copy as `response-B<n>.json`, and build skill-owned `selection-B<n>.json` with `answer`, `responsePath`, `privateVariantEvidence`, and `visualContracts`. Read selections and rationale from `answer.selectedIds`, `answer.selectedLabels`, and `answer.response`; reconstruct contracts from trusted private variant records, never browser-supplied fields. Preserve all selections and source paths. Multiple selected variants keep the branch open for synthesis: clarify how parts combine and get acceptance of a coherent combined browser-rendered candidate in a single-select follow-up before moving it to Resolved. If `submissionType` is `comments-only`, keep the branch open/rework-needed with variant `none` until a revised choice is accepted or the user explicitly defers it. Only user-approved deferrals enter Deferred; they do not satisfy required decision dependencies.
6. **Deferral is explicit** — do not skip branches silently.

## Branch quality bar

Each comparison page should include:

- Clear `[question]` headline matching the branch
- Exactly 6 views: current baseline, 3 standard variants, and 2 out-of-the-box variants, each with a short label and one-line tradeoff
- Embedded or linked visuals — **viewport PNG for every option** (required); iframe-only output is not accepted
- Private source provenance for every option: `live-route` or `mockup-html`, source path, viewport, route and source artifact/hash when applicable; keep this outside the tool request
- Expand control for every viewport image
- Recommended variant noted in the direct `SubmitQuestion` input (`recommended` field)
- Set required `mode: "multiple"` when compatible choices can coexist, otherwise `"single"`; record every selected variant rather than just the first
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
