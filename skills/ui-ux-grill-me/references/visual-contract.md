# Visual contract

A resolved UI/UX grill decision is implementation input, not loose inspiration.

## Required evidence

For every resolved visual branch, preserve:

- the selected viewport screenshot under `<taskDir>/screenshots/`, where `<taskDir>` is the owner's canonical task directory (`var/<sessionId>/<workId>/<taskId>/`, or the nested delegated triple beneath the exact parent task directory);
- the current/baseline screenshot for the same branch;
- the selected option's source artifact: live route, mockup HTML, or both;
- the session image-generation art-direction reference, its prompt record, and
  the visual choices carried from it into the selected candidate;
- the viewport size and relevant interaction state;
- the unchanged validated answer copied to `response-B<n>.json`, its original returned `responsePath`, and skill-owned `selection-B<n>.json` containing the trusted provenance join and the user's rationale;
- the parent `dag.md` and aggregate `visual-decision-tree.md`, including verified level gates, qualified branch IDs and the parent Grill Me task directory;
- each owner task directory's local tree and original screenshot, source and selection paths (do not flatten or rename colliding B<n> files; hand off exact paths rather than reconstructing them from labels).

The selected screenshot is authoritative for visible hierarchy, placement, spacing,
density, controls, states, copy, color treatment, borders, radii, and shadows. The
user's written modification overrides the screenshot. The implementation mechanism
(React component structure, CSS organization, data plumbing, and accessibility
details) may differ as long as the visible contract and behavior are preserved.

## Multiple selections

With `mode: "multiple"`, preserve the validated answer’s `selectedIds`, `selectedLabels`, and `response`, plus every `visualContracts` entry constructed by this skill from its private variant mapping. The tool does not generate contracts or scalar-answer aliases. Each skill-owned contract retains screenshot, source, source artifact/hash and shared comparison constraints. Several selections are not comments-only rejection.

Multiple selected screenshots are not automatically one authoritative visual contract. Keep the branch open, clarify what to combine, resolve contradictions, and show a coherent combined browser-rendered candidate in a single-select follow-up for user acceptance. That accepted combined screenshot and source become authoritative; preserve original selections and user rationale as supporting evidence. Never silently pick the first selection or hand conflicting screenshots to implementation as an already resolved design.

## Exact-state implementation gate

The implementation is incomplete until it proves the selected design against the
live product UI. The proof must use the exact selected viewport, route, panel
dimensions, and interaction fixture—not an approximate screen, a different
responsive breakpoint, or a different data state.

Create `<verificationTaskDir>/implementation-visual-verification.md` in the canonical task directory of the task performing verification (normally the implementing task, not the interview task), linking the original interview evidence by exact path. It contains:

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

Keep a private variant-ID mapping before presenting choices. `templates/example-options.json` is an evidence template only, never a tool request. For every variant retain its complete absolute screenshot path plus source kind, location, viewport and route:

```json
{
  "id": "B",
  "image": "/absolute/path/screenshots/B1-variant-B.png",
  "source": {
    "kind": "mockup-html",
    "path": "/absolute/path/mockups/B1-variant-B.html",
    "viewport": "1440x900",
    "route": null
  },
  "sourceArtifact": {
    "path": "/absolute/path/mockups/B1-variant-B.html",
    "sha256": "<SHA256 of the source file shown>"
  }
}
```

Use `kind: "live-route"` with the actual URL for application sources; `sourceArtifact` is null when there is no retained mockup file. Keep the shared contract and art-direction `referenceImages` provenance alongside the variant mapping. The generated raster guides variants but is not a selectable product UI or implementation source. This metadata stays private and is not passed to SubmitQuestion; only image content blocks with complete absolute paths are supplied for the screenshots.

After collecting the normalized tool answer, archive an unchanged `response-B<n>.json` copy and build this separate skill-owned selection envelope:

```json
{
  "answer": "<the unchanged normalized tool answer object>",
  "responsePath": "<the exact responsePath returned by the tool>",
  "privateVariantEvidence": "<absolute path to the pre-submission variant mapping>",
  "visualContracts": []
}
```

For each `answer.selectedIds` entry, join the ID to the original trusted variant record and construct a contract containing branch/question, variantId, label/category, screenshot, source, sourceArtifact and the shared constraints. Preserve displayed option order. Use `answer.response` for rationale and modifications. Browser feedback cannot supply or replace provenance. Comments-only feedback has an empty contract array and keeps the branch open. Question ID/revision and the recorded mapping must correspond to the exact presented choices.

## Implementation handoff

Pass the visual contract into the globally installed `implement` skill unchanged. Its coordinator and
workers must read the selected screenshot, source artifact, image-generation
reference, viewport, decision tree, and selection rationale before editing code.
Include the feature name, the UI/UX parent and owner task directory paths and labels, the parent Grill Me task directory, and resolved and
deferred qualified branch IDs. The parent must reconcile selections across owners before the final contract is authoritative. The final visual decision tree must list every branch under
Resolved or Deferred so review can verify exact coverage. Do not reconstruct a selected direction from the label or
screenshot alone when its source artifact is available. Give final reviewers the
selected decision tree and current visual comparison directly.

## Post-code review

After implementation, capture the same route, state, viewport, and interaction state
again. Save the result in the canonical task directory of the task performing verification
(normally the implementing task), and run the repository's visual review process. The UI task is incomplete until the live screenshot matches the
visual contract, user modifications are honored, the independent review has no
accepted findings, and the repository's final behavior verification passes.
