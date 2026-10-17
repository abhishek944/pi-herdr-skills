# Visual contract

A resolved UI/UX grill decision is implementation input, not loose inspiration.

## Required evidence

For every resolved visual branch, preserve:

- the selected viewport screenshot under `var/<feature-name>/ui-ux-grill-me/<slug>/screenshots/`;
- the current/baseline screenshot for the same branch;
- the selected option's source artifact: live route, mockup HTML, or both;
- the session image-generation art-direction reference, its prompt record, and
  the visual choices carried from it into the selected candidate;
- the viewport size and relevant interaction state;
- `selection-B<n>.json`, including the user's rationale and modifications;
- the parent `dag.md` and aggregate `visual-decision-tree.md`, including verified level gates, qualified branch IDs and the parent global `grill-me` session slug;
- each owner session's local tree and original screenshot, source and selection paths (do not flatten or rename colliding B<n> files).

The selected screenshot is authoritative for visible hierarchy, placement, spacing,
density, controls, states, copy, color treatment, borders, radii, and shadows. The
user's written modification overrides the screenshot. The implementation mechanism
(React component structure, CSS organization, data plumbing, and accessibility
details) may differ as long as the visible contract and behavior are preserved.

## Multiple selections

With `selectionMode: "multiple"`, preserve `selectedIds`, `selectedLabels`, and every `visualContracts` entry from the original response. Each entry retains its screenshot, source, source artifact, and shared comparison contract. Legacy singular fields are null when more than one choice is selected; this is not comments-only rejection.

Multiple selected screenshots are not automatically one authoritative visual contract. Keep the branch open, clarify what to combine, resolve contradictions, and show a coherent combined browser-rendered candidate in a single-select follow-up for user acceptance. That accepted combined screenshot and source become authoritative; preserve original selections and user rationale as supporting evidence. Never silently pick the first selection or hand conflicting screenshots to implementation as an already resolved design.

## Exact-state implementation gate

The implementation is incomplete until it proves the selected design against the
live product UI. The proof must use the exact selected viewport, route, panel
dimensions, and interaction fixture—not an approximate screen, a different
responsive breakpoint, or a different data state.

Create `var/<feature-name>/ui-ux-grill-me/<slug>/implementation-visual-verification.md` containing:

- selected screenshot and source artifact paths;
- selected viewport, route, panel dimensions, and interaction fixture;
- post-implementation screenshot path captured in that exact state;
- a side-by-side comparison verdict covering hierarchy, spacing, density, copy,
  controls, borders, radii, shadows, and visible states; and
- every mismatch plus the rework screenshot that resolved it.

Any mismatch keeps the implementation in rework. Lint, a build, DOM assertions,
or a recording at another state cannot substitute for this comparison. Only an
explicit user decision may revise the visual contract.

## Candidate provenance

Every option in `options-B<n>.json` must include:

```json
{
  "image": "screenshots/B1-variant-B.png",
  "source": {
    "kind": "mockup-html",
    "path": "mockups/B1-variant-B.html",
    "viewport": "1440x900",
    "route": null
  }
}
```

Use `kind: "live-route"` for a real application route. Every options file must
also include a session-level `referenceImages` array pointing to the generated
art-direction reference. The generated raster guides the variants but is not a
selectable product UI candidate or an implementation source; the browser-rendered
candidate remains the implementation reference.

## Implementation handoff

Pass the visual contract into the globally installed `implement` skill unchanged. Its coordinator and
workers must read the selected screenshot, source artifact, image-generation
reference, viewport, decision tree, and selection rationale before editing code.
Include the feature name, parent UI/UX session slug, all owner session slugs/artifact paths, parent Grill Me slug, and resolved and
deferred qualified branch IDs. The parent must reconcile selections across owners before the final contract is authoritative. The final visual decision tree must list every branch under
Resolved or Deferred so review can verify exact coverage. Do not reconstruct a selected direction from the label or
screenshot alone when its source artifact is available. Give final reviewers the
selected decision tree and current visual comparison directly.

## Post-code review

After implementation, capture the same route, state, viewport, and interaction state
again. Save the result in the repository's approved visual-review artifact location and
run the repository's visual review process. The UI task is incomplete until the live screenshot matches the
visual contract, user modifications are honored, the independent review has no
accepted findings, and the repository's final behavior verification passes.
