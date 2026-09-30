# UI/UX grill-me visual decision tree

The conductor maintains this artifact at `var/<feature-name>/ui-ux-grill-me/<session-slug>/visual-decision-tree.md`.

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

| ID  | Branch      | Axis   | Status | Depends on |
| --- | ----------- | ------ | ------ | ---------- |
| B1  | Hero layout | layout | open   | —          |

## Resolved branches

| ID  | Choice | Variant id | Why | Evidence          |
| --- | ------ | ---------- | --- | ----------------- |
| B1  | …      | B or none  | …   | selection-B1.json |

## Deferred

| ID | Reason | When |

## Assumptions

- A1: … — validated: yes | no | pending

## Shared understanding checklist

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

1. **Depth-first on dependencies** — parent branches before children.
2. **One comparison at a time** — wait for feedback before opening the next page; automatic same-turn progression is allowed.
3. **Current first** — option A is always the captured baseline unless user requests otherwise.
4. **One axis per branch** — e.g. layout OR CTA prominence, not both.
5. **Record feedback JSON** — keep the original `B<n>` branch ID and copy `selected`, `label`, and `why` from `selection-B<n>.json` into Resolved. If `submissionType` is `comments-only`, record the branch as rejected/rework-needed with variant `none`.
6. **Deferral is explicit** — do not skip branches silently.

## Branch quality bar

Each comparison page should include:

- Clear `[question]` headline matching the branch
- Exactly 6 views: current baseline, 3 standard variants, and 2 out-of-the-box variants, each with a short label and one-line tradeoff
- Embedded or linked visuals — **viewport PNG for every option** (required); iframe-only output is not accepted
- Source provenance for every option: `live-route` or `mockup-html`, source path, viewport, and route when applicable
- Expand control for every viewport image
- Recommended variant noted in `generate-comparison` config (`recommended` field)
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
