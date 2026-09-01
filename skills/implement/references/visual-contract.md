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
- `visual-decision-tree.md`, including the resolved branch and parent `/grill-me` slug.

The selected screenshot is authoritative for visible hierarchy, placement, spacing,
density, controls, states, copy, color treatment, borders, radii, and shadows. The
user's written modification overrides the screenshot. The implementation mechanism
(React component structure, CSS organization, data plumbing, and accessibility
details) may differ as long as the visible contract and behavior are preserved.

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
explicit user decision may revise the visual contract. A written `pass` is not
sufficient by itself: the selected screenshot, implemented screenshot, selection
JSON, and comparison report must be digest-bound to the final contract-review pack.

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

Pass the visual contract into `/implement` unchanged. The implement coordinator and
workers must read the selected screenshot, source artifact, image-generation
reference, viewport, decision tree, and selection rationale before editing code.
Do not reconstruct a selected direction from the label or screenshot alone when its
source artifact is available.

## Contract-review pack

Before final review, add every resolved and deferred branch from the selected UI/UX
decision tree to `var/<feature-name>/implement/contract-review-pack.json` using the
schema enforced by the global Agent Review `validate-contract-preflight.py` script.
For each resolved branch, record the exact route, viewport, fixture, interaction
state, theme, container, selected source (with a digest-bound mockup file when applicable),
required behavior, accessibility constraints, exact user modifications, valid selected and implemented PNGs, selection evidence, passing JSON comparison
report, current review fingerprint, and `userModificationsHonored: true`. Deferred branches
do not require parity evidence and must not claim a pass.

Run the validator with the exact feature name and persist
`var/<feature-name>/implement/evidence/contract-preflight.json`. If validation fails,
return to implementation before reviewer resource creation.

## Post-code review

After implementation, capture the same route, state, viewport, and interaction state
again. Save the result in the project's approved visual-review artifact location and
run the repository's visual review process. The UI task is incomplete until the live screenshot matches the
visual contract, user modifications are honored, and the independent review has no
accepted findings. Live interactive end-to-end behavior testing remains a separate,
user-owned handoff unless the latest request explicitly asks an agent to run it; a
visual match must never be presented as proof that the user-owned behavior test passed.
