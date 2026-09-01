# Contract-aware review preflight

Run this preflight before model resolution, pane creation, or reviewer launch.

## Discovery

Use the implementation feature name and inspect only:

```text
var/<feature-name>/grill-me/<session-slug>/decision-tree.md
var/<feature-name>/ui-ux-grill-me/<session-slug>/visual-decision-tree.md
```

Ignore legacy `var/grill-me/`. Record every discovered candidate in the contract pack.

- No candidate: record `selectionBasis: none` and a reason.
- One candidate: select it with `selectionBasis: single-candidate`.
- Several candidates: require a digest-bound JSON selection with `featureName`, `kind`, and `selected` matching the chosen session. Do not choose the newest session.

## Contract pack

Create `var/<feature-name>/implement/contract-review-pack.json`. The validator script is the schema authority:

```bash
python3 <agent-review-root>/scripts/validate-contract-preflight.py \
  --pack var/<feature-name>/implement/contract-review-pack.json \
  --repo-root <repository-root> \
  --feature-name <feature-name> \
  --fingerprint <current-review-fingerprint> \
  --output var/<feature-name>/implement/evidence/contract-preflight.json
```

The pack contains:

- the current review fingerprint and feature name;
- discovered and selected Grill Me and UI/UX Grill Me sessions;
- unresolved ambiguities, which must be empty;
- every resolved and deferred branch listed in the selected decision-tree Markdown;
- exact branch coverage in the pack, with no omitted or invented IDs;
- current passing functionality evidence for every resolved Grill Me decision;
- current exact-state visual-parity evidence for every resolved UI/UX branch;
- the separate status of user-owned live testing.

Deferred decisions are not requirements and cannot claim passing evidence.

## Functionality evidence

Each resolved Grill Me decision must map to a current passing verdict with:

- the same review fingerprint;
- a plain-language summary of the expected behavior;
- one or more small JSON reports binding `decisionId`, fingerprint, command, zero exit code, and digest-bound output.

A build or lint result alone is not functionality evidence unless the decision is specifically about build or lint behavior. Missing or failing evidence returns the work to implementation.

## Visual parity evidence

Each resolved UI/UX branch must map to a current passing verdict with:

- exact route;
- exact viewport width and height;
- exact data fixture, interaction state, theme, and container;
- selected source and, for mockups, its digest-bound source file;
- required behavior, accessibility constraints, and exact user modifications;
- selected browser-rendered PNG screenshot;
- post-implementation screenshot;
- generated selection JSON containing the same exact-state contract, source, rationale, and modifications;
- passing JSON comparison report binding the same fingerprint, branch, exact state, requirements, and screenshot digests;
- confirmation that written user modifications were honored.

The selected and implemented screenshots must be valid PNG files, use the exact viewport dimensions, and be different files. Art-direction images are supporting references, not selectable product UI and not parity evidence.

## Freshness and launch gate

The contract pack must name the live review fingerprint. Every functionality and visual-parity verdict must use that fingerprint, and every referenced file must match its SHA-256 digest.

Persist the validator output as `evidence/contract-preflight.json`. Record the contract-pack digest and preflight-output digest before creating reviewer resources. Every reviewer prompt and report must bind both digests:

```text
Contract pack: <sha256>
Contract preflight: <sha256>
```

If discovery is ambiguous, inventories and pack coverage differ, validation fails, evidence is stale, functionality fails, visual parity fails, or a required artifact is missing, stop before model resolution and reviewer launch. Report the concrete mismatch and hand the work back to implementation.

## User-owned live testing

Certification and completion recompute discovery and the preflight so contract evidence cannot change after review without invalidating completion.

The preflight records user-owned live testing separately as `pending`, `pass`, or `not-required`. A pending user test does not block review when current automated functionality and visual-parity evidence pass, but no agent may claim the pending live interaction passed.
